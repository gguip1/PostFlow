import json
import mimetypes
import urllib.error
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

from vcli.adapters.velog.auth import get_auth_cookie_header, update_auth_from_headers

VELOG_GRAPHQL = "https://v3.velog.io/graphql"
VELOG_IMAGE_UPLOAD = "https://v3.velog.io/api/files/v3/upload"
AUTH_REFRESH_ERROR = (
    "인증 세션을 갱신할 수 없습니다. refresh_token이 없거나 만료되었습니다. "
    "'vcli login'으로 다시 로그인하세요."
)


def _graphql(query: str, variables: dict | None = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    for attempt in range(2):
        req = Request(
            VELOG_GRAPHQL,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Cookie": get_auth_cookie_header(),
            },
        )
        try:
            with urlopen(req, timeout=30) as resp:
                update_auth_from_headers(resp.headers)
                body = resp.read()
                if not body:
                    return {}
                return json.loads(body)
        except urllib.error.HTTPError as e:
            tokens_changed = update_auth_from_headers(e.headers)
            if e.code == 401 and tokens_changed and attempt == 0:
                continue
            if e.code == 401:
                raise PermissionError(AUTH_REFRESH_ERROR) from e
            raise ConnectionError(f"Velog API 오류 (HTTP {e.code}): {e.reason}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Velog API에 연결할 수 없습니다. 네트워크 상태를 확인하세요.\n원인: {e}"
            ) from e

    raise PermissionError(AUTH_REFRESH_ERROR)


def _multipart_form_data(
    fields: dict[str, str],
    file_field: str,
    file_path: Path,
) -> tuple[bytes, str]:
    boundary = f"----vcli-{uuid4().hex}"
    filename = file_path.name
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    parts: list[bytes] = []

    for name, value in fields.items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode(),
                b"\r\n",
            ]
        )

    parts.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{filename}"\r\n'
            ).encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(parts), boundary


def upload_image_file(
    path: Path,
    image_type: str = "post",
    ref_id: str | None = None,
) -> str:
    fields = {"type": image_type}
    if ref_id:
        fields["ref_id"] = ref_id

    body, boundary = _multipart_form_data(fields, "image", path)
    payload: dict = {}
    for attempt in range(2):
        req = Request(
            VELOG_IMAGE_UPLOAD,
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
                "Cookie": get_auth_cookie_header(),
            },
        )

        try:
            with urlopen(req, timeout=60) as resp:
                update_auth_from_headers(resp.headers)
                payload = json.loads(resp.read() or b"{}")
                break
        except urllib.error.HTTPError as e:
            tokens_changed = update_auth_from_headers(e.headers)
            if e.code == 401 and tokens_changed and attempt == 0:
                continue
            if e.code == 401:
                raise PermissionError(AUTH_REFRESH_ERROR) from e
            raise ConnectionError(
                f"Velog 이미지 업로드 실패 (HTTP {e.code}): {e.reason}"
            ) from e
        except urllib.error.URLError as e:
            raise ConnectionError(f"Velog 이미지 업로드 실패: {e}") from e

    url = payload.get("path")
    if not url:
        raise RuntimeError("Velog 이미지 업로드 응답에 URL이 없습니다.")
    return url


def get_current_user() -> dict | None:
    result = _graphql("{ currentUser { id username } }")
    return result.get("data", {}).get("currentUser")


def get_user_posts(username: str) -> list[dict]:
    """사용자의 모든 글을 가져온다."""
    query = """query GetUserPosts($input: GetPostsInput!) {
        posts(input: $input) {
            id title url_slug tags is_private
            released_at updated_at short_description body
            series { id name }
        }
    }"""
    posts: list[dict] = []
    seen_ids: set[str] = set()
    cursor: str | None = None

    while True:
        input_data: dict[str, object] = {"username": username, "limit": 100}
        if cursor:
            input_data["cursor"] = cursor

        result = _graphql(query, {"input": input_data})
        if result.get("errors"):
            message = result["errors"][0].get("message", str(result["errors"]))
            raise RuntimeError(
                f"Velog 글 목록을 완전히 가져오지 못했습니다: {message}"
            )

        data = result.get("data")
        page = data.get("posts") if isinstance(data, dict) else None
        if not isinstance(page, list):
            raise RuntimeError("Velog 글 목록 응답이 올바르지 않습니다.")
        if not page:
            return posts

        for post in page:
            if not isinstance(post, dict) or not post.get("id"):
                raise RuntimeError("Velog 글 목록에 식별자가 없는 항목이 있습니다.")
            if post["id"] in seen_ids:
                raise RuntimeError(
                    "Velog 글 목록 페이지가 중복되어 전체 목록을 확인할 수 없습니다."
                )
            seen_ids.add(post["id"])
            posts.append(post)

        cursor = page[-1]["id"]


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
