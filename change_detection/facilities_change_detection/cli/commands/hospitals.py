import typing
from pathlib import Path

import typer

from facilities_change_detection.core.hospitals import assign_hpi_likelihood, download_hpi_excel, load_hpi_excel
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
        download_hpi_excel(output_folder, overwrite)
    except Exception as e:
        logger.fatal(e)


@app.command()
def load_hpi_file(
    input_file: typing.Annotated[
        Path,
        typer.Option(
            "-i",
            "--input-file",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to input HPI Excel file.",
        ),
    ],
    output_file: typing.Annotated[
        Path,
        typer.Option(
            "-o",
            "--output-file",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            writable=True,
            help="Path to output GeoPackage.",
        ),
    ],
    likelihood_file: typing.Annotated[
        Path,
        typer.Option(
            "-l",
            "--likelihood-file",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to likelihood CSV file.",
        ),
    ],
):
    try:
        logger.info("Loading Excel file")
        gdf = load_hpi_excel(input_file)
        logger.info("Assigning likelihood")
        gdf = assign_hpi_likelihood(gdf, likelihood_file)
        logger.info("Saving GeoPackage")
        gdf.to_file(output_file)
    except Exception as e:
        logger.fatal(e)