from importlib.metadata import PackageNotFoundError, version

import typer

from vcli.commands.check import check
from vcli.commands.create import create
from vcli.commands.doctor import doctor
from vcli.commands.import_posts import pull
from vcli.commands.image import image_app
from vcli.commands.init import init
from vcli.commands.list import list_posts
from vcli.commands.login import login_cmd
from vcli.commands.logout import logout
from vcli.commands.push import push
from vcli.commands.status import status


def _package_version() -> str:
    try:
        return version("unofficial-velog-cli")
    except PackageNotFoundError:
        return "unknown"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(_package_version())
        raise typer.Exit()


app = typer.Typer(
    name="vcli",
    help="AI 에이전트가 Velog 글을 안전하게 가져오고 발행하도록 돕는 CLI.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main(
    show_version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="설치된 vcli 버전을 출력합니다.",
    ),
) -> None:
    """vcli 최상위 옵션을 처리합니다."""


app.command(name="create")(create)
app.command(name="list")(list_posts)
app.command(name="check")(check)
app.command(name="doctor")(doctor)
app.command(name="login")(login_cmd)
app.command(name="logout")(logout)
app.command(name="push")(push)
app.command(name="pull")(pull)
app.command(name="init")(init)
app.command(name="status")(status)
app.add_typer(image_app, name="image")

if __name__ == "__main__":
    app()
