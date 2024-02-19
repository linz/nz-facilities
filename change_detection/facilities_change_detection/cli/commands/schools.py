import datetime
import typing
from pathlib import Path

import typer

import facilities_change_detection.core.facilities
import facilities_change_detection.core.io
from facilities_change_detection.cli import parsers
from facilities_change_detection.cli import callbacks
from facilities_change_detection.core import schools
from facilities_change_detection.core.facilities import DBConnectionDetails
from facilities_change_detection.core.log import get_logger

logger = get_logger()


def compare_schools(
    input_file: typing.Annotated[
        Path | None,
        typer.Option(
            exists=True,
            dir_okay=False,
            resolve_path=True,
            help=(
                "Path to an OGR readable file containing the NZ facilities dataset. "
                "One, but not both, of --input-file and --input-db must be passed."
            ),
        ),
    ] = None,
    input_db: typing.Annotated[
        DBConnectionDetails | None,
        typer.Option(
            parser=parsers.parse_facilities_db_connection_details,
            metavar="",
            help=(
                "Connection details to load the NZ facilities dataset from a postgreSQL database. "
                "Must be a JSON formatted string containing the values for these keys: "
                "name, host, port, user, password, schema, table."
            ),
        ),
    ] = None,
    overwrite: typing.Annotated[bool, typer.Option(help="Overwrite the specified output file if it exists")] = False,
    output: typing.Annotated[
        Path,
        typer.Option(
            default=...,
            dir_okay=False,
            resolve_path=True,
            callback=callbacks.output_file_callback,
            help="Output file location. Must be a valid path a file ending in .gpkg.",
        ),
    ] = Path.cwd()
    / "facilities_change_detection.gpkg",
    moe_api_input: typing.Annotated[
        Path | None,
        typer.Option(
            exists=True,
            dir_okay=False,
            resolve_path=True,
            help=(
                "Path to response from the MOE API saved from a previous run of this script. "
                "If passed, this data will be used instead of querying the API. Useful for testing."
            ),
        ),
    ] = None,
    comparison_attrs: typing.Annotated[
        set[str],
        typer.Option(
            "--compare",
            parser=parsers.parse_comparison_arg,
            metavar="",
            help=(
                f"Comma separated list of attributes to compare on. "
                f"Valid options are {','.join(facilities_change_detection.core.facilities.get_comparable_attrs(schools.FacilitiesSchool, schools.MOESchool))}."
            ),
        ),
    ] = ",".join(facilities_change_detection.core.facilities.Source.get_comparable_attrs(default=True)),
) -> None:
    if input_file is not None and input_db is not None:
        raise typer.BadParameter("Only one of --input-file or --input-db may be passed.")
    elif input_file is not None:
        logger.info("Loading facilities from file")
        facilities_schools = facilities_change_detection.core.io.load_file_source(input_file)
    elif input_db is not None:
        logger.info("Loading facilities from DB")
        facilities_schools = facilities_change_detection.core.io.load_db_source(input_db)
    else:
        raise typer.BadParameter("One of --input-file or --input must be passed.")

    moe_api_output = output.parent / f"{output.stem}__moe_api_response_{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}.json"
    moe_schools = schools.request_moe_api(api_response_input_path=moe_api_input, api_response_output_path=moe_api_output)
    logger.info("Filtering MOE schools")
    moe_schools = schools.filter_moe_schools(moe_schools)

    logger.info("Comparing MOE and facilities schools")
    facilities_schools, moe_schools = schools.compare_schools(facilities_schools, moe_schools, comparison_attrs)

    facilities_change_detection.core.io.save_layers_to_gpkg(
        output_file=output,
        layer_schema=schools.FacilitiesSchool.schema,
        layer_data=facilities_schools.values(),
        layer_name="nz_facilities",
    )
    facilities_change_detection.core.io.save_layers_to_gpkg(
        output_file=output, layer_schema=schools.MOESchool.schema, layer_data=moe_schools.values(), layer_name="moe_schools"
    )
