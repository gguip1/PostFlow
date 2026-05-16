import json
import urllib.error
from urllib.request import Request, urlopen

from vcli.adapters.velog.auth import get_auth_path

VELOG_GRAPHQL = "https://v3.velog.io/graphql"


def _get_access_token() -> str:
    with open(get_auth_path(), encoding="utf-8") as f:
        storage = json.load(f)
    cookies = {c["name"]: c["value"] for c in storage.get("cookies", [])}
    return cookies.get("access_token", "")


def _graphql(query: str, variables: dict | None = None) -> dict:
    access_token = _get_access_token()
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    req = Request(
        VELOG_GRAPHQL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Cookie": f"access_token={access_token}",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            body = resp.read()
            if not body:
                return {}
            return json.loads(body)
    except urllib.error.URLError as e:
        raise ConnectionError(
            f"Velog API에 연결할 수 없습니다. 네트워크 상태를 확인하세요.\n원인: {e}"
        )
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise PermissionError(
                "인증이 만료되었습니다. 'vcli login'으로 다시 로그인하세요."
            )
        raise ConnectionError(f"Velog API 오류 (HTTP {e.code}): {e.reason}")


def get_current_user() -> dict | None:
    result = _graphql("{ currentUser { id username } }")
    return result.get("data", {}).get("currentUser")


def get_user_posts(username: str) -> list[dict]:
    """사용자의 모든 글을 가져온다."""
    query = """query {
        posts(input: { username: "%s" }) {
            id title url_slug tags is_private
            released_at updated_at short_description body
            series { id name }
        }
    }""" % username

    result = _graphql(query)
    return result.get("data", {}).get("posts", [])


def write_post(
    title: str,
    body: str,
    tags: list[str],
    is_private: bool = False,
    url_slug: str = "",
    description: str = "",
    series_id: str | None = None,
) -> dict | None:
    """새 글을 발행한다."""
    query = """mutation WritePost($input: WritePostInput!) {
        writePost(input: $input) {
            id title url_slug released_at updated_at
        }
    }"""
    variables = {
        "input": {
            "title": title,
            "body": body,
            "tags": tags,
            "is_markdown": True,
            "is_temp": False,
            "is_private": is_private,
            "url_slug": url_slug,
            "meta": {"short_description": description},
        }
    }
    if series_id:
        variables["input"]["series_id"] = series_id

    result = _graphql(query, variables)
    if "errors" in result:
        raise RuntimeError(result["errors"][0].get("message", str(result["errors"])))
    return result.get("data", {}).get("writePost")


def edit_post(
    post_id: str,
    title: str,
    body: str,
    tags: list[str],
    is_private: bool = False,
    url_slug: str = "",
    description: str = "",
    series_id: str | None = None,
) -> dict | None:
    """기존 글을 수정한다."""
    query = """mutation EditPost($input: EditPostInput!) {
        editPost(input: $input) {
            id title url_slug released_at updated_at
        }
    }"""
    variables = {
        "input": {
            "id": post_id,
            "title": title,
            "body": body,
            "tags": tags,
            "is_markdown": True,
            "is_temp": False,
            "is_private": is_private,
            "url_slug": url_slug,
            "meta": {"short_description": description},
        }
    }
    if series_id:
        variables["input"]["series_id"] = series_id

    result = _graphql(query, variables)
    if "errors" in result:
        raise RuntimeError(result["errors"][0].get("message", str(result["errors"])))
    return result.get("data", {}).get("editPost")
