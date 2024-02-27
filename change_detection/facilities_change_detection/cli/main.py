import typer

from facilities_change_detection.cli.commands.schools import compare_schools
from facilities_change_detection.cli.commands.hospitals import compare_hospitals
from facilities_change_detection.core.log import setup_logging

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)
app.command()(compare_schools)
app.command()(compare_hospitals)

if __name__ == "__main__":
    setup_logging()
    app()
