import os
import shutil
import unittest
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

from typer.testing import CliRunner

from vcli.core.workspace import find_workspace_root
from vcli.main import app
from vcli.utils.fs import read_yaml


class VcliCliSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_root = Path(__file__).resolve().parent / ".tmp" / uuid4().hex
        self.tmp_root.mkdir(parents=True)
        self.previous_cwd = Path.cwd()
        os.chdir(self.tmp_root)
        self.runner = CliRunner()
        self.addCleanup(os.chdir, self.previous_cwd)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_init_create_status_smoke_flow(self) -> None:
        init_result = self.runner.invoke(app, ["init"])
        self.assertEqual(init_result.exit_code, 0, init_result.stdout)

        create_result = self.runner.invoke(
            app,
            ["create", "hello-velog", "--title", "Hello Velog", "--tags", "cli,velog"],
        )
        self.assertEqual(create_result.exit_code, 0, create_result.stdout)

        post_dir = self.tmp_root / ".vcli" / "posts" / "hello-velog"
        self.assertTrue((post_dir / "content.md").exists())
        meta = read_yaml(post_dir / "meta.yaml")
        self.assertEqual(meta["title"], "Hello Velog")
        self.assertEqual(meta["tags"], ["cli", "velog"])

        status_result = self.runner.invoke(app, ["status"])
        self.assertEqual(status_result.exit_code, 0, status_result.stdout)
        self.assertIn("draft", status_result.stdout)
        self.assertIn("hello-velog", status_result.stdout)

    def test_removed_legacy_commands_are_not_available(self) -> None:
        for command in ("publish", "sync", "ready", "root", "workspace"):
            result = self.runner.invoke(app, [command, "--help"])

            self.assertNotEqual(result.exit_code, 0, command)

    def test_version_option_prints_installed_package_version(self) -> None:
        result = self.runner.invoke(app, ["--version"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertEqual(result.stdout.strip(), version("unofficial-velog-cli"))

    def test_commands_find_workspace_from_nested_directory(self) -> None:
        init_result = self.runner.invoke(app, ["init"])
        self.assertEqual(init_result.exit_code, 0, init_result.stdout)
        nested = self.tmp_root / ".vcli" / "posts"

        os.chdir(nested)
        status_result = self.runner.invoke(app, ["status"])

        self.assertEqual(status_result.exit_code, 0, status_result.stdout)
        self.assertEqual(find_workspace_root(nested), self.tmp_root)

    def test_auth_path_is_inside_local_vcli_store(self) -> None:
        from vcli.adapters.velog.auth import get_auth_path, login_with_token

        self.runner.invoke(app, ["init"])

        auth_path = self.tmp_root / ".vcli" / "velog-auth.json"
        self.assertEqual(get_auth_path(self.tmp_root), auth_path)

        login_with_token("access-token", "refresh-token", self.tmp_root)

        self.assertTrue(auth_path.exists())
        self.assertFalse((Path.home() / ".vcli" / "velog-auth.json") == auth_path)

    def test_logout_removes_only_local_auth_file(self) -> None:
        from vcli.adapters.velog.auth import login_with_token

        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["create", "kept-post", "--title", "Kept Post"])
        login_with_token("access-token", "refresh-token", self.tmp_root)

        result = self.runner.invoke(app, ["logout"], input="y\n")

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertFalse((self.tmp_root / ".vcli" / "velog-auth.json").exists())
        self.assertTrue((self.tmp_root / ".vcli" / "posts" / "kept-post").exists())


if __name__ == "__main__":
    unittest.main()
