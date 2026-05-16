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
        logger.error(f"업로드되지 않은 로컬 이미지 경로가 남아 있습니다: {ref}")
        logger.info(f"먼저 업로드하세요: vcli image upload \"{post_dir / ref}\"")
        logger.info("그다음 본문의 이미지 URL을 업로드된 URL로 바꾸세요.")
    return False


def _confirm_push(root: Path, entry: RegistryEntry, meta, status: str) -> bool:
    post_dir = get_post_dir(root, entry.slug)

    if entry.velog_id:
        logger.warn("Velog 글을 수정하려고 합니다.")
        logger.warn("vcli push는 동기화 병합이 아닙니다. 로컬 글 상태로 원격 Velog 글을 덮어씁니다.")
    else:
        logger.warn("Velog에 새 글을 발행하려고 합니다.")
        logger.warn("로컬 draft가 새 Velog 글로 발행됩니다.")

    logger.info("로컬 글")
    logger.info(f"  slug: {entry.slug}")
    logger.info(f"  제목: {meta.title}")
    logger.info(f"  상태: {status}")
    logger.info(f"  경로: {post_dir / 'content.md'}")

    if entry.velog_id:
        logger.info("원격 Velog 글")
        logger.info(f"  URL: {entry.url or '(registry에 URL 없음)'}")
        logger.info(f"  velog_id: {entry.velog_id}")
        logger.info("실행 작업: 로컬 글 내용으로 위 Velog 글을 덮어씁니다.")
    else:
        logger.info("실행 작업: 로컬 draft를 새 Velog 글로 발행합니다.")

    return typer.confirm("계속할까요?", default=False)


def _push_entry(root: Path, entry: RegistryEntry, adapter: VelogAdapter) -> bool:
    meta, content = read_post(root, entry.slug)
    post_dir = get_post_dir(root, entry.slug)
    status = calculate_status(root, entry)
    restored_content = _restore_image_urls(content, post_dir)
    if not _validate_no_unuploaded_local_images(restored_content, post_dir):
        return False
    if status == "synced":
        logger.info(f"이미 synced 상태입니다. push할 변경사항이 없습니다: {entry.slug}")
        return True
    if not _confirm_push(root, entry, meta, status):
        logger.info("push를 취소했습니다.")
        return False

    post_data = to_post_data(meta, restored_content)

    if entry.velog_id:
        logger.info(f"Velog 글을 수정합니다: {meta.title}")
        result = adapter.update(entry.velog_id, post_data)
    else:
        logger.info(f"Velog에 새 글을 발행합니다: {meta.title}")
        result = adapter.create(post_data)

    if not result.success:
        logger.error(result.error or "push에 실패했습니다.")
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
    logger.success(f"push 완료: {result.url or entry.url}")
    return True


def _pushable_status(root: Path, entry: RegistryEntry) -> str | None:
    try:
        status = calculate_status(root, entry)
    except FileNotFoundError as error:
        logger.warn(f"깨진 로컬 글을 건너뜁니다: {entry.slug} ({error})")
        logger.info(f"Velog에서 복원하려면 `vcli pull`, 상태를 보려면 `vcli check {entry.slug}`를 실행하세요.")
        return None

    if status in {"draft", "modified"}:
        return status
    return None


def push(slug: str | None = typer.Argument(None, help="push할 글 slug")) -> None:
    """로컬 draft 또는 modified 글을 Velog에 반영합니다."""
    root = find_project_root()

    if not check_auth():
        logger.error("Velog 로그인이 필요합니다. 먼저 `vcli login`을 실행하세요.")
        raise typer.Exit(1)

    adapter = VelogAdapter()

    if slug:
        entry = find_entry(root, slug)
        if not entry:
            logger.error(f"글을 찾을 수 없습니다: {slug}")
            raise typer.Exit(1)
        try:
            pushed = _push_entry(root, entry, adapter)
        except FileNotFoundError as error:
            logger.error(f"깨진 로컬 글은 push할 수 없습니다: {slug} ({error})")
            logger.info(f"Velog에서 복원하려면 `vcli pull`, 상태를 보려면 `vcli check {slug}`를 실행하세요.")
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
        logger.info("push할 draft 또는 modified 글이 없습니다.")
        return

    selected = inquirer.checkbox(
        message="push할 글을 선택하세요",
        instruction="(스페이스: 선택/해제, Enter: 선택한 글 push)",
        mandatory_message="스페이스로 하나 이상 선택한 뒤 Enter를 누르세요.",
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
