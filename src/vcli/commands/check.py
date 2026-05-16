import typer

from vcli.core.validator import validate_all, validate_post
from vcli.utils import logger
from vcli.utils.paths import find_project_root


def check(
    slug: str = typer.Argument(None, help="Validate a single post by slug"),
) -> None:
    """Validate blog post files and registry state."""
    root = find_project_root()

    try:
        result = validate_post(root, slug) if slug else validate_all(root)
    except FileNotFoundError as error:
        logger.error(str(error))
        raise typer.Exit(1) from error

    for warning in result.warnings:
        logger.warn(warning)
    for error in result.errors:
        logger.error(error)

    if result.ok:
        logger.success(f"Validation passed for {slug}" if slug else "Validation passed")
        return

    logger.error(f"Validation failed with {len(result.errors)} error(s)")
    raise typer.Exit(1)
