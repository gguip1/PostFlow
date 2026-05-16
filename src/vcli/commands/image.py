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

image_app = typer.Typer(help="이미지를 Velog CDN에 업로드합니다.")


@image_app.command(name="upload")
def upload(
    path: Path = typer.Argument(..., help="업로드할 로컬 이미지 파일"),
    post_slug: str | None = typer.Option(
        None,
        "--post",
        help="업로드 기록에 함께 저장할 글 slug",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="에이전트가 파싱하기 쉬운 JSON으로 출력",
    ),
) -> None:
    """로컬 이미지 하나를 업로드하고 Velog CDN URL을 출력합니다."""
    root = find_project_root()
    image_path = path.resolve()

    if not image_path.exists() or not image_path.is_file():
        logger.error(f"이미지 파일을 찾을 수 없습니다: {path}")
        raise typer.Exit(1)

    if not check_auth():
        logger.error("Velog 로그인이 필요합니다. 먼저 `vcli login`을 실행하세요.")
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
