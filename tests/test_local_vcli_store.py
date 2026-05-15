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
