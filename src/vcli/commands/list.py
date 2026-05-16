import typer
from rich.table import Table

from vcli.core.post import read_post
from vcli.core.registry import calculate_status, load_registry
from vcli.utils.logger import console
from vcli.utils.paths import find_project_root


def list_posts(
    status: str = typer.Option(
        None, "--status", "-s", help="Filter by status: draft, modified, synced"
    ),
) -> None:
    """List posts in the local .vcli store."""
    root = find_project_root()
    registry = load_registry(root)

    if status:
        valid_statuses = {"draft", "modified", "synced"}
        if status not in valid_statuses:
            console.print("Status must be one of: draft, modified, synced")
            raise typer.Exit(1)

    rows = []
    for entry in registry.posts:
        calculated_status = calculate_status(root, entry)
        if status and calculated_status != status:
            continue

        try:
            meta, _ = read_post(root, entry.slug)
            title = meta.title
        except FileNotFoundError:
            title = ""

        rows.append((calculated_status, entry.slug, title, entry.url or ""))

    if not rows:
        if status:
            console.print(f"No posts with status '{status}'.")
        else:
            console.print("No posts yet. Run `vcli create` to start one.")
        return

    table = Table(title=f"Posts ({len(rows)})")
    table.add_column("Status", style="green")
    table.add_column("Slug", style="cyan")
    table.add_column("Title")
    table.add_column("URL", style="dim")

    for row in rows:
        table.add_row(*row)

    console.print(table)
