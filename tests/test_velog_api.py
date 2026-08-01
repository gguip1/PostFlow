import unittest
import unittest.mock

import vcli.adapters.velog.api as velog_api


class VelogApiTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
