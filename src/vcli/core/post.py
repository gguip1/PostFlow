from pathlib import Path

from vcli.core.registry import upsert_entry
from vcli.models import Meta, RegistryEntry
from vcli.utils.fs import read_text, read_yaml, write_text, write_yaml
from vcli.utils.paths import get_post_dir


def create_post(
    root: Path,
    title: str,
    slug: str,
    tags: list[str] | None = None,
    visibility: str = "public",
    description: str = "",
    series: str | None = None,
) -> Meta:
    post_dir = get_post_dir(root, slug)

    if post_dir.exists():
        raise FileExistsError(f"post directory already exists: {slug}")

    meta = Meta(
        title=title,
        slug=slug,
        description=description,
        tags=tags or [],
        visibility=visibility,
        series=series,
    )

    post_dir.mkdir(parents=True)
    write_yaml(post_dir / "meta.yaml", meta.model_dump(mode="json"))
    write_text(post_dir / "content.md", f"# {title}\n\n")

    upsert_entry(root, RegistryEntry(slug=slug))
    return meta


def read_post(root: Path, slug: str) -> tuple[Meta, str]:
    post_dir = get_post_dir(root, slug)

    if not post_dir.exists():
        raise FileNotFoundError(f"post directory not found: {slug}")

    meta = Meta(**read_yaml(post_dir / "meta.yaml"))
    content = read_text(post_dir / "content.md")
    return meta, content


def write_post_meta(root: Path, meta: Meta) -> None:
    post_dir = get_post_dir(root, meta.slug)
    if not post_dir.exists():
        raise FileNotFoundError(f"post directory not found: {meta.slug}")
    write_yaml(post_dir / "meta.yaml", meta.model_dump(mode="json"))
