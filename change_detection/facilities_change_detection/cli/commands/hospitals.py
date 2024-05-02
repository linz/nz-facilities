import datetime
import typing
from pathlib import Path

import typer

from facilities_change_detection.core.hospitals import download_hpi_excel
from facilities_change_detection.core.log import get_logger

logger = get_logger()

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.command()
def download_hpi_data(
    output_folder: typing.Annotated[
        Path,
        typer.Option(
            "-o",
            "--output-folder",
            dir_okay=True,
            file_okay=False,
            resolve_path=True,
            help="Folder where you want to download the data to.",
        ),
    ] = Path.cwd() / "source_data",
    overwrite: typing.Annotated[bool, typer.Option(help="Whether to overwrite an existing file with the same name.")] = False,
    create_output_folder_if_not_exists: typing.Annotated[
        bool, typer.Option("--create", help="Whether to create the output folder if it doesn't exist.")
    ] = True,
):
    if create_output_folder_if_not_exists is True:
        output_folder.mkdir(parents=True, exist_ok=True)
    try:
        print(logger.getEffectiveLevel())
        download_hpi_excel(output_folder, overwrite)
    except Exception as e:
        logger.fatal(e)
