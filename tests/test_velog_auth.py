import json
import stat
import tempfile
import unittest
import unittest.mock
from email.message import Message
from pathlib import Path

import vcli.adapters.velog.auth as velog_auth


class FakeResponse:
    def __init__(self, payload: dict, headers: Message | None = None) -> None:
        self._body = json.dumps(payload).encode()
        self.headers = headers or Message()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self) -> bytes:
        return self._body


class VelogAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.auth_path = Path(self.temp_dir.name) / ".vcli" / "velog-auth.json"
        self.path_patch = unittest.mock.patch.object(
            velog_auth,
            "get_auth_path",
            lambda root=None: self.auth_path,
        )
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)

    def test_login_saves_both_tokens_with_private_permissions(self) -> None:
        velog_auth.login_with_token("access-old", "refresh-old")

        self.assertEqual(
            velog_auth.get_auth_cookie_header(),
            "access_token=access-old; refresh_token=refresh-old",
        )
        mode = stat.S_IMODE(self.auth_path.stat().st_mode)
        self.assertEqual(mode, 0o600)

    def test_check_auth_persists_rotated_tokens(self) -> None:
        velog_auth.login_with_token("access-old", "refresh-old")
        headers = Message()
        headers.add_header("Set-Cookie", "access_token=access-new; Path=/; HttpOnly")
        headers.add_header("Set-Cookie", "refresh_token=refresh-new; Path=/; HttpOnly")
        response = FakeResponse(
            {"data": {"currentUser": {"id": "user-1", "username": "me"}}},
            headers,
        )

        with unittest.mock.patch.object(velog_auth, "urlopen", return_value=response) as mocked:
            self.assertTrue(velog_auth.check_auth())

        request = mocked.call_args.args[0]
        self.assertEqual(
            request.get_header("Cookie"),
            "access_token=access-old; refresh_token=refresh-old",
        )
        self.assertEqual(
            velog_auth.load_auth_cookies(),
            {"access_token": "access-new", "refresh_token": "refresh-new"},
        )


if __name__ == "__main__":
    unittest.main()
