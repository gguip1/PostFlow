import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

import typer

from vcli.adapters.velog.api import get_current_user, get_user_posts
from vcli.adapters.velog.auth import check_auth
from vcli.core.hashing import hash_post
from vcli.core.images import file_sha256, strip_fenced_code_blocks
from vcli.core.registry import (
    calculate_status,
    find_entry,
    find_entry_by_velog_id,
    load_registry,
    upsert_entry,
)
from vcli.models import Meta, RegistryEntry
from vcli.utils import logger
from vcli.utils.fs import write_text, write_yaml
from vcli.utils.paths import find_project_root, get_post_dir


def _remote_timestamp(post: dict) -> str:
    raw = post.get("updated_at") or post.get("released_at")
    if raw:
        return raw
    return datetime.now(timezone.utc).isoformat()


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _find_image_urls(body: str) -> list[str]:
    body = strip_fenced_code_blocks(body)
    urls: list[str] = []
    for match in re.finditer(r"!\[[^\]]*\]\((https?://[^)]+)\)", body):
        urls.append(match.group(1))
    for match in re.finditer(r'<img[^>]+src=["\']?(https?://[^"\'>\s]+)', body):
        urls.append(match.group(1))
    return urls


def _make_filename(url: str, index: int) -> str:
    parsed = urlparse(url)
    original = unquote(parsed.path.split("/")[-1])

    ext = ".png"
    if "." in original:
        candidate = "." + original.rsplit(".", 1)[-1].lower()
        if len(candidate) <= 5:
            ext = candidate

    name_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"image-{index + 1}-{name_hash}{ext}"


def _download_images(body: str, post_dir: Path) -> str:
    urls = _find_image_urls(body)
    if not urls:
        return body

    images_dir = post_dir / "images"
    images_dir.mkdir(exist_ok=True)

    mapping_path = images_dir / "mapping.json"
    if mapping_path.exists():
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    else:
        mapping = {}

    processed = 0
    for index, url in enumerate(urls):
        try:
            filename = _make_filename(url, index)
            local_path = images_dir / filename
            if not local_path.exists():
                req = Request(url, headers={"User-Agent": "unofficial-velog-cli/0.1"})
                with urlopen(req, timeout=30) as resp:
                    local_path.write_bytes(resp.read())

            local_ref = f"./images/{filename}"
            mapping[local_ref] = {
                "url": url,
                "sha256": file_sha256(local_path),
                "source": "pull",
            }
            body = body.replace(url, local_ref)
            processed += 1
        except Exception:
            logger.warn(f"이미지를 다운로드하지 못했습니다: {url}")

    if mapping:
        mapping_path.write_text(
            json.dumps(mapping, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    if processed:
        logger.info(f"이미지 처리 완료: {processed}/{len(urls)}")

    return body


def _has_modified_local_copy(root: Path, entry) -> bool:
    try:
        return calculate_status(root, entry) == "modified"
    except FileNotFoundError as error:
        logger.warn(f"깨진 로컬 글을 원격 기준으로 다시 가져옵니다: {entry.slug} ({error})")
        return False


def pull() -> None:
    """Velog 글을 .vcli/posts로 가져옵니다."""
    root = find_project_root()

    if not check_auth():
        logger.error("Velog 로그인이 필요합니다. 먼저 `vcli login`을 실행하세요.")
        raise typer.Exit(1)

    try:
        user = get_current_user()
        if not user:
            logger.error("Velog 사용자 정보를 읽을 수 없습니다.")
            raise typer.Exit(1)
        username = user["username"]
        remote_posts = get_user_posts(username)
    except (PermissionError, ConnectionError, RuntimeError) as error:
        logger.error(str(error))
        logger.warn("원격 목록을 완전히 확인하지 못해 누락 판정을 수행하지 않습니다.")
        raise typer.Exit(1) from error

    created = 0
    updated = 0
    skipped = 0
    missing = 0

    remote_ids = {post["id"] for post in remote_posts}

    for post in remote_posts:
        slug = post.get("url_slug") or _slugify(post["title"])
        velog_id = post["id"]
        entry = find_entry_by_velog_id(root, velog_id)
        slug_entry = find_entry(root, slug)

        if entry is None and slug_entry is not None:
            logger.warn(
                f"원격 글을 가져오지 못했습니다. 로컬 slug가 다른 글에서 사용 중입니다: {slug}"
            )
            skipped += 1
            continue

        if entry and entry.slug != slug:
            old_slug = entry.slug
            old_dir = get_post_dir(root, old_slug)
            new_dir = get_post_dir(root, slug)

            if _has_modified_local_copy(root, entry):
                upsert_entry(
                    root,
                    entry.model_copy(
                        update={
                            "url": f"https://velog.io/@{username}/{slug}",
                            "remote_missing_at": None,
                            "remote_slug": slug,
                        }
                    ),
                )
                logger.warn(
                    f"원격 slug 변경과 로컬 수정이 충돌합니다: {old_slug} -> {slug}"
                )
                skipped += 1
                continue

            if new_dir.exists():
                upsert_entry(
                    root,
                    entry.model_copy(
                        update={
                            "url": f"https://velog.io/@{username}/{slug}",
                            "remote_missing_at": None,
                            "remote_slug": slug,
                        }
                    ),
                )
                logger.warn(
                    f"원격 slug로 이동할 수 없습니다. 로컬 폴더가 이미 존재합니다: {slug}"
                )
                skipped += 1
                continue

            if old_dir.exists():
                old_dir.rename(new_dir)
            logger.info(f"원격 slug 변경을 반영합니다: {old_slug} -> {slug}")
            entry = entry.model_copy(
                update={
                    "slug": slug,
                    "url": f"https://velog.io/@{username}/{slug}",
                    "remote_missing_at": None,
                    "remote_slug": None,
                }
            )
            upsert_entry(root, entry)

        if entry and _has_modified_local_copy(root, entry):
            upsert_entry(
                root,
                entry.model_copy(
                    update={
                        "url": f"https://velog.io/@{username}/{slug}",
                        "remote_missing_at": None,
                        "remote_slug": None,
                    }
                ),
            )
            logger.warn(f"수정된 로컬 글은 덮어쓰지 않고 건너뜁니다: {slug}")
            skipped += 1
            continue

        post_dir = get_post_dir(root, slug)
        post_dir.mkdir(parents=True, exist_ok=True)

        meta = Meta(
            title=post["title"],
            slug=slug,
            description=post.get("short_description", "") or "",
            tags=post.get("tags", []),
            visibility="private" if post.get("is_private") else "public",
            series=post["series"]["name"] if post.get("series") else None,
        )
        write_yaml(post_dir / "meta.yaml", meta.model_dump(mode="json"))

        body = post.get("body", "") or ""
        write_text(post_dir / "content.md", _download_images(body, post_dir))

        upsert_entry(
            root,
            RegistryEntry(
                slug=slug,
                velog_id=post["id"],
                url=f"https://velog.io/@{username}/{slug}",
                last_synced_hash=hash_post(post_dir),
                last_synced_at=_remote_timestamp(post),
                remote_missing_at=None,
                remote_slug=None,
            ),
        )

        if entry:
            updated += 1
        else:
            created += 1

    observed_at = datetime.now(timezone.utc).isoformat()
    for entry in load_registry(root).posts:
        if not entry.velog_id or entry.velog_id in remote_ids:
            continue
        if entry.remote_missing_at is None:
            entry = entry.model_copy(update={"remote_missing_at": observed_at})
            upsert_entry(root, entry)
        logger.warn(
            f"원격 Velog에서 찾을 수 없습니다. 로컬 글은 보존합니다: {entry.slug}"
        )
        missing += 1

    logger.success(
        f"Pull 완료: 생성 {created}개, 갱신 {updated}개, "
        f"건너뜀 {skipped}개, 원격 누락 {missing}개"
    )
