from pathlib import Path

from vcli.core.hashing import hash_post
from vcli.models import Registry, RegistryEntry
from vcli.utils.fs import read_yaml, write_yaml
from vcli.utils.paths import get_post_dir, get_registry_path


def load_registry(root: Path) -> Registry:
    path = get_registry_path(root)
    if not path.exists():
        return Registry()
    data = read_yaml(path)
    return Registry(**data)


def save_registry(root: Path, registry: Registry) -> None:
    path = get_registry_path(root)
    write_yaml(path, registry.model_dump(mode="json", exclude_none=True))


def find_entry(root: Path, slug: str) -> RegistryEntry | None:
    registry = load_registry(root)
    for entry in registry.posts:
        if entry.slug == slug:
            return entry
    return None


def upsert_entry(root: Path, entry: RegistryEntry) -> None:
    registry = load_registry(root)
    for index, existing in enumerate(registry.posts):
        if existing.slug == entry.slug:
            registry.posts[index] = entry
            save_registry(root, registry)
            return
    registry.posts.append(entry)
    save_registry(root, registry)


def calculate_status(root: Path, entry: RegistryEntry) -> str:
    if not entry.velog_id:
        return "draft"
    if hash_post(get_post_dir(root, entry.slug)) == entry.last_synced_hash:
        return "synced"
    return "modified"
