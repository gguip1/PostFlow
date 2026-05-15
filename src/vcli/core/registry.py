from datetime import datetime
from pathlib import Path

from vcli.core.config import load_config
from vcli.core.hashing import hash_post
from vcli.models import Meta, ProviderInfo, Registry, RegistryEntry
from vcli.utils.fs import read_yaml, write_yaml
from vcli.utils.paths import get_post_dir, get_registry_path

_UNSET = object()


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


def add_entry(root: Path, entry: RegistryEntry) -> None:
    registry = load_registry(root)

    for existing in registry.posts:
        if entry.id and existing.id == entry.id:
            raise ValueError(f"post id already exists: {entry.id}")
        if existing.slug == entry.slug:
            raise ValueError(f"post slug already exists: {entry.slug}")

    registry.posts.append(entry)
    save_registry(root, registry)


def update_entry(root: Path, entry_id: str, **updates) -> None:
    registry = load_registry(root)
    for index, entry in enumerate(registry.posts):
        if entry.id == entry_id or entry.slug == entry_id:
            registry.posts[index] = entry.model_copy(update=updates)
            save_registry(root, registry)
            return
    raise ValueError(f"post not found for id: {entry_id}")


def sync_entry_with_meta(
    root: Path,
    meta: Meta,
    *,
    provider: ProviderInfo | None | object = _UNSET,
    last_published_at: datetime | None | object = _UNSET,
) -> None:
    config = load_config(root)
    meta_id = getattr(meta, "id", None)
    entry = (find_entry(root, meta_id) if meta_id else None) or find_entry(root, meta.slug)
    if entry is None:
        raise ValueError(f"registry entry not found for post: {meta.slug}")

    updates: dict[str, object] = {
        "slug": meta.slug,
        "directory": f"{config.posts_dir}/{meta.slug}",
        "title": meta.title,
        "visibility": meta.visibility,
        "series": meta.series,
    }
    if hasattr(meta, "status"):
        updates["status"] = meta.status
    if meta_id:
        updates["id"] = meta_id
    if provider is not _UNSET:
        updates["provider"] = provider
        if provider is not None:
            updates["velog_id"] = provider.post_id
            updates["url"] = provider.url
    if last_published_at is not _UNSET:
        updates["last_published_at"] = last_published_at
        if last_published_at is not None:
            updates["last_synced_at"] = last_published_at.isoformat()

    update_entry(root, entry.id or entry.slug, **updates)
