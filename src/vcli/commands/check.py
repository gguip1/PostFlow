import typer

from vcli.core.validator import validate_all, validate_post
from vcli.utils import logger
from vcli.utils.paths import find_project_root


def check(
    slug: str = typer.Argument(None, help="검증할 글 slug"),
) -> None:
    """글 파일과 registry 상태를 검증합니다."""
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
        logger.success(f"검증을 통과했습니다: {slug}" if slug else "검증을 통과했습니다.")
        return

    logger.error(f"검증 실패: 오류 {len(result.errors)}개")
    raise typer.Exit(1)
