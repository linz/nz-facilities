import typing
from pathlib import Path

import geopandas as gpd
import typer

from facilities_change_detection.core.log import get_logger
from facilities_change_detection.core.polygonise import (
    build_titles_with_owners,
    find_points_in_titles_with_owners,
)

logger = get_logger()


def polygonise(
    input_file: typing.Annotated[
        Path,
        typer.Option(
            "-i",
            "--input-file",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            help="Input file to read points from.",
        ),
    ],
    titles_file: typing.Annotated[
        Path,
        typer.Option(
            "-i_ti",
            "--input-titles-file",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            help="NZ Property Titles GeoPackage exported from LDS.",
        ),
    ],
    owners_file: typing.Annotated[
        Path,
        typer.Option(
            "-i_ow",
            "--input-owners-file",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            help="NZ Property Titles Owners List CSV exported from LDS.",
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
            help="Output file to save polygonised layer to.",
        ),
    ],
    input_layer: typing.Annotated[
        str, typer.Option(help="Layer name in the input file if it contains multiple layers.")
    ] = None,
    use_standardised_names: typing.Annotated[
        bool, typer.Option(help="Whether to join adjacent polygons by comparing standardised, or actual owner names.")
    ] = True,
    distance_threshold: typing.Annotated[
        int, typer.Option(help="Distance in metres of how close titles with a same name must be to be merged together.")
    ] = 50,
    save_titles_file: typing.Annotated[
        Path,
        typer.Option(
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            help=(
                "Optional path to save the combined titles with owners file to."
                "Will only be saved if a path to a file is passed via this parameter."
            ),
        ),
    ] = None,
):
    logger.info(f"Reading input from {input_file}")
    input_gdf = gpd.read_file(input_file, layer=input_layer, engine="pyogrio", use_arrow=True)
    input_gdf = input_gdf.to_crs(2193)
    input_gdf.sindex
    titles_gdf = build_titles_with_owners(titles_file, owners_file, use_standardised_names)
    if save_titles_file is not None:
        logger.info(f"Saving combined titles with owners layer to {save_titles_file}")
        titles_gdf.to_file(save_titles_file, engine="pyogrio")
    input_gdf = find_points_in_titles_with_owners(input_gdf, titles_gdf, use_standardised_names, distance_threshold)
    logger.info(f"Saving output to {output_file}")
    input_gdf.to_file(output_file)
