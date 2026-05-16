import os
import shutil
import unittest
import unittest.mock
from pathlib import Path
from uuid import uuid4

from typer.testing import CliRunner

from vcli.main import app
from vcli.utils.fs import read_yaml


class LocalVcliStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_root = Path(__file__).resolve().parent / ".tmp" / uuid4().hex
        self.tmp_root.mkdir(parents=True)
        self.previous_cwd = Path.cwd()
        os.chdir(self.tmp_root)
        self.runner = CliRunner()
        self.addCleanup(os.chdir, self.previous_cwd)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_init_creates_local_vcli_store(self) -> None:
        result = self.runner.invoke(app, ["init"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertTrue((self.tmp_root / ".vcli" / "config.yaml").exists())
        self.assertTrue((self.tmp_root / ".vcli" / "registry.yaml").exists())
        self.assertTrue((self.tmp_root / ".vcli" / "uploads.yaml").exists())
        self.assertTrue((self.tmp_root / ".vcli" / "posts").is_dir())

        registry = read_yaml(self.tmp_root / ".vcli" / "registry.yaml")
        self.assertEqual(registry, {"version": 1, "posts": []})
        uploads = read_yaml(self.tmp_root / ".vcli" / "uploads.yaml")
        self.assertEqual(uploads, {"version": 1, "uploads": []})

    def test_calculate_status_is_draft_without_velog_id(self) -> None:
        from vcli.core.registry import RegistryEntry, calculate_status

        self.runner.invoke(app, ["init"])
        post_dir = self.tmp_root / ".vcli" / "posts" / "local-draft"
        post_dir.mkdir(parents=True)
        (post_dir / "meta.yaml").write_text("title: Local Draft\nslug: local-draft\n", encoding="utf-8")
        (post_dir / "content.md").write_text("# Local Draft\n", encoding="utf-8")

        self.assertEqual(calculate_status(self.tmp_root, RegistryEntry(slug="local-draft")), "draft")

    def test_calculate_status_is_modified_when_hash_differs(self) -> None:
        from vcli.core.hashing import hash_post
        from vcli.core.registry import RegistryEntry, calculate_status

        self.runner.invoke(app, ["init"])
        post_dir = self.tmp_root / ".vcli" / "posts" / "local-post"
        post_dir.mkdir(parents=True)
        (post_dir / "meta.yaml").write_text("title: Local Post\nslug: local-post\n", encoding="utf-8")
        (post_dir / "content.md").write_text("# Local Post\n", encoding="utf-8")

        entry = RegistryEntry(
            slug="local-post",
            velog_id="velog-1",
            url="https://velog.io/@me/local-post",
            last_synced_hash=hash_post(post_dir),
            last_synced_at="2026-05-16T12:00:00Z",
        )
        (post_dir / "content.md").write_text("# Changed\n", encoding="utf-8")

        self.assertEqual(calculate_status(self.tmp_root, entry), "modified")

    def test_hash_post_raises_when_required_file_is_missing(self) -> None:
        from vcli.core.hashing import hash_post

        self.runner.invoke(app, ["init"])
        post_dir = self.tmp_root / ".vcli" / "posts" / "broken-post"
        post_dir.mkdir(parents=True)
        (post_dir / "meta.yaml").write_text("title: Broken Post\nslug: broken-post\n", encoding="utf-8")

        missing_path = post_dir / "content.md"
        with self.assertRaisesRegex(FileNotFoundError, str(missing_path).replace("\\", "\\\\")):
            hash_post(post_dir)

    def test_find_entry_matches_slug_only(self) -> None:
        from vcli.core.registry import find_entry

        self.runner.invoke(app, ["init"])
        registry_path = self.tmp_root / ".vcli" / "registry.yaml"
        registry_path.write_text(
            "version: 1\n"
            "posts:\n"
            "  - slug: canonical-slug\n"
            "    id: legacy-id\n"
            "    velog_id: velog-1\n",
            encoding="utf-8",
        )

        self.assertEqual(find_entry(self.tmp_root, "canonical-slug").slug, "canonical-slug")
        self.assertIsNone(find_entry(self.tmp_root, "legacy-id"))
        self.assertIsNone(find_entry(self.tmp_root, "legacy"))

    def test_create_writes_post_under_local_vcli_posts(self) -> None:
        self.runner.invoke(app, ["init"])

        result = self.runner.invoke(
            app,
            [
                "create",
                "agent-post",
                "--title",
                "Agent Post",
                "--tags",
                "velog,cli",
                "--visibility",
                "private",
            ],
        )

        self.assertEqual(result.exit_code, 0, result.stdout)
        post_dir = self.tmp_root / ".vcli" / "posts" / "agent-post"
        self.assertTrue((post_dir / "content.md").exists())
        meta = read_yaml(post_dir / "meta.yaml")
        self.assertEqual(meta["title"], "Agent Post")
        self.assertEqual(meta["slug"], "agent-post")
        self.assertEqual(meta["tags"], ["velog", "cli"])
        self.assertEqual(meta["visibility"], "private")

    def test_create_with_required_arguments_does_not_prompt_for_optional_fields(self) -> None:
        self.runner.invoke(app, ["init"])

        result = self.runner.invoke(
            app,
            ["create", "minimal-post", "--title", "Minimal Post"],
        )

        self.assertEqual(result.exit_code, 0, result.stdout)
        post_dir = self.tmp_root / ".vcli" / "posts" / "minimal-post"
        meta = read_yaml(post_dir / "meta.yaml")
        self.assertEqual(meta["title"], "Minimal Post")
        self.assertEqual(meta["tags"], [])
        self.assertEqual(meta["description"], "")

    def test_status_command_shows_calculated_states(self) -> None:
        from vcli.core.hashing import hash_post
        from vcli.core.registry import RegistryEntry, upsert_entry

        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["create", "draft-post", "--title", "Draft Post"])
        self.runner.invoke(app, ["create", "synced-post", "--title", "Synced Post"])
        self.runner.invoke(app, ["create", "modified-post", "--title", "Modified Post"])

        synced_dir = self.tmp_root / ".vcli" / "posts" / "synced-post"
        upsert_entry(
            self.tmp_root,
            RegistryEntry(
                slug="synced-post",
                velog_id="velog-synced",
                url="https://velog.io/@me/synced-post",
                last_synced_hash=hash_post(synced_dir),
                last_synced_at="2026-05-16T12:00:00Z",
            ),
        )

        modified_dir = self.tmp_root / ".vcli" / "posts" / "modified-post"
        modified_hash = hash_post(modified_dir)
        (modified_dir / "content.md").write_text("# Changed\n", encoding="utf-8")
        upsert_entry(
            self.tmp_root,
            RegistryEntry(
                slug="modified-post",
                velog_id="velog-modified",
                url="https://velog.io/@me/modified-post",
                last_synced_hash=modified_hash,
                last_synced_at="2026-05-16T12:00:00Z",
            ),
        )

        result = self.runner.invoke(app, ["status"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertIn("draft", result.stdout)
        self.assertIn("draft-post", result.stdout)
        self.assertIn("synced", result.stdout)
        self.assertIn("synced-post", result.stdout)
        self.assertIn("modified", result.stdout)
        self.assertIn("modified-post", result.stdout)

    def test_list_shows_calculated_status_and_meta_title(self) -> None:
        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["create", "listed-post", "--title", "Listed Post"])

        result = self.runner.invoke(app, ["list"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertIn("draft", result.stdout)
        self.assertIn("listed-post", result.stdout)
        self.assertIn("Listed Post", result.stdout)

    def test_check_accepts_local_draft_without_legacy_ids(self) -> None:
        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["create", "check-me", "--title", "Check Me"])

        result = self.runner.invoke(app, ["check"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertIn("검증을 통과했습니다", result.stdout)

    def test_pull_imports_remote_post_and_marks_synced(self) -> None:
        import vcli.commands.import_posts as pull_command

        self.runner.invoke(app, ["init"])
        remote_posts = [
            {
                "id": "velog-1",
                "title": "Remote Post",
                "url_slug": "remote-post",
                "tags": ["velog"],
                "is_private": False,
                "released_at": "2026-05-16T12:00:00Z",
                "updated_at": "2026-05-16T12:00:00Z",
                "short_description": "Remote description",
                "body": "# Remote Post\n",
                "series": None,
            }
        ]

        with unittest.mock.patch.object(pull_command, "check_auth", lambda: True), \
             unittest.mock.patch.object(pull_command, "get_current_user", lambda: {"username": "me"}), \
             unittest.mock.patch.object(pull_command, "get_user_posts", lambda username: remote_posts):
            result = self.runner.invoke(app, ["pull"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        post_dir = self.tmp_root / ".vcli" / "posts" / "remote-post"
        self.assertTrue((post_dir / "content.md").exists())

        registry = read_yaml(self.tmp_root / ".vcli" / "registry.yaml")
        self.assertEqual(registry["posts"][0]["slug"], "remote-post")
        self.assertEqual(registry["posts"][0]["velog_id"], "velog-1")
        self.assertEqual(registry["posts"][0]["url"], "https://velog.io/@me/remote-post")
        self.assertIsNotNone(registry["posts"][0]["last_synced_hash"])

        status_result = self.runner.invoke(app, ["status"])
        self.assertIn("synced", status_result.stdout)
        self.assertIn("remote-post", status_result.stdout)

    def test_find_image_urls_ignores_markdown_images_inside_fenced_code_blocks(self) -> None:
        from vcli.commands.import_posts import _find_image_urls

        body = (
            "README에 한 줄이면 끝이에요.\n\n"
            "```\n"
            "![My Music](https://sound-badge.vercel.app/api/card.svg?url=유튜브_URL&theme=stream)\n"
            "```\n\n"
            "![real](https://example.com/image.png)\n"
        )

        self.assertEqual(_find_image_urls(body), ["https://example.com/image.png"])

    def test_download_images_reports_processed_images(self) -> None:
        import vcli.commands.import_posts as pull_command

        self.runner.invoke(app, ["init"])
        post_dir = self.tmp_root / ".vcli" / "posts" / "image-post"
        post_dir.mkdir(parents=True)
        messages: list[str] = []

        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return None

            def read(self):
                return b"image-bytes"

        def fake_urlopen(req, timeout=30):
            return DummyResponse()

        with unittest.mock.patch.object(pull_command, "urlopen", fake_urlopen), \
             unittest.mock.patch.object(pull_command.logger, "info", messages.append):
            result = pull_command._download_images(
                "![image](https://example.com/image.png)",
                post_dir,
            )

        self.assertIn("./images/image-1-", result)
        self.assertEqual(messages, ["이미지 처리 완료: 1/1"])

    def test_pull_skips_modified_local_post(self) -> None:
        import vcli.commands.import_posts as pull_command
        from vcli.core.hashing import hash_post
        from vcli.core.registry import RegistryEntry, upsert_entry

        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["create", "remote-post", "--title", "Remote Post"])

        post_dir = self.tmp_root / ".vcli" / "posts" / "remote-post"
        baseline_hash = hash_post(post_dir)
        (post_dir / "content.md").write_text("# Local Edit\n", encoding="utf-8")
        upsert_entry(
            self.tmp_root,
            RegistryEntry(
                slug="remote-post",
                velog_id="velog-1",
                url="https://velog.io/@me/remote-post",
                last_synced_hash=baseline_hash,
                last_synced_at="2026-05-16T12:00:00Z",
            ),
        )

        remote_posts = [
            {
                "id": "velog-1",
                "title": "Remote Post",
                "url_slug": "remote-post",
                "tags": ["velog"],
                "is_private": False,
                "released_at": "2026-05-16T12:00:00Z",
                "updated_at": "2026-05-16T12:30:00Z",
                "short_description": "Remote description",
                "body": "# Remote Edit\n",
                "series": None,
            }
        ]

        with unittest.mock.patch.object(pull_command, "check_auth", lambda: True), \
             unittest.mock.patch.object(pull_command, "get_current_user", lambda: {"username": "me"}), \
             unittest.mock.patch.object(pull_command, "get_user_posts", lambda username: remote_posts):
            result = self.runner.invoke(app, ["pull"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertEqual((post_dir / "content.md").read_text(encoding="utf-8"), "# Local Edit\n")
        self.assertIn("수정된 로컬 글은 덮어쓰지 않고 건너뜁니다", result.stdout)

    def test_pull_refreshes_registry_entry_with_missing_local_files(self) -> None:
        import vcli.commands.import_posts as pull_command
        from vcli.core.registry import RegistryEntry, upsert_entry

        self.runner.invoke(app, ["init"])
        upsert_entry(
            self.tmp_root,
            RegistryEntry(
                slug="missing-local",
                velog_id="velog-1",
                url="https://velog.io/@me/missing-local",
                last_synced_hash="old-hash",
                last_synced_at="2026-05-16T12:00:00Z",
            ),
        )

        remote_posts = [
            {
                "id": "velog-1",
                "title": "Missing Local",
                "url_slug": "missing-local",
                "tags": ["velog"],
                "is_private": False,
                "released_at": "2026-05-16T12:00:00Z",
                "updated_at": "2026-05-16T12:30:00Z",
                "short_description": "Remote description",
                "body": "# Restored\n",
                "series": None,
            }
        ]

        with unittest.mock.patch.object(pull_command, "check_auth", lambda: True), \
             unittest.mock.patch.object(pull_command, "get_current_user", lambda: {"username": "me"}), \
             unittest.mock.patch.object(pull_command, "get_user_posts", lambda username: remote_posts):
            result = self.runner.invoke(app, ["pull"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        post_dir = self.tmp_root / ".vcli" / "posts" / "missing-local"
        self.assertEqual((post_dir / "content.md").read_text(encoding="utf-8"), "# Restored\n")
        self.assertTrue((post_dir / "meta.yaml").exists())
        self.assertIn("깨진 로컬 글을 원격 기준으로 다시 가져옵니다", result.stdout)

    def test_push_single_draft_creates_remote_and_marks_synced(self) -> None:
        import vcli.commands.push as push_command
        from vcli.adapters.velog.adapter import PublishResult

        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["create", "push-me", "--title", "Push Me"])

        class DummyAdapter:
            def create(self, post):
                return PublishResult(
                    success=True,
                    post_id="velog-created",
                    url="https://velog.io/@me/push-me",
                    published_at="2026-05-16T13:00:00Z",
                )

            def update(self, post_id, post):
                return self.create(post)

        with unittest.mock.patch.object(push_command, "check_auth", lambda: True), \
             unittest.mock.patch.object(push_command, "VelogAdapter", DummyAdapter):
            result = self.runner.invoke(app, ["push", "push-me"], input="y\n")

        self.assertEqual(result.exit_code, 0, result.stdout)
        registry = read_yaml(self.tmp_root / ".vcli" / "registry.yaml")
        entry = registry["posts"][0]
        self.assertEqual(entry["velog_id"], "velog-created")
        self.assertEqual(entry["url"], "https://velog.io/@me/push-me")
        self.assertIsNotNone(entry["last_synced_hash"])

        status_result = self.runner.invoke(app, ["status"])
        self.assertIn("synced", status_result.stdout)
        self.assertIn("push-me", status_result.stdout)

    def test_push_existing_remote_uses_update(self) -> None:
        import vcli.commands.push as push_command
        from vcli.adapters.velog.adapter import PublishResult
        from vcli.core.hashing import hash_post
        from vcli.core.registry import RegistryEntry, upsert_entry

        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["create", "update-me", "--title", "Update Me"])
        post_dir = self.tmp_root / ".vcli" / "posts" / "update-me"
        baseline_hash = hash_post(post_dir)
        (post_dir / "content.md").write_text("# Updated\n", encoding="utf-8")
        upsert_entry(
            self.tmp_root,
            RegistryEntry(
                slug="update-me",
                velog_id="velog-existing",
                url="https://velog.io/@me/update-me",
                last_synced_hash=baseline_hash,
                last_synced_at="2026-05-16T12:00:00Z",
            ),
        )

        calls: list[tuple[str, str | None]] = []

        class DummyAdapter:
            def create(self, post):
                calls.append(("create", None))
                return PublishResult(success=False, error="create should not be called")

            def update(self, post_id, post):
                calls.append(("update", post_id))
                return PublishResult(
                    success=True,
                    post_id=post_id,
                    url="https://velog.io/@me/update-me",
                    published_at="2026-05-16T13:00:00Z",
                )

        with unittest.mock.patch.object(push_command, "check_auth", lambda: True), \
             unittest.mock.patch.object(push_command, "VelogAdapter", DummyAdapter):
            result = self.runner.invoke(app, ["push", "update-me"], input="y\n")

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertEqual(calls, [("update", "velog-existing")])
        self.assertIn("원격 Velog 글", result.stdout)
        self.assertIn("https://velog.io/@me/update-me", result.stdout)
        self.assertIn("덮어씁니다", result.stdout)
        status_result = self.runner.invoke(app, ["status"])
        self.assertIn("synced", status_result.stdout)
        self.assertIn("update-me", status_result.stdout)

    def test_push_interactive_prompt_explains_space_selection(self) -> None:
        import vcli.commands.push as push_command

        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["create", "select-me", "--title", "Select Me"])

        captured_prompt: dict = {}

        class DummyPrompt:
            def execute(self):
                return []

        def fake_checkbox(**kwargs):
            captured_prompt.update(kwargs)
            return DummyPrompt()

        class DummyAdapter:
            pass

        with unittest.mock.patch.object(push_command, "check_auth", lambda: True), \
             unittest.mock.patch.object(push_command, "VelogAdapter", DummyAdapter), \
             unittest.mock.patch.object(push_command.inquirer, "checkbox", fake_checkbox):
            result = self.runner.invoke(app, ["push"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertIn("스페이스", captured_prompt.get("instruction", ""))
        self.assertIn("Enter", captured_prompt.get("instruction", ""))

    def test_push_without_slug_skips_registry_entries_with_missing_local_files(self) -> None:
        import vcli.commands.push as push_command
        from vcli.core.registry import RegistryEntry, upsert_entry

        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["create", "select-me", "--title", "Select Me"])
        upsert_entry(
            self.tmp_root,
            RegistryEntry(
                slug="missing-local",
                velog_id="velog-1",
                url="https://velog.io/@me/missing-local",
                last_synced_hash="old-hash",
                last_synced_at="2026-05-16T12:00:00Z",
            ),
        )

        captured_prompt: dict = {}

        class DummyPrompt:
            def execute(self):
                return []

        def fake_checkbox(**kwargs):
            captured_prompt.update(kwargs)
            return DummyPrompt()

        class DummyAdapter:
            pass

        with unittest.mock.patch.object(push_command, "check_auth", lambda: True), \
             unittest.mock.patch.object(push_command, "VelogAdapter", DummyAdapter), \
             unittest.mock.patch.object(push_command.inquirer, "checkbox", fake_checkbox):
            result = self.runner.invoke(app, ["push"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        choice_values = [choice["value"] for choice in captured_prompt["choices"]]
        self.assertEqual(choice_values, ["select-me"])
        self.assertIn("깨진 로컬 글을 건너뜁니다", result.stdout)
