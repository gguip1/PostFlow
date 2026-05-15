from pathlib import Path

from vcli.models import Config
from vcli.utils.fs import read_yaml, write_yaml


def workspace_dir(root: Path) -> Path:
    return root / ".vcli"


def config_path(root: Path) -> Path:
    return workspace_dir(root) / "config.yaml"


def registry_path(root: Path) -> Path:
    return workspace_dir(root) / "registry.yaml"


def posts_dir(root: Path) -> Path:
    return workspace_dir(root) / "posts"


def is_workspace_root(path: Path) -> bool:
    return workspace_dir(path).is_dir() and registry_path(path).exists()


def find_workspace_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()

    for parent in [current, *current.parents]:
        if is_workspace_root(parent):
            return parent

    raise FileNotFoundError(
        "vcli workspace not found. Run `vcli init` in the folder you want to manage."
    )


def init_workspace(root: Path) -> Path:
    resolved = root.resolve()

    workspace_dir(resolved).mkdir(parents=True, exist_ok=True)
    posts_dir(resolved).mkdir(parents=True, exist_ok=True)

    if not config_path(resolved).exists():
        write_yaml(config_path(resolved), Config().model_dump(mode="json"))

    registry = {}
    if registry_path(resolved).exists():
        registry = read_yaml(registry_path(resolved))
    registry.setdefault("version", 1)
    registry.setdefault("posts", [])
    write_yaml(registry_path(resolved), registry)

    return resolved
