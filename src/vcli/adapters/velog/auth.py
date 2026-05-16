import json
from pathlib import Path
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


def check_auth(root: Path | None = None) -> bool:
    """저장된 토큰이 유효한지 Velog GraphQL API로 확인한다."""
    auth_path = get_auth_path(root)
    if not auth_path.exists():
        return False

    try:
        with open(auth_path, encoding="utf-8") as f:
            storage = json.load(f)

        cookies = {c["name"]: c["value"] for c in storage.get("cookies", [])}
        access_token = cookies.get("access_token", "")
        if not access_token:
            return False

        query = json.dumps({"query": "{ currentUser { id username } }"}).encode()
        req = Request(
            "https://v3.velog.io/graphql",
            data=query,
            headers={
                "Content-Type": "application/json",
                "Cookie": f"access_token={access_token}",
            },
        )
        with urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            user = result.get("data", {}).get("currentUser")
            return user is not None
    except Exception:
        return False


def login_with_token(access_token: str, refresh_token: str, root: Path | None = None) -> None:
    """사용자가 직접 복사한 토큰으로 세션을 저장한다."""
    auth_path = get_auth_path(root)
    auth_path.parent.mkdir(parents=True, exist_ok=True)

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

    with open(auth_path, "w", encoding="utf-8") as f:
        json.dump(storage, f)
