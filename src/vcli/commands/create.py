import re

import typer

from vcli.core.post import create_post
from vcli.utils import logger
from vcli.utils.paths import find_project_root


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def create(
    post_slug: str = typer.Argument(None, help="글 slug"),
    title: str = typer.Option(None, "--title", "-t", help="글 제목"),
    slug: str = typer.Option(None, "--slug", "-s", help="글 slug"),
    tags: str = typer.Option(None, "--tags", help="쉼표로 구분한 태그"),
    description: str = typer.Option("", "--description", "-d", help="글 설명"),
    visibility: str = typer.Option(
        "public", "--visibility", "-v", help="공개 범위: public 또는 private"
    ),
    series: str = typer.Option(None, "--series", help="Velog 시리즈 이름"),
) -> None:
    """새 로컬 draft 글을 만듭니다."""
    root = find_project_root()
    interactive = title is None and slug is None and post_slug is None

    if visibility not in {"public", "private"}:
        logger.error("visibility는 public 또는 private이어야 합니다.")
        raise typer.Exit(1)

    if title is None:
        title = typer.prompt("글 제목")

    slug = slug or post_slug
    if slug is None:
        slug = typer.prompt("글 slug", default=_slugify(title))

    parsed_tags: list[str] = []
    if tags is None and interactive:
        tags = typer.prompt("태그(쉼표 구분)", default="")
    if tags:
        parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

    try:
        meta = create_post(
            root=root,
            title=title,
            slug=slug,
            tags=parsed_tags,
            visibility=visibility,
            description=description,
            series=series,
        )
    except (FileExistsError, ValueError) as error:
        logger.error(str(error))
        raise typer.Exit(1) from error

    post_dir = root / ".vcli" / "posts" / slug
    logger.success(f"로컬 draft를 만들었습니다: {post_dir}")
    logger.info(f"본문 파일: {post_dir / 'content.md'}")
