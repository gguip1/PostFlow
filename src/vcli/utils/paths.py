from pathlib import Path

from vcli.core.workspace import find_workspace_root, posts_dir, registry_path


def find_project_root(start: Path | None = None) -> Path:
    return find_workspace_root(start)


def get_posts_dir(root: Path, posts_dir_name: str = "posts") -> Path:
    return posts_dir(root)


def get_post_dir(root: Path, slug: str, posts_dir_name: str = "posts") -> Path:
    return posts_dir(root) / slug


def get_registry_path(root: Path, posts_dir_name: str = "posts") -> Path:
    return registry_path(root)


def get_config_path(root: Path) -> Path:
    from vcli.core.workspace import config_path

    return config_path(root)
