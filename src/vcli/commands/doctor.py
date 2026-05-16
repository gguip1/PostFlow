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
    """Show local environment and .vcli store status."""
    all_ok = True

    try:
        root = find_project_root()
        logger.info(f"Workspace root: {root}")
    except FileNotFoundError as error:
        root = Path.cwd()
        logger.error(str(error))
        all_ok = False

    ver = sys.version_info
    if ver >= (3, 12):
        logger.success(f"Python {ver.major}.{ver.minor}.{ver.micro}")
    else:
        logger.error(f"Python {ver.major}.{ver.minor}.{ver.micro} (requires 3.12+)")
        all_ok = False

    if config_exists(root):
        config = load_config(root)
        logger.success(str(get_config_path(root)))
        if config.velog.username:
            logger.info(f"Velog username: {config.velog.username}")
        else:
            logger.info("Velog username is not set in local config.")
    else:
        logger.error(f"{get_config_path(root)} is missing")
        all_ok = False

    registry_path = get_registry_path(root)
    if registry_path.exists():
        logger.success(str(registry_path))
    else:
        logger.error(f"{registry_path} is missing")
        all_ok = False

    posts_dir = get_posts_dir(root)
    if posts_dir.exists():
        post_count = sum(
            1
            for entry in posts_dir.iterdir()
            if entry.is_dir() and (entry / "meta.yaml").exists()
        )
        logger.success(f"Posts directory: {posts_dir} ({post_count} post(s))")
    else:
        logger.error(f"{posts_dir} is missing")
        all_ok = False

    from vcli.adapters.velog.auth import auth_exists, check_auth

    if auth_exists():
        if check_auth():
            logger.success("Velog auth: valid")
        else:
            logger.warn("Velog auth: stored but expired")
    else:
        logger.info("Velog auth: not logged in")

    if shutil.which("gh"):
        logger.success("GitHub CLI: installed")
    else:
        logger.info("GitHub CLI: not installed")

    if all_ok:
        logger.success("Doctor check passed")
    else:
        logger.warn("Doctor found one or more issues")
