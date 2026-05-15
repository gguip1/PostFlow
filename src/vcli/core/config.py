from pathlib import Path

from vcli.models import Config
from vcli.utils.fs import read_yaml, write_yaml
from vcli.utils.paths import get_config_path


def load_config(root: Path) -> Config:
    path = get_config_path(root)
    if not path.exists():
        raise FileNotFoundError("vcli config not found. Run `vcli init` first.")
    return Config(**read_yaml(path))


def save_config(root: Path, config: Config) -> None:
    write_yaml(get_config_path(root), config.model_dump(mode="json"))


def config_exists(root: Path) -> bool:
    return get_config_path(root).exists()
