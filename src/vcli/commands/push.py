import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from InquirerPy import inquirer

from vcli.adapters.velog.adapter import VelogAdapter
from vcli.adapters.velog.auth import check_auth
from vcli.adapters.velog.mapper import to_post_data
from vcli.core.hashing import hash_post
from vcli.core.images import (
    file_sha256,
    find_image_references,
    is_remote_image_ref,
    normalize_local_image_ref,
)
from vcli.core.post import read_post
from vcli.core.registry import calculate_status, find_entry, load_registry, upsert_entry
from vcli.models import RegistryEntry
from vcli.utils import logger
from vcli.utils.paths import find_project_root, get_post_dir


def _restore_image_urls(content: str, post_dir: Path) -> str:
    mapping_path = post_dir / "images" / "mapping.json"
    if not mapping_path.exists():
        return content

    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    for local_ref, value in mapping.items():
        original_url = value if isinstance(value, str) else value.get("url") or value.get("remote_url")
        if not original_url:
            continue

        expected_hash = None if isinstance(value, str) else value.get("sha256")
        if expected_hash:
            local_path = post_dir / local_ref
            if not local_path.exists() or file_sha256(local_path) != expected_hash:
                continue

        content = content.replace(local_ref, original_url)
    return content


def _unuploaded_local_images(content: str) -> list[str]:
    refs = []
    for ref in find_image_references(content):
        normalized = normalize_local_image_ref(ref)
        if not is_remote_image_ref(normalized):
            refs.append(normalized)
    return refs


def _validate_no_unuploaded_local_images(content: str, post_dir: Path) -> bool:
    local_refs = _unuploaded_local_images(content)
    if not local_refs:
        return True

    for ref in local_refs:
        logger.error(f"Local image path is not uploaded: {ref}")
        logger.info(f"Upload it first: vcli image upload \"{post_dir / ref}\"")
        logger.info("Then replace the markdown image URL with the uploaded URL.")
    return False


def _push_entry(root: Path, entry: RegistryEntry, adapter: VelogAdapter) -> bool:
    meta, content = read_post(root, entry.slug)
    post_dir = get_post_dir(root, entry.slug)
    restored_content = _restore_image_urls(content, post_dir)
    if not _validate_no_unuploaded_local_images(restored_content, post_dir):
        return False
    post_data = to_post_data(meta, restored_content)

    if entry.velog_id:
        logger.info(f"Updating: {meta.title}")
        result = adapter.update(entry.velog_id, post_data)
    else:
        logger.info(f"Publishing: {meta.title}")
        result = adapter.create(post_data)

    if not result.success:
        logger.error(result.error or "push failed")
        return False

    upsert_entry(
        root,
        RegistryEntry(
            slug=entry.slug,
            velog_id=result.post_id or entry.velog_id,
            url=result.url or entry.url,
            last_synced_hash=hash_post(post_dir),
            last_synced_at=result.published_at or datetime.now(timezone.utc).isoformat(),
        ),
    )
    logger.success(f"Pushed: {result.url or entry.url}")
    return True


def _pushable_status(root: Path, entry: RegistryEntry) -> str | None:
    try:
        status = calculate_status(root, entry)
    except FileNotFoundError as error:
        logger.warn(f"Skipped invalid local post: {entry.slug} ({error})")
        logger.info(f"Run `vcli pull` to restore it from Velog, or `vcli check {entry.slug}`.")
        return None

    if status in {"draft", "modified"}:
        return status
    return None


def push(slug: str | None = typer.Argument(None, help="Post slug to push")) -> None:
    """Push local draft or modified posts to Velog."""
    root = find_project_root()

    if not check_auth():
        logger.error("Velog login required. Run `vcli login` first.")
        raise typer.Exit(1)

    adapter = VelogAdapter()

    if slug:
        entry = find_entry(root, slug)
        if not entry:
            logger.error(f"Post not found: {slug}")
            raise typer.Exit(1)
        try:
            pushed = _push_entry(root, entry, adapter)
        except FileNotFoundError as error:
            logger.error(f"Cannot push invalid local post: {slug} ({error})")
            logger.info(f"Run `vcli pull` to restore it from Velog, or `vcli check {slug}`.")
            raise typer.Exit(1) from error
        if not pushed:
            raise typer.Exit(1)
        return

    registry = load_registry(root)
    candidates = []
    for entry in registry.posts:
        status = _pushable_status(root, entry)
        if status:
            candidates.append((entry, status))

    if not candidates:
        logger.info("No draft or modified posts to push.")
        return

    selected = inquirer.checkbox(
        message="Select posts to push",
        instruction="(Space: select/deselect, Enter: push selected)",
        mandatory_message="Select at least one post with Space, then press Enter.",
        choices=[
            {
                "name": f"{status}  {entry.slug}",
                "value": entry.slug,
            }
            for entry, status in candidates
        ],
    ).execute()

    for selected_slug in selected:
        entry = find_entry(root, selected_slug)
        if entry:
            _push_entry(root, entry, adapter)
