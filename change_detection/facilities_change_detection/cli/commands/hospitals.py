import datetime as dt
import typing
from enum import Enum
from pathlib import Path

import click
import typer
from tqdm.contrib.logging import logging_redirect_tqdm

from facilities_change_detection.core.hospitals import (
    assign_hpi_likelihood,
    compare_facilities_gdf_to_hpi_gdf,
    download_hpi_excel,
    load_hpi_excel,
    read_hospital_facilities,
    scrape_healthcert_map_page,
)
from facilities_change_detection.core.io import add_styles_to_gpkg, get_layer_styles
from facilities_change_detection.core.log import get_logger
from facilities_change_detection.core.util import gdf_concat

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


healthcert_kinds = {"public": "Public hospital", "private": "Private hospital", "resthome": "Rest home", "all": "all"}


def validate_healthcert_kinds_args(kind_codes: list[str]) -> tuple[list[str], str]:
    # Convert the list of kind_codes to a set to remove any duplicates
    kind_codes = set(kind_codes)
    # Remove "all" from the list of allowed kinds
    healthcert_kinds.pop("all")
    # If "all" was one of the kind_codes we received, or we received every
    # possible option, return a list of all the options with a name of "all"
    if "all" in kind_codes or kind_codes == healthcert_kinds.keys():
        kinds = list(healthcert_kinds.values())
        kinds_name = "all"
    # Else, return a list of the kinds with a name of their codes,
    # separated by commas
    else:
        # Sort the set first to ensure the order is always the same
        kind_codes = sorted(kind_codes)
        kinds = [healthcert_kinds[kind_code] for kind_code in kind_codes]
        kinds_name = ",".join(kind_codes)
    return kinds, kinds_name


@app.command()
def download_healthcert_data(
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
    kind_codes: typing.Annotated[
        list[str],
        typer.Option(
            "-k",
            "--kind",
            click_type=click.Choice(choices=healthcert_kinds.keys()),
            help="Which HealthCERT webmap to scrape more chars.",
        ),
    ] = ["all"],
    overwrite: typing.Annotated[bool, typer.Option(help="Whether to overwrite an existing file with the same name.")] = False,
    create_output_folder_if_not_exists: typing.Annotated[
        bool, typer.Option("--create", help="Whether to create the output folder if it doesn't exist.")
    ] = True,
    progress: typing.Annotated[bool, typer.Option(help="Show progress bars")] = True,
):
    if create_output_folder_if_not_exists is True:
        output_folder.mkdir(parents=True, exist_ok=True)
    try:
        kinds, kinds_name = validate_healthcert_kinds_args(kind_codes)
        if progress is True:
            with logging_redirect_tqdm(loggers=[logger]):
                gdfs = [scrape_healthcert_map_page(kind, progress) for kind in kinds]
        else:
            gdfs = [scrape_healthcert_map_page(kind, progress) for kind in kinds]
        gdf = gdf_concat(gdfs)
        output_file = output_folder / f"healthcert__{kinds_name}__{dt.date.today()}.gpkg"
        gdf.to_file(output_file)
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
        gdf.to_file(output_file, laywer="hpi")
        logger.info("Adding layer styles to GeoPackage")
        add_styles_to_gpkg(output_file, get_layer_styles({"hpi": "hpi_new.qml"}))
    except Exception as e:
        logger.fatal(e)


@app.command()
def compare_facilities_to_hpi(
    facilities_file: typing.Annotated[
        Path,
        typer.Option(
            "-if",
            "--input-file-facilities",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to Facilities GeoPackage file.",
        ),
    ],
    hpi_file: typing.Annotated[
        Path,
        typer.Option(
            "-ih",
            "--input-file-hpi",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to HPI Excel file.",
        ),
    ],
    likelihood_file: typing.Annotated[
        Path,
        typer.Option(
            "-il",
            "--input-file-likelihood",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to likelihood CSV file.",
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
    ignore_file: typing.Annotated[
        Path | None,
        typer.Option(
            "-ii",
            "--input-file-ignore",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to ignore list CSV file.",
        ),
    ] = None,
):
    try:
        logger.info("Loading HPI Excel file")
        hpi_gdf = load_hpi_excel(hpi_file, ignore_file)
        logger.info("Assigning likelihood")
        hpi_gdf = assign_hpi_likelihood(hpi_gdf, likelihood_file)
        logger.info("Loading Facilities GeoPackage")
        facilities_gdf = read_hospital_facilities(facilities_file)
        logger.info("Comparing Facilities to HPI")
        facilities_gdf, hpi_new_gdf, hpi_matched_gdf = compare_facilities_gdf_to_hpi_gdf(facilities_gdf, hpi_gdf)
        logger.info("Saving layers to output GeoPackage")
        facilities_gdf.to_file(output_file, layer="hospital_facilities")
        hpi_new_gdf.to_file(output_file, layer="hpi_new")
        hpi_matched_gdf.to_file(output_file, layer="hpi_matched")
        logger.info("Adding layer styles to GeoPackage")
        layer_styles = get_layer_styles(
            {"hospital_facilities": "hospital_facilities.qml", "hpi_new": "hpi_new.qml", "hpi_matched": "hpi_matched.qml"}
        )
        add_styles_to_gpkg(output_file, layer_styles)
    except Exception as e:
        logger.fatal(e)