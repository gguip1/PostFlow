import shutil
import sys
from pathlib import Path

from vcli.core.config import config_exists, load_config
from vcli.utils import logger
from vcli.utils.paths import (
    find_project_root,
    get_config_path,
    get_posts_dir,
    get_registry_path,
)


def doctor() -> None:
    """로컬 환경과 .vcli 저장소 상태를 점검합니다."""
    all_ok = True

    try:
        root = find_project_root()
        logger.info(f"작업 폴더: {root}")
    except FileNotFoundError as error:
        root = Path.cwd()
        logger.error(str(error))
        all_ok = False

    ver = sys.version_info
    if ver >= (3, 12):
        logger.success(f"Python {ver.major}.{ver.minor}.{ver.micro}")
    else:
        logger.error(f"Python {ver.major}.{ver.minor}.{ver.micro} (3.12 이상 필요)")
        all_ok = False

    if config_exists(root):
        config = load_config(root)
        logger.success(str(get_config_path(root)))
        if config.velog.username:
            logger.info(f"Velog 사용자명: {config.velog.username}")
        else:
            logger.info("로컬 설정에 Velog 사용자명이 없습니다.")
    else:
        logger.error(f"{get_config_path(root)} 파일이 없습니다.")
        all_ok = False

    registry_path = get_registry_path(root)
    if registry_path.exists():
        logger.success(str(registry_path))
    else:
        logger.error(f"{registry_path} 파일이 없습니다.")
        all_ok = False

    posts_dir = get_posts_dir(root)
    if posts_dir.exists():
        post_count = sum(
            1
            for entry in posts_dir.iterdir()
            if entry.is_dir() and (entry / "meta.yaml").exists()
        )
        logger.success(f"글 폴더: {posts_dir} ({post_count}개)")
    else:
        logger.error(f"{posts_dir} 폴더가 없습니다.")
        all_ok = False

    from vcli.adapters.velog.auth import auth_exists, check_auth

    if auth_exists():
        if check_auth():
            logger.success("Velog 인증: 유효함")
        else:
            logger.warn("Velog 인증: 저장되어 있지만 만료됨")
    else:
        logger.info("Velog 인증: 로그인되지 않음")

    if shutil.which("gh"):
        logger.success("GitHub CLI: 설치됨")
    else:
        logger.info("GitHub CLI: 설치되지 않음")

    if all_ok:
        logger.success("doctor 점검을 통과했습니다.")
    else:
        logger.warn("doctor 점검에서 문제가 발견되었습니다.")
