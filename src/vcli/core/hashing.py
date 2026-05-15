from hashlib import sha256
from pathlib import Path


def hash_post(post_dir: Path) -> str:
    content_path = post_dir / "content.md"
    meta_path = post_dir / "meta.yaml"

    digest = sha256()
    for path in (meta_path, content_path):
        if not path.exists():
            raise FileNotFoundError(f"required post file is missing: {path}")
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
