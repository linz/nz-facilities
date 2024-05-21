import typing
from pathlib import Path

import geopandas as gpd
import typer

from facilities_change_detection.core.log import get_logger
from facilities_change_detection.core.polygonise import find_points_in_titles_with_owners

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
    titles_file: typing.Annotated[
        Path,
        typer.Option(
            "-t",
            "--titles-file",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            help="Titles with Owners file.",
        ),
    ],
    input_layer: typing.Annotated[
        str, typer.Option(help="Layer name in the input file if it contains multiple layers.")
    ] = None,
):
    logger.info(f"Reading input from {input_file}")
    gdf = gpd.read_file(input_file, layer=input_layer, engine="pyogrio", use_arrow=True)
    gdf.sindex
    gdf = find_points_in_titles_with_owners(gdf, titles_file)
    logger.info(f"Saving output to {output_file}")
    gdf.to_file(output_file)
