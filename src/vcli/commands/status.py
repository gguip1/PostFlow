from rich.table import Table

from vcli.core.registry import calculate_status, load_registry
from vcli.utils.logger import console
from vcli.utils.paths import find_project_root


def status() -> None:
    """Show local vcli post sync status."""
    root = find_project_root()
    registry = load_registry(root)

    if not registry.posts:
        console.print("No posts. Run `vcli create` or `vcli pull`.")
        return

    table = Table(title="vcli status")
    table.add_column("Status")
    table.add_column("Slug")
    table.add_column("URL")

    for entry in registry.posts:
        table.add_row(calculate_status(root, entry), entry.slug, entry.url or "")

    console.print(table)
