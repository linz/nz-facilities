import typer

from facilities_change_detection.cli.commands import hospitals
from facilities_change_detection.cli.commands.schools import compare_schools
from facilities_change_detection.core.log import setup_logging

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)
app.command()(compare_schools)
app.add_typer(hospitals.app, name="hospitals")


@app.callback()
def _setup_logging():
    setup_logging()


if __name__ == "__main__":
    app()
