import webbrowser

import typer

from vcli.adapters.velog.auth import auth_exists, check_auth, login_with_token
from vcli.utils import logger


def login_cmd() -> None:
    """Velog에 로그인합니다."""
    try:
        existing_auth = auth_exists()
    except FileNotFoundError as error:
        logger.error(str(error))
        raise typer.Exit(1) from error

    if existing_auth:
        logger.info("기존 세션이 있습니다. 유효한지 확인 중...")
        if check_auth():
            logger.success("이미 로그인되어 있습니다.")
            relogin = typer.confirm("다시 로그인할까요?", default=False)
            if not relogin:
                return

    # 브라우저에서 Velog 열기
    logger.info("브라우저에서 Velog를 엽니다. 로그인해주세요.")
    webbrowser.open("https://velog.io")

    logger.info("")
    logger.info("로그인 후 토큰을 복사해주세요:")
    logger.info("  1. F12 (개발자 도구) 열기")
    logger.info("  2. Application(애플리케이션) 탭 > Cookies(쿠키) > https://velog.io")
    logger.info("  3. access_token 값 복사")
    logger.info("  4. refresh_token 값 복사")
    logger.info("")

    access_token = typer.prompt("access_token", default="", show_default=False).strip()
    refresh_token = typer.prompt("refresh_token", default="", show_default=False).strip()

    if not access_token or not refresh_token:
        logger.error("토큰이 비어있습니다.")
        raise typer.Exit(1)

    login_with_token(access_token, refresh_token)

    # 저장된 토큰 검증
    logger.info("토큰을 검증하는 중...")
    if check_auth():
        logger.success("로그인 완료! 세션이 저장되었습니다.")
    else:
        logger.warn("토큰이 저장되었지만 검증에 실패했습니다. 토큰 값을 다시 확인해주세요.")
