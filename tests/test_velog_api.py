import json
import tempfile
import unittest
import unittest.mock
import urllib.error
from email.message import Message
from pathlib import Path

import vcli.adapters.velog.api as velog_api
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


class VelogApiTests(unittest.TestCase):
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

    def test_get_user_posts_reads_pages_until_empty_page(self) -> None:
        calls: list[dict] = []

        def fake_graphql(query, variables=None):
            calls.append(variables)
            cursor = variables["input"].get("cursor")
            if cursor is None:
                return {"data": {"posts": [{"id": "post-2"}, {"id": "post-1"}]}}
            if cursor == "post-1":
                return {"data": {"posts": [{"id": "post-0"}]}}
            return {"data": {"posts": []}}

        with unittest.mock.patch.object(velog_api, "_graphql", fake_graphql):
            posts = velog_api.get_user_posts("me")

        self.assertEqual([post["id"] for post in posts], ["post-2", "post-1", "post-0"])
        self.assertEqual(
            [call["input"].get("cursor") for call in calls],
            [None, "post-1", "post-0"],
        )
        self.assertTrue(all(call["input"]["limit"] == 100 for call in calls))

    def test_get_user_posts_rejects_error_on_later_page(self) -> None:
        def fake_graphql(query, variables=None):
            if variables["input"].get("cursor") is None:
                return {"data": {"posts": [{"id": "post-1"}]}}
            return {"errors": [{"message": "page failed"}]}

        with unittest.mock.patch.object(velog_api, "_graphql", fake_graphql):
            with self.assertRaisesRegex(RuntimeError, "page failed"):
                velog_api.get_user_posts("me")

    def test_get_user_posts_rejects_repeated_page(self) -> None:
        def fake_graphql(query, variables=None):
            return {"data": {"posts": [{"id": "post-1"}]}}

        with unittest.mock.patch.object(velog_api, "_graphql", fake_graphql):
            with self.assertRaisesRegex(RuntimeError, "중복"):
                velog_api.get_user_posts("me")

    def test_get_user_posts_rejects_malformed_page(self) -> None:
        with unittest.mock.patch.object(
            velog_api,
            "_graphql",
            lambda query, variables=None: {"data": {}},
        ):
            with self.assertRaisesRegex(RuntimeError, "응답이 올바르지 않습니다"):
                velog_api.get_user_posts("me")

    def test_graphql_sends_refresh_token_and_saves_rotated_tokens(self) -> None:
        velog_auth.login_with_token("access-old", "refresh-old")
        headers = Message()
        headers.add_header("Set-Cookie", "access_token=access-new; Path=/; HttpOnly")
        headers.add_header("Set-Cookie", "refresh_token=refresh-new; Path=/; HttpOnly")
        response = FakeResponse({"data": {"currentUser": {"id": "user-1"}}}, headers)

        with unittest.mock.patch.object(velog_api, "urlopen", return_value=response) as mocked:
            result = velog_api._graphql("{ currentUser { id } }")

        self.assertEqual(result["data"]["currentUser"]["id"], "user-1")
        request = mocked.call_args.args[0]
        self.assertEqual(
            request.get_header("Cookie"),
            "access_token=access-old; refresh_token=refresh-old",
        )
        self.assertEqual(
            velog_auth.load_auth_cookies(),
            {"access_token": "access-new", "refresh_token": "refresh-new"},
        )

    def test_graphql_retries_once_when_401_rotates_tokens(self) -> None:
        velog_auth.login_with_token("access-old", "refresh-old")
        headers = Message()
        headers.add_header("Set-Cookie", "access_token=access-new; Path=/; HttpOnly")
        headers.add_header("Set-Cookie", "refresh_token=refresh-new; Path=/; HttpOnly")
        unauthorized = urllib.error.HTTPError(
            velog_api.VELOG_GRAPHQL,
            401,
            "Unauthorized",
            headers,
            None,
        )
        self.addCleanup(unauthorized.close)
        requests = []

        def fake_urlopen(request, timeout=30):
            requests.append(request)
            if len(requests) == 1:
                raise unauthorized
            return FakeResponse({"data": {"currentUser": {"id": "user-1"}}})

        with unittest.mock.patch.object(velog_api, "urlopen", fake_urlopen):
            result = velog_api._graphql("{ currentUser { id } }")

        self.assertEqual(result["data"]["currentUser"]["id"], "user-1")
        self.assertEqual(len(requests), 2)
        self.assertEqual(
            requests[1].get_header("Cookie"),
            "access_token=access-new; refresh_token=refresh-new",
        )

    def test_graphql_does_not_retry_401_without_new_tokens(self) -> None:
        velog_auth.login_with_token("access-old", "refresh-old")
        unauthorized = urllib.error.HTTPError(
            velog_api.VELOG_GRAPHQL,
            401,
            "Unauthorized",
            Message(),
            None,
        )
        self.addCleanup(unauthorized.close)

        with unittest.mock.patch.object(
            velog_api,
            "urlopen",
            side_effect=unauthorized,
        ) as mocked:
            with self.assertRaisesRegex(PermissionError, "vcli login"):
                velog_api._graphql("{ currentUser { id } }")

        self.assertEqual(mocked.call_count, 1)

    def test_image_upload_sends_refresh_token_and_saves_rotated_tokens(self) -> None:
        velog_auth.login_with_token("access-old", "refresh-old")
        image_path = Path(self.temp_dir.name) / "image.png"
        image_path.write_bytes(b"image-bytes")
        headers = Message()
        headers.add_header("Set-Cookie", "access_token=access-new; Path=/; HttpOnly")
        headers.add_header("Set-Cookie", "refresh_token=refresh-new; Path=/; HttpOnly")
        response = FakeResponse({"path": "https://velog.velcdn.com/image.png"}, headers)

        with unittest.mock.patch.object(velog_api, "urlopen", return_value=response) as mocked:
            url = velog_api.upload_image_file(image_path)

        self.assertEqual(url, "https://velog.velcdn.com/image.png")
        request = mocked.call_args.args[0]
        self.assertEqual(
            request.get_header("Cookie"),
            "access_token=access-old; refresh_token=refresh-old",
        )
        self.assertEqual(
            velog_auth.load_auth_cookies(),
            {"access_token": "access-new", "refresh_token": "refresh-new"},
        )

    def test_image_upload_retries_once_when_401_rotates_tokens(self) -> None:
        velog_auth.login_with_token("access-old", "refresh-old")
        image_path = Path(self.temp_dir.name) / "image.png"
        image_path.write_bytes(b"image-bytes")
        headers = Message()
        headers.add_header("Set-Cookie", "access_token=access-new; Path=/; HttpOnly")
        headers.add_header("Set-Cookie", "refresh_token=refresh-new; Path=/; HttpOnly")
        unauthorized = urllib.error.HTTPError(
            velog_api.VELOG_IMAGE_UPLOAD,
            401,
            "Unauthorized",
            headers,
            None,
        )
        self.addCleanup(unauthorized.close)
        requests = []

        def fake_urlopen(request, timeout=60):
            requests.append(request)
            if len(requests) == 1:
                raise unauthorized
            return FakeResponse({"path": "https://velog.velcdn.com/image.png"})

        with unittest.mock.patch.object(velog_api, "urlopen", fake_urlopen):
            url = velog_api.upload_image_file(image_path)

        self.assertEqual(url, "https://velog.velcdn.com/image.png")
        self.assertEqual(len(requests), 2)
        self.assertEqual(
            requests[1].get_header("Cookie"),
            "access_token=access-new; refresh_token=refresh-new",
        )

    def test_image_upload_does_not_retry_401_without_new_tokens(self) -> None:
        velog_auth.login_with_token("access-old", "refresh-old")
        image_path = Path(self.temp_dir.name) / "image.png"
        image_path.write_bytes(b"image-bytes")
        unauthorized = urllib.error.HTTPError(
            velog_api.VELOG_IMAGE_UPLOAD,
            401,
            "Unauthorized",
            Message(),
            None,
        )
        self.addCleanup(unauthorized.close)

        with unittest.mock.patch.object(
            velog_api,
            "urlopen",
            side_effect=unauthorized,
        ) as mocked:
            with self.assertRaisesRegex(PermissionError, "refresh_token"):
                velog_api.upload_image_file(image_path)

        self.assertEqual(mocked.call_count, 1)

    def test_image_upload_without_auth_file_shows_login_guidance(self) -> None:
        image_path = Path(self.temp_dir.name) / "image.png"
        image_path.write_bytes(b"image-bytes")
        unauthorized = urllib.error.HTTPError(
            velog_api.VELOG_IMAGE_UPLOAD,
            401,
            "Unauthorized",
            Message(),
            None,
        )
        self.addCleanup(unauthorized.close)

        with unittest.mock.patch.object(
            velog_api,
            "urlopen",
            side_effect=unauthorized,
        ) as mocked:
            with self.assertRaisesRegex(PermissionError, "vcli login"):
                velog_api.upload_image_file(image_path)

        self.assertEqual(mocked.call_count, 1)


if __name__ == "__main__":
    unittest.main()
