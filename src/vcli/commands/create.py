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
    post_slug: str = typer.Argument(None, help="Post slug"),
    title: str = typer.Option(None, "--title", "-t", help="Post title"),
    slug: str = typer.Option(None, "--slug", "-s", help="Post slug"),
    tags: str = typer.Option(None, "--tags", help="Comma-separated tags"),
    visibility: str = typer.Option(
        "public", "--visibility", "-v", help="Visibility: public or private"
    ),
    series: str = typer.Option(None, "--series", help="Velog series name"),
) -> None:
    """Create a new draft post."""
    root = find_project_root()

    if visibility not in {"public", "private"}:
        logger.error("visibility must be public or private")
        raise typer.Exit(1)

    if title is None:
        title = typer.prompt("Post title")

    slug = slug or post_slug
    if slug is None:
        slug = typer.prompt("Post slug", default=_slugify(title))

    parsed_tags: list[str] = []
    if tags is None:
        tags = typer.prompt("Tags (comma-separated)", default="")
    if tags:
        parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

    try:
        meta = create_post(
            root=root,
            title=title,
            slug=slug,
            tags=parsed_tags,
            visibility=visibility,
            series=series,
        )
    except (FileExistsError, ValueError) as error:
        logger.error(str(error))
        raise typer.Exit(1) from error

    post_dir = root / ".vcli" / "posts" / slug
    logger.success(f"Draft created: {post_dir}")
    logger.info(f"Edit: {post_dir / 'content.md'}")
