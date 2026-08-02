import json
import os
import tempfile
import urllib.error
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from vcli.core.workspace import workspace_dir


AUTH_FILENAME = "velog-auth.json"


def get_auth_path(root: Path | None = None) -> Path:
    if root is None:
        from vcli.core.workspace import find_workspace_root

        root = find_workspace_root()
    return workspace_dir(root) / AUTH_FILENAME


def auth_exists(root: Path | None = None) -> bool:
    return get_auth_path(root).exists()


def _load_storage(root: Path | None = None) -> dict[str, Any]:
    try:
        with open(get_auth_path(root), encoding="utf-8") as f:
            storage = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return storage if isinstance(storage, dict) else {}


def _write_storage(storage: dict[str, Any], root: Path | None = None) -> None:
    auth_path = get_auth_path(root)
    auth_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=auth_path.parent,
            prefix=f".{auth_path.name}.",
            delete=False,
        ) as f:
            json.dump(storage, f)
            f.flush()
            os.fsync(f.fileno())
            temp_path = Path(f.name)
        temp_path.chmod(0o600)
        os.replace(temp_path, auth_path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def load_auth_cookies(root: Path | None = None) -> dict[str, str]:
    """저장된 Velog 인증 쿠키를 이름과 값으로 반환한다."""
    storage = _load_storage(root)
    stored_cookies = storage.get("cookies", [])
    if not isinstance(stored_cookies, list):
        return {}
    return {
        cookie["name"]: cookie["value"]
        for cookie in stored_cookies
        if isinstance(cookie, dict)
        and cookie.get("name") in {"access_token", "refresh_token"}
        and isinstance(cookie.get("value"), str)
    }


def get_auth_cookie_header(root: Path | None = None) -> str:
    """Velog 요청에 사용할 인증 Cookie 헤더를 만든다."""
    cookies = load_auth_cookies(root)
    return "; ".join(
        f"{name}={cookies[name]}"
        for name in ("access_token", "refresh_token")
        if cookies.get(name)
    )


def update_auth_from_headers(headers: Any, root: Path | None = None) -> bool:
    """응답의 Set-Cookie에 회전된 인증 토큰이 있으면 로컬에 저장한다."""
    if headers is None:
        return False

    if hasattr(headers, "get_all"):
        raw_headers = headers.get_all("Set-Cookie") or []
    else:
        raw_header = headers.get("Set-Cookie")
        raw_headers = [raw_header] if raw_header else []
    received: dict[str, str] = {}
    for raw_header in raw_headers:
        parsed = SimpleCookie()
        parsed.load(raw_header)
        for name in ("access_token", "refresh_token"):
            if name in parsed:
                received[name] = parsed[name].value

    if not received:
        return False

    storage = _load_storage(root)
    changed = False
    rotated = False
    stored_cookies = storage.get("cookies")
    if not isinstance(stored_cookies, list):
        stored_cookies = []
        storage["cookies"] = stored_cookies
    by_name = {
        cookie.get("name"): cookie
        for cookie in stored_cookies
        if isinstance(cookie, dict)
    }
    for name, value in received.items():
        cookie = by_name.get(name)
        if not value:
            if cookie is not None:
                stored_cookies.remove(cookie)
                changed = True
            continue
        if cookie is None:
            cookie = {
                "name": name,
                "domain": ".velog.io",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
            stored_cookies.append(cookie)
        if cookie.get("value") != value:
            cookie["value"] = value
            changed = True
            rotated = True

    if changed:
        _write_storage(storage, root)
    return rotated


def check_auth(root: Path | None = None) -> bool:
    """저장된 토큰이 유효한지 Velog GraphQL API로 확인한다."""
    auth_path = get_auth_path(root)
    if not auth_path.exists():
        return False

    for attempt in range(2):
        cookie_header = get_auth_cookie_header(root)
        if not cookie_header:
            return False

        query = json.dumps({"query": "{ currentUser { id username } }"}).encode()
        req = Request(
            "https://v3.velog.io/graphql",
            data=query,
            headers={
                "Content-Type": "application/json",
                "Cookie": cookie_header,
            },
        )
        try:
            with urlopen(req, timeout=10) as resp:
                update_auth_from_headers(resp.headers, root)
                result = json.loads(resp.read())
                user = result.get("data", {}).get("currentUser")
                return user is not None
        except urllib.error.HTTPError as error:
            tokens_rotated = update_auth_from_headers(error.headers, root)
            if error.code == 401 and tokens_rotated and attempt == 0:
                continue
            return False
        except Exception:
            return False

    return False


def login_with_token(access_token: str, refresh_token: str, root: Path | None = None) -> None:
    """사용자가 직접 복사한 토큰으로 세션을 저장한다."""
    storage = {
        "cookies": [
            {
                "name": "access_token",
                "value": access_token,
                "domain": ".velog.io",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            },
            {
                "name": "refresh_token",
                "value": refresh_token,
                "domain": ".velog.io",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            },
        ],
        "origins": [],
    }

    _write_storage(storage, root)
