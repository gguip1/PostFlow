import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from typer.testing import CliRunner

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


if __name__ == "__main__":
    unittest.main()
