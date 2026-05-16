import typer
from rich.table import Table

from vcli.core.post import read_post
from vcli.core.registry import calculate_status, load_registry
from vcli.utils.logger import console
from vcli.utils.paths import find_project_root


def list_posts(
    status: str = typer.Option(
        None, "--status", "-s", help="상태로 필터링: draft, modified, synced"
    ),
) -> None:
    """로컬 .vcli 저장소의 글 목록을 보여줍니다."""
    root = find_project_root()
    registry = load_registry(root)

    if status:
        valid_statuses = {"draft", "modified", "synced"}
        if status not in valid_statuses:
            console.print("상태는 draft, modified, synced 중 하나여야 합니다.")
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
            console.print(f"'{status}' 상태의 글이 없습니다.")
        else:
            console.print("글이 없습니다. `vcli create`로 새 글을 만드세요.")
        return

    table = Table(title=f"글 목록 ({len(rows)})")
    table.add_column("상태", style="green")
    table.add_column("Slug", style="cyan")
    table.add_column("제목")
    table.add_column("URL", style="dim")

    for row in rows:
        table.add_row(*row)

    console.print(table)
