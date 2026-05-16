import json as jsonlib
from datetime import datetime, timezone
from pathlib import Path

import typer

from vcli.adapters.velog.api import upload_image_file
from vcli.adapters.velog.auth import check_auth
from vcli.core.images import file_sha256, workspace_relative_path
from vcli.core.uploads import upsert_upload
from vcli.models import UploadEntry
from vcli.utils import logger
from vcli.utils.paths import find_project_root

image_app = typer.Typer(help="Upload images to Velog CDN.")


@image_app.command(name="upload")
def upload(
    path: Path = typer.Argument(..., help="Local image file to upload"),
    post_slug: str | None = typer.Option(
        None,
        "--post",
        help="Optional post slug to store with the upload record",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print machine-readable JSON",
    ),
) -> None:
    """Upload one local image and print the Velog CDN URL."""
    root = find_project_root()
    image_path = path.resolve()

    if not image_path.exists() or not image_path.is_file():
        logger.error(f"Image file not found: {path}")
        raise typer.Exit(1)

    if not check_auth():
        logger.error("Velog login required. Run `vcli login` first.")
        raise typer.Exit(1)

    sha = file_sha256(image_path)
    local_path = workspace_relative_path(root, image_path)
    url = upload_image_file(image_path, image_type="post")
    uploaded_at = datetime.now(timezone.utc).isoformat()

    entry = UploadEntry(
        local_path=local_path,
        url=url,
        sha256=sha,
        post_slug=post_slug,
        uploaded_at=uploaded_at,
    )
    upsert_upload(root, entry)

    if json_output:
        typer.echo(jsonlib.dumps(entry.model_dump(mode="json", exclude_none=True), ensure_ascii=False))
        return

    typer.echo(url)
