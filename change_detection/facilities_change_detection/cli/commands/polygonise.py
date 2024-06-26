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
            help="Titles with Owners file.",
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
            help="Titles with Owners file.",
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
):
    logger.info(f"Reading input from {input_file}")
    gdf = gpd.read_file(input_file, layer=input_layer, engine="pyogrio", use_arrow=True)
    gdf = gdf.to_crs(2193)
    gdf.sindex
    titles_gdf = build_titles_with_owners(titles_file, owners_file, use_standardised_names)
    gdf = find_points_in_titles_with_owners(gdf, titles_gdf, use_standardised_names, distance_threshold)
    logger.info(f"Saving output to {output_file}")
    gdf.to_file(output_file)
