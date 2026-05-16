from rich.table import Table

from vcli.core.registry import calculate_status, load_registry
from vcli.utils.logger import console
from vcli.utils.paths import find_project_root


def status() -> None:
    """로컬 vcli 글 상태를 보여줍니다."""
    root = find_project_root()
    registry = load_registry(root)

    if not registry.posts:
        console.print("글이 없습니다. `vcli create` 또는 `vcli pull`을 실행하세요.")
        return

    table = Table(title="vcli 상태")
    table.add_column("상태")
    table.add_column("Slug")
    table.add_column("URL")

    for entry in registry.posts:
        table.add_row(calculate_status(root, entry), entry.slug, entry.url or "")

    console.print(table)
