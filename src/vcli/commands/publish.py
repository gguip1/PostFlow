import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from InquirerPy import inquirer

from vcli.adapters.velog.adapter import VelogAdapter
from vcli.adapters.velog.auth import check_auth
from vcli.adapters.velog.mapper import to_post_data
from vcli.core.hashing import hash_post
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
    for local_ref, original_url in mapping.items():
        content = content.replace(local_ref, original_url)
    return content


def _push_entry(root: Path, entry: RegistryEntry, adapter: VelogAdapter) -> bool:
    meta, content = read_post(root, entry.slug)
    post_dir = get_post_dir(root, entry.slug)
    post_data = to_post_data(meta, _restore_image_urls(content, post_dir))

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
        if not _push_entry(root, entry, adapter):
            raise typer.Exit(1)
        return

    registry = load_registry(root)
    candidates = [
        entry
        for entry in registry.posts
        if calculate_status(root, entry) in {"draft", "modified"}
    ]
    if not candidates:
        logger.info("No draft or modified posts to push.")
        return

    selected = inquirer.checkbox(
        message="Select posts to push",
        choices=[
            {
                "name": f"{calculate_status(root, entry)}  {entry.slug}",
                "value": entry.slug,
            }
            for entry in candidates
        ],
    ).execute()

    for selected_slug in selected:
        entry = find_entry(root, selected_slug)
        if entry:
            _push_entry(root, entry, adapter)


publish = push
