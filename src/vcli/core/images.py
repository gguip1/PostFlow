import re
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse


FENCED_CODE_BLOCK_RE = re.compile(
    r"^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[ \t]*$",
    re.MULTILINE | re.DOTALL,
)


def strip_fenced_code_blocks(content: str) -> str:
    return FENCED_CODE_BLOCK_RE.sub("", content)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_image_references(content: str) -> list[str]:
    content = strip_fenced_code_blocks(content)
    refs: list[str] = []

    for match in re.finditer(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+['\"][^)]*['\"])?\)", content):
        refs.append(match.group(1).strip("<>"))

    for match in re.finditer(r'<img[^>]+src=["\']?([^"\'>\s]+)', content):
        refs.append(match.group(1))

    return refs


def is_remote_image_ref(ref: str) -> bool:
    parsed = urlparse(ref)
    return parsed.scheme in {"http", "https", "data"}


def normalize_local_image_ref(ref: str) -> str:
    return ref.replace("\\", "/")


def workspace_relative_path(root: Path, path: Path) -> str:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root)
        return relative.as_posix()
    except ValueError:
        return str(resolved_path)
