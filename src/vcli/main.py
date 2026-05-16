import typer

from vcli.commands.check import check
from vcli.commands.create import create
from vcli.commands.doctor import doctor
from vcli.commands.import_posts import pull
from vcli.commands.init import init
from vcli.commands.list import list_posts
from vcli.commands.login import login_cmd
from vcli.commands.logout import logout
from vcli.commands.publish import push
from vcli.commands.status import status

app = typer.Typer(
    name="vcli",
    help="AI-first Velog writing CLI.",
    no_args_is_help=True,
)

app.command(name="create")(create)
app.command(name="list")(list_posts)
app.command(name="check")(check)
app.command(name="doctor")(doctor)
app.command(name="login")(login_cmd)
app.command(name="logout")(logout)
app.command(name="push")(push)
app.command(name="publish", hidden=True, deprecated=True)(push)
app.command(name="pull")(pull)
app.command(name="sync", hidden=True, deprecated=True)(pull)
app.command(name="init")(init)
app.command(name="status")(status)

if __name__ == "__main__":
    app()
