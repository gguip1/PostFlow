from pathlib import Path

import typer

from vcli.core.workspace import init_workspace
from vcli.utils import logger


def init(
    path: Path = typer.Option(
        ".", "--path", "-p", help="Folder to initialize as a vcli workspace"
    ),
) -> None:
    """Initialize a local .vcli store."""
    root = init_workspace(path)
    logger.success(f"Initialized vcli workspace: {root / '.vcli'}")
