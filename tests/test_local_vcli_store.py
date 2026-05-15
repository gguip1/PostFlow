import os
import shutil
import unittest
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
        self.assertTrue((self.tmp_root / ".vcli" / "posts").is_dir())

        registry = read_yaml(self.tmp_root / ".vcli" / "registry.yaml")
        self.assertEqual(registry, {"version": 1, "posts": []})

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

    def test_sync_entry_with_meta_does_not_refresh_last_synced_hash(self) -> None:
        from vcli.core.registry import RegistryEntry, find_entry, sync_entry_with_meta, upsert_entry
        from vcli.models import Meta

        self.runner.invoke(app, ["init"])
        post_dir = self.tmp_root / ".vcli" / "posts" / "local-post"
        post_dir.mkdir(parents=True)
        (post_dir / "meta.yaml").write_text("title: Local Post\nslug: local-post\n", encoding="utf-8")
        (post_dir / "content.md").write_text("# Changed Locally\n", encoding="utf-8")
        upsert_entry(
            self.tmp_root,
            RegistryEntry(
                slug="local-post",
                velog_id="velog-1",
                url="https://velog.io/@me/local-post",
                last_synced_hash="remote-baseline",
                last_synced_at="2026-05-16T12:00:00Z",
            ),
        )

        sync_entry_with_meta(self.tmp_root, Meta(title="Renamed", slug="local-post"))

        entry = find_entry(self.tmp_root, "local-post")
        self.assertEqual(entry.last_synced_hash, "remote-baseline")
