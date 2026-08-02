import hashlib
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from typer.testing import CliRunner

from vcli.core.skills import bundled_skill_bytes
from vcli.main import app
from vcli.utils.fs import read_yaml, write_yaml


class SkillCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_root = Path(__file__).resolve().parent / ".tmp" / uuid4().hex
        self.tmp_root.mkdir(parents=True)
        self.previous_cwd = Path.cwd()
        os.chdir(self.tmp_root)
        self.runner = CliRunner()
        self.addCleanup(os.chdir, self.previous_cwd)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def init_workspace(self) -> None:
        result = self.runner.invoke(app, ["init"])
        self.assertEqual(result.exit_code, 0, result.stdout)

    def skill_path(self, target: str) -> Path:
        directory = ".agents" if target == "codex" else ".claude"
        return self.tmp_root / directory / "skills/vcli-manage-posts/SKILL.md"

    def test_install_copies_bundled_skill_to_both_harnesses(self) -> None:
        self.init_workspace()

        result = self.runner.invoke(app, ["skill", "install"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        for target in ("codex", "claude"):
            self.assertEqual(self.skill_path(target).read_bytes(), bundled_skill_bytes())
        self.assertFalse((self.tmp_root / "AGENTS.md").exists())
        self.assertFalse((self.tmp_root / "CLAUDE.md").exists())

        manifest = read_yaml(self.tmp_root / ".vcli/skills.yaml")
        targets = manifest["skills"]["vcli-manage-posts"]["targets"]
        self.assertEqual(set(targets), {"codex", "claude"})

        status = self.runner.invoke(app, ["skill", "status"])
        self.assertEqual(status.exit_code, 0, status.stdout)
        self.assertIn("codex: current", status.stdout)
        self.assertIn("claude: current", status.stdout)

    def test_install_does_not_overwrite_unmanaged_skill_without_force(self) -> None:
        self.init_workspace()
        path = self.skill_path("codex")
        path.parent.mkdir(parents=True)
        path.write_text("user-owned\n", encoding="utf-8")

        result = self.runner.invoke(
            app, ["skill", "install", "--target", "codex"]
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(path.read_text(encoding="utf-8"), "user-owned\n")
        self.assertFalse((self.tmp_root / ".vcli/skills.yaml").exists())

        forced = self.runner.invoke(
            app, ["skill", "install", "--target", "codex", "--force"]
        )
        self.assertEqual(forced.exit_code, 0, forced.stdout)
        self.assertEqual(path.read_bytes(), bundled_skill_bytes())

    def test_update_protects_user_changes_and_force_restores_bundle(self) -> None:
        self.init_workspace()
        installed = self.runner.invoke(
            app, ["skill", "install", "--target", "codex"]
        )
        self.assertEqual(installed.exit_code, 0, installed.stdout)
        path = self.skill_path("codex")
        path.write_text("user change\n", encoding="utf-8")

        result = self.runner.invoke(
            app, ["skill", "update", "--target", "codex"]
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(path.read_text(encoding="utf-8"), "user change\n")

        forced = self.runner.invoke(
            app, ["skill", "update", "--target", "codex", "--force"]
        )
        self.assertEqual(forced.exit_code, 0, forced.stdout)
        self.assertEqual(path.read_bytes(), bundled_skill_bytes())

    def test_force_install_replaces_matching_symlink_with_regular_file(self) -> None:
        self.init_workspace()
        path = self.skill_path("codex")
        path.parent.mkdir(parents=True)
        source = self.tmp_root / "matching-skill.md"
        source.write_bytes(bundled_skill_bytes())
        path.symlink_to(source)

        result = self.runner.invoke(
            app,
            ["skill", "install", "--target", "codex", "--force"],
        )

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertFalse(path.is_symlink())
        self.assertEqual(path.read_bytes(), bundled_skill_bytes())

    def test_force_update_replaces_matching_symlink_with_regular_file(self) -> None:
        self.init_workspace()
        installed = self.runner.invoke(
            app, ["skill", "install", "--target", "codex"]
        )
        self.assertEqual(installed.exit_code, 0, installed.stdout)
        path = self.skill_path("codex")
        source = self.tmp_root / "matching-skill.md"
        source.write_bytes(bundled_skill_bytes())
        path.unlink()
        path.symlink_to(source)

        result = self.runner.invoke(
            app,
            ["skill", "update", "--target", "codex", "--force"],
        )

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertFalse(path.is_symlink())
        self.assertEqual(path.read_bytes(), bundled_skill_bytes())

    def test_update_replaces_unchanged_outdated_installation(self) -> None:
        self.init_workspace()
        installed = self.runner.invoke(
            app, ["skill", "install", "--target", "codex"]
        )
        self.assertEqual(installed.exit_code, 0, installed.stdout)
        path = self.skill_path("codex")
        old_content = b"previous bundled skill\n"
        path.write_bytes(old_content)

        manifest_path = self.tmp_root / ".vcli/skills.yaml"
        manifest = read_yaml(manifest_path)
        record = manifest["skills"]["vcli-manage-posts"]["targets"]["codex"]
        record["installed_hash"] = hashlib.sha256(old_content).hexdigest()
        write_yaml(manifest_path, manifest)

        status = self.runner.invoke(
            app, ["skill", "status", "--target", "codex"]
        )
        self.assertEqual(status.exit_code, 0, status.stdout)
        self.assertIn("codex: outdated", status.stdout)

        updated = self.runner.invoke(
            app, ["skill", "update", "--target", "codex"]
        )
        self.assertEqual(updated.exit_code, 0, updated.stdout)
        self.assertEqual(path.read_bytes(), bundled_skill_bytes())

    def test_uninstall_removes_only_managed_unmodified_skill(self) -> None:
        self.init_workspace()
        unmanaged = self.skill_path("codex")
        unmanaged.parent.mkdir(parents=True)
        unmanaged.write_text("user-owned\n", encoding="utf-8")

        skipped = self.runner.invoke(
            app, ["skill", "uninstall", "--target", "codex"]
        )
        self.assertEqual(skipped.exit_code, 0, skipped.stdout)
        self.assertTrue(unmanaged.exists())

        installed = self.runner.invoke(
            app,
            ["skill", "install", "--target", "codex", "--force"],
        )
        self.assertEqual(installed.exit_code, 0, installed.stdout)
        unmanaged.write_text("user change\n", encoding="utf-8")

        protected = self.runner.invoke(
            app, ["skill", "uninstall", "--target", "codex"]
        )
        self.assertNotEqual(protected.exit_code, 0)
        self.assertTrue(unmanaged.exists())

        forced = self.runner.invoke(
            app, ["skill", "uninstall", "--target", "codex", "--force"]
        )
        self.assertEqual(forced.exit_code, 0, forced.stdout)
        self.assertFalse(unmanaged.exists())
        self.assertFalse((self.tmp_root / ".vcli/skills.yaml").exists())

    def test_install_rejects_symlinked_target_parent(self) -> None:
        self.init_workspace()
        outside = self.tmp_root / "outside"
        outside.mkdir()
        (self.tmp_root / ".agents").symlink_to(outside, target_is_directory=True)

        result = self.runner.invoke(
            app,
            ["skill", "install", "--target", "codex", "--force"],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("심볼릭 링크", result.stdout)
        self.assertFalse((outside / "skills/vcli-manage-posts/SKILL.md").exists())

    def test_skill_commands_require_initialized_workspace(self) -> None:
        result = self.runner.invoke(app, ["skill", "install"])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("vcli 저장소를 찾을 수 없습니다", result.stdout)

    def test_filesystem_errors_are_reported_without_traceback(self) -> None:
        self.init_workspace()
        with patch(
            "vcli.commands.skill.install_skill",
            side_effect=PermissionError("read-only skill directory"),
        ):
            result = self.runner.invoke(app, ["skill", "install"])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("read-only skill directory", result.stdout)
        self.assertNotIn("Traceback", result.stdout)


if __name__ == "__main__":
    unittest.main()
