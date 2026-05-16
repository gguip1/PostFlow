from pathlib import Path

import typer

from vcli.core.workspace import init_workspace
from vcli.utils import logger


def init(
    path: Path = typer.Option(
        ".", "--path", "-p", help="vcli 저장소로 초기화할 폴더"
    ),
) -> None:
    """로컬 .vcli 저장소를 초기화합니다."""
    root = init_workspace(path)
    logger.success(f"vcli 저장소를 초기화했습니다: {root / '.vcli'}")
