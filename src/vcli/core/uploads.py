from pathlib import Path

from vcli.models import UploadEntry, UploadRegistry
from vcli.utils.fs import read_yaml, write_yaml
from vcli.utils.paths import get_uploads_path


def load_uploads(root: Path) -> UploadRegistry:
    path = get_uploads_path(root)
    if not path.exists():
        return UploadRegistry()
    return UploadRegistry(**read_yaml(path))


def save_uploads(root: Path, uploads: UploadRegistry) -> None:
    write_yaml(get_uploads_path(root), uploads.model_dump(mode="json", exclude_none=True))


def upsert_upload(root: Path, entry: UploadEntry) -> None:
    uploads = load_uploads(root)
    for index, existing in enumerate(uploads.uploads):
        if existing.local_path == entry.local_path and existing.sha256 == entry.sha256:
            uploads.uploads[index] = entry
            save_uploads(root, uploads)
            return
    uploads.uploads.append(entry)
    save_uploads(root, uploads)
