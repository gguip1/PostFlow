import typer

from vcli.adapters.velog.auth import auth_exists, get_auth_path
from vcli.utils import logger


def logout() -> None:
    """Velog 로그인 세션을 삭제합니다."""
    try:
        auth_path = get_auth_path()
    except FileNotFoundError as error:
        logger.error(str(error))
        raise typer.Exit(1) from error

    if not auth_exists():
        logger.info("저장된 세션이 없습니다.")
        return

    confirm = typer.confirm(
        f"세션 파일을 삭제합니다 ({auth_path}). 계속할까요?",
        default=True,
    )
    if not confirm:
        return

    auth_path.unlink()
    logger.success("세션이 삭제되었습니다.")
