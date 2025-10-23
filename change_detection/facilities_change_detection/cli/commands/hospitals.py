import datetime as dt
import typing
from pathlib import Path

import pandas as pd
import typer

from facilities_change_detection.core.hospitals import (
    add_hpi_likelihood,
    add_hpi_occupancy,
    compare_facilities_to_hpi,
    download_healthcert_gpkg,
    download_hpi_excel,
    load_facilities_hospitals,
    load_healthcert_hospitals,
    load_hpi_excel,
    update_linking_table,
)
from facilities_change_detection.core.io import add_styles_to_gpkg, get_layer_styles
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
    ] = Path.cwd()
    / "source_data",
    overwrite: typing.Annotated[
        bool,
        typer.Option(help="Whether to overwrite an existing file with the same name."),
    ] = False,
    create_output_folder_if_not_exists: typing.Annotated[
        bool,
        typer.Option(
            "--create", help="Whether to create the output folder if it doesn't exist."
        ),
    ] = True,
):
    if create_output_folder_if_not_exists is True:
        output_folder.mkdir(parents=True, exist_ok=True)
    try:
        download_hpi_excel(output_folder, overwrite)
    except Exception as e:
        logger.fatal(e)


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
    ] = Path.cwd()
    / "source_data",
    overwrite: typing.Annotated[
        bool,
        typer.Option(help="Whether to overwrite an existing file with the same name."),
    ] = False,
    create_output_folder_if_not_exists: typing.Annotated[
        bool,
        typer.Option(
            "--create", help="Whether to create the output folder if it doesn't exist."
        ),
    ] = True,
    progress: typing.Annotated[bool, typer.Option(help="Show progress bars")] = True,
):
    if create_output_folder_if_not_exists is True:
        output_folder.mkdir(parents=True, exist_ok=True)
    try:
        gdf = download_healthcert_gpkg(progress)
        output_file = output_folder / f"healthcert__{dt.date.today()}.gpkg"
        gdf.to_file(output_file)
    except Exception as e:
        logger.fatal(e)


@app.command()
def update_linking(
    hpi_file: typing.Annotated[
        Path,
        typer.Option(
            "-i_hpi",
            "--input-hpi",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to HPI file. Must be an Excel file downloaded from the Te Whatu Ora website [see command 'download-hpi-data'].",
            show_default=False,
        ),
    ],
    healthcert_file: typing.Annotated[
        Path,
        typer.Option(
            "-i_hc",
            "--input-healthcert",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to HealthCERT file. Must be a GeoPackage file of data scraped from the Ministry of Health website [see command 'download-healthcert-data'].",
            show_default=False,
        ),
    ],
    linking_file: typing.Annotated[
        Path,
        typer.Option(
            "-i_lin",
            "--input-linking",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to linking file. Must be a CSV with columns 'hpi_facility_id,healthcert_name'",
            show_default=False,
        ),
    ],
    output_linking_file: typing.Annotated[
        Path,
        typer.Option(
            "-o_lin",
            "--output-linking",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            writable=True,
            help="Path to output linking CSV.",
            show_default=False,
        ),
    ],
    output_missing_file: typing.Annotated[
        Path,
        typer.Option(
            "-o_mis",
            "--output-missing",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            writable=True,
            help="Path to output missing GeoPackage.",
            show_default=False,
        ),
    ],
):
    logger.info("Loading HPI Excel file")
    hpi_gdf = load_hpi_excel(hpi_file)
    logger.info("Loading HealthCERT GeoPackage")
    healthcert_gdf = load_healthcert_hospitals(healthcert_file)
    logger.info("Finding new HealthCERT features in HPI data")
    linking_df = pd.read_csv(linking_file)
    updated_linking_df, missing_gdf = update_linking_table(
        hpi_gdf, healthcert_gdf, linking_df
    )
    if matched_count := len(updated_linking_df) - len(linking_df):
        logger.info(
            f"Matched {matched_count} HealthCERT features not in the linking "
            "table by name to a HPi feature."
        )
        logger.info(f"Saving updated linking table to {output_linking_file}")
        updated_linking_df.to_csv(output_linking_file, index=False)
    if missing_count := len(missing_gdf):
        logger.info(
            f"{missing_count} HealthCERT features not in the linking table did "
            "not match any names in the HPI data - will require manual checking"
        )
        logger.info(f"Saving missing HealthCERT features to {output_missing_file}")
        missing_gdf.to_file(output_missing_file)


@app.command()
def compare(
    facilities_file: typing.Annotated[
        Path,
        typer.Option(
            "-i_fac",
            "--input-facilities",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to Facilities file. Must be a GeoPackage export of the LINZ NZ Facilities dataset.",
            show_default=False,
        ),
    ],
    hpi_file: typing.Annotated[
        Path,
        typer.Option(
            "-i_hpi",
            "--input-hpi",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to HPI file. Must be an Excel file downloaded from the Te Whatu Ora website [see command 'download-hpi-data'].",
            show_default=False,
        ),
    ],
    healthcert_file: typing.Annotated[
        Path,
        typer.Option(
            "-i_hc",
            "--input-healthcert",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to HealthCERT file. Must be a Excel file of data received from the Ministry of Health.",
            show_default=False,
        ),
    ],
    likelihood_file: typing.Annotated[
        Path,
        typer.Option(
            "-i_lik",
            "--input-likelihood",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to likelihood file. Must be a CSV with columns 'type,likelihood'.",
            show_default=False,
        ),
    ],
    linking_file: typing.Annotated[
        Path,
        typer.Option(
            "-i_lin",
            "--input-linking",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to linking file. Must be a CSV with columns 'hpi_facility_id,healthcert_name'",
            show_default=False,
        ),
    ],
    hpi_ignore_file: typing.Annotated[
        Path | None,
        typer.Option(
            "-i_hig",
            "--input-hpi-ignore",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            exists=True,
            readable=True,
            help="Path to HPI ignore list file. Must be a CSV with column 'hpi_facility_id'. Other columns may be present but will be ignored.",
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
            show_default=False,
        ),
    ],
    ignore_occupancy: typing.Annotated[
        bool,
        typer.Option(
            help="Whether to ignore occupancy when comparing Facilities to HPI data."
        ),
    ] = False,
):
    """
    Compares hospitals in the NZ Facilities dataset to new hospitals from
    Te Whatu Ora HPI data, augmented by occupancy from Ministry of Health
    HealthCERT data.

    This command has six required inputs: the three source data files
    (NZ Facilities Geopackage, HPI Excel, and HealthCERT Excel), and three
    additional helper files (a likelihood CSV, a linking CSV, and an HPI ignore
    CSV).

    Each of the three source files is read in, with NZ Facilities filtered to
    only include Hospitals, and the HPI filtered to exclude any feature present
    in the ignore list. Estimated occupancy is added to the HPI data from the
    HealthCERT data (where present), using the linking CSV to match HealthCERT
    names to HPi Facility IDs. The merged data is then compared against the
    NZ Facilities data.

    The output is a single GeoPackage file with three layers:
    'hospital_facilities' which is the input Facilities layer with additional
    columns describing the differences with the HPI data, hpi_matched, which is
    the features from the HPI data which matched with a feature in the
    Facilities data, and hpi_new, which is all features in the HPI data not
    present in the Facilities data nor in the ignore list.
    """
    try:
        logger.info("Loading Facilities GeoPackage")
        facilities_gdf = load_facilities_hospitals(facilities_file)
        logger.info("Loading HPI Excel file")
        hpi_gdf = load_hpi_excel(hpi_file, hpi_ignore_file)
        logger.info("Loading HealthCERT Excel")
        healthcert_gdf = load_healthcert_hospitals(healthcert_file)
        logger.info("Assigning likelihood to HPI features")
        hpi_gdf = add_hpi_likelihood(hpi_gdf, likelihood_file)
        logger.info("Augmenting HPI with HealthCERT occupancy")
        hpi_gdf = add_hpi_occupancy(hpi_gdf, healthcert_gdf, linking_file)
        logger.info("Comparing Facilities to HPI")
        facilities_gdf, hpi_new_gdf, hpi_matched_gdf = compare_facilities_to_hpi(
            facilities_gdf, hpi_gdf, ignore_occupancy
        )
        logger.info("Saving layers to output GeoPackage")
        facilities_gdf.to_file(output_file, layer="hospital_facilities")
        hpi_new_gdf.to_file(output_file, layer="hpi_new")
        hpi_matched_gdf.to_file(output_file, layer="hpi_matched")
        logger.info("Adding layer styles to GeoPackage")
        layer_styles = get_layer_styles(
            {
                "hospital_facilities": "hospital_facilities.qml",
                "hpi_new": "hpi_new.qml",
                "hpi_matched": "hpi_matched.qml",
            }
        )
        add_styles_to_gpkg(output_file, layer_styles)
    except Exception as e:
        logger.fatal(e)
