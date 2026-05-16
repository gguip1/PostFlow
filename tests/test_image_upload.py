import json
import os
import shutil
import unittest
import unittest.mock
from pathlib import Path
from uuid import uuid4

from typer.testing import CliRunner

from vcli.main import app
from vcli.utils.fs import read_yaml


class ImageUploadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_root = Path(__file__).resolve().parent / ".tmp" / uuid4().hex
        self.tmp_root.mkdir(parents=True)
        self.previous_cwd = Path.cwd()
        os.chdir(self.tmp_root)
        self.runner = CliRunner()
        self.addCleanup(os.chdir, self.previous_cwd)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_image_upload_outputs_url_and_records_upload(self) -> None:
        import vcli.commands.image as image_command

        self.runner.invoke(app, ["init"])
        image_path = self.tmp_root / ".vcli" / "posts" / "image-post" / "images" / "diagram.png"
        image_path.parent.mkdir(parents=True)
        image_path.write_bytes(b"image-bytes")

        with unittest.mock.patch.object(image_command, "check_auth", lambda: True), \
             unittest.mock.patch.object(
                 image_command, "upload_image_file", lambda path, image_type="post", ref_id=None: "https://velog.velcdn.com/images/me/post/1/image.png"
             ):
            result = self.runner.invoke(
                app,
                ["image", "upload", str(image_path), "--post", "image-post"],
            )

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertIn("https://velog.velcdn.com/images/me/post/1/image.png", result.stdout)

        uploads = read_yaml(self.tmp_root / ".vcli" / "uploads.yaml")
        entry = uploads["uploads"][0]
        self.assertEqual(entry["local_path"], ".vcli/posts/image-post/images/diagram.png")
        self.assertEqual(entry["url"], "https://velog.velcdn.com/images/me/post/1/image.png")
        self.assertEqual(entry["post_slug"], "image-post")
        self.assertIsNotNone(entry["sha256"])
        self.assertIsNotNone(entry["uploaded_at"])

    def test_image_upload_json_outputs_machine_readable_data(self) -> None:
        import vcli.commands.image as image_command

        self.runner.invoke(app, ["init"])
        image_path = self.tmp_root / ".vcli" / "posts" / "image-post" / "images" / "diagram.png"
        image_path.parent.mkdir(parents=True)
        image_path.write_bytes(b"image-bytes")

        with unittest.mock.patch.object(image_command, "check_auth", lambda: True), \
             unittest.mock.patch.object(
                 image_command, "upload_image_file", lambda path, image_type="post", ref_id=None: "https://velog.velcdn.com/images/me/post/1/image.png"
             ):
            result = self.runner.invoke(app, ["image", "upload", str(image_path), "--json"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["url"], "https://velog.velcdn.com/images/me/post/1/image.png")
        self.assertEqual(payload["local_path"], ".vcli/posts/image-post/images/diagram.png")
        self.assertIsNotNone(payload["sha256"])

    def test_push_blocks_unmapped_local_image_paths(self) -> None:
        import vcli.commands.push as push_command

        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["create", "image-post", "--title", "Image Post"])
        post_dir = self.tmp_root / ".vcli" / "posts" / "image-post"
        (post_dir / "images").mkdir()
        (post_dir / "images" / "diagram.png").write_bytes(b"image-bytes")
        (post_dir / "content.md").write_text(
            "![diagram](./images/diagram.png)\n",
            encoding="utf-8",
        )

        class DummyAdapter:
            def create(self, post):
                raise AssertionError("push should stop before publishing")

            def update(self, post_id, post):
                raise AssertionError("push should stop before publishing")

        with unittest.mock.patch.object(push_command, "check_auth", lambda: True), \
             unittest.mock.patch.object(push_command, "VelogAdapter", DummyAdapter):
            result = self.runner.invoke(app, ["push", "image-post"])

        self.assertEqual(result.exit_code, 1, result.stdout)
        self.assertIn("Local image path is not uploaded", result.stdout)
        self.assertIn("vcli image upload", result.stdout)

    def test_push_allows_mapped_local_image_when_hash_matches(self) -> None:
        import vcli.commands.push as push_command
        from vcli.adapters.velog.adapter import PublishResult
        from vcli.core.images import file_sha256

        self.runner.invoke(app, ["init"])
        self.runner.invoke(app, ["create", "image-post", "--title", "Image Post"])
        post_dir = self.tmp_root / ".vcli" / "posts" / "image-post"
        (post_dir / "images").mkdir()
        image_path = post_dir / "images" / "diagram.png"
        image_path.write_bytes(b"image-bytes")
        (post_dir / "images" / "mapping.json").write_text(
            json.dumps(
                {
                    "./images/diagram.png": {
                        "url": "https://velog.velcdn.com/images/me/post/1/image.png",
                        "sha256": file_sha256(image_path),
                        "source": "pull",
                    }
                }
            ),
            encoding="utf-8",
        )
        (post_dir / "content.md").write_text(
            "![diagram](./images/diagram.png)\n",
            encoding="utf-8",
        )

        bodies: list[str] = []

        class DummyAdapter:
            def create(self, post):
                bodies.append(post.body)
                return PublishResult(
                    success=True,
                    post_id="velog-1",
                    url="https://velog.io/@me/image-post",
                    published_at="2026-05-16T12:00:00Z",
                )

            def update(self, post_id, post):
                return self.create(post)

        with unittest.mock.patch.object(push_command, "check_auth", lambda: True), \
             unittest.mock.patch.object(push_command, "VelogAdapter", DummyAdapter):
            result = self.runner.invoke(app, ["push", "image-post"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertEqual(
            bodies,
            ["![diagram](https://velog.velcdn.com/images/me/post/1/image.png)\n"],
        )


if __name__ == "__main__":
    unittest.main()
