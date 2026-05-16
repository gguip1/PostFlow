import json
import mimetypes
import urllib.error
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

from vcli.adapters.velog.auth import get_auth_path

VELOG_GRAPHQL = "https://v3.velog.io/graphql"
VELOG_IMAGE_UPLOAD = "https://v3.velog.io/api/files/v3/upload"


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
    access_token = _get_access_token()
    fields = {"type": image_type}
    if ref_id:
        fields["ref_id"] = ref_id

    body, boundary = _multipart_form_data(fields, "image", path)
    req = Request(
        VELOG_IMAGE_UPLOAD,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
            "Cookie": f"access_token={access_token}",
        },
    )

    try:
        with urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise PermissionError(
                "인증이 만료되었습니다. 'vcli login'으로 다시 로그인하세요."
            )
        raise ConnectionError(f"Velog 이미지 업로드 실패 (HTTP {e.code}): {e.reason}")
    except urllib.error.URLError as e:
        raise ConnectionError(f"Velog 이미지 업로드 실패: {e}")

    url = payload.get("path")
    if not url:
        raise RuntimeError("Velog 이미지 업로드 응답에 URL이 없습니다.")
    return url


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
