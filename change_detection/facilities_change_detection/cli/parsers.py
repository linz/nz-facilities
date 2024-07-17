import json

import typer

from facilities_change_detection.core.facilities import DBConnectionDetails, Source


def parse_facilities_db_connection_details(input_arg: str) -> DBConnectionDetails:
    """
    Validates the JSON string passed in by the user. It must be
    formatted correctly and contain all, and only, the fields required
    for the db connection.
    """
    # Parse JSON
    try:
        dbconn = json.loads(input_arg)
    except ValueError as error:
        raise typer.BadParameter("Invalid JSON") from error
    # Validate JSON keys are the ones we want for the db connection
    valid_keys = DBConnectionDetails.keys()
    valid_keys_msg = ", ".join(f'"{k}"' for k in valid_keys)
    # Check all keys are valid according to schema
    if extra_fields := dbconn.keys() - valid_keys:
        raise typer.BadParameter(f"'{extra_fields}' not a valid JSON key for facilities db. Valid keys are: {valid_keys_msg}")
    # Check for missing keys
    if missing_fields := valid_keys - dbconn.keys():
        raise typer.BadParameter(f"'{missing_fields}' is missing from JSON string. Required keys are: {valid_keys_msg}")
    for k, v in dbconn.items():
        expected_type = DBConnectionDetails.__annotations__[k]
        if not isinstance(v, expected_type):
            raise typer.BadParameter(f"Value '{v}' for '{k}' is of type '{type(v)}', should be type '{expected_type}'")
    return dbconn


def parse_comparison_arg(comparison_arg: str) -> list[str]:
    """
    Validates the attributes to perform the comparison with.
    Must be a comma separated list of valid comparable attributes, being an
    attribute with the type hint of typing.Annotated[<type>, COMPARABLE] which
    exists on both classes. If any invalid attributes or no valid attributes are
    passed, a FatalError exception will be raised.
    """
    options = Source.comparable_attrs()
    options_msg = f"Valid options are {','.join(sorted(options))}."
    parts = comparison_arg.split(",")
    valid_attrs = []
    invalid_attrs = []
    for part in parts:
        if part in options:
            valid_attrs.append(part)
        else:
            invalid_attrs.append(part)
    if invalid_attrs:
        if len(invalid_attrs) == 1:
            raise typer.BadParameter(f'"{invalid_attrs[0]}" is not a valid attribute to compare on. {options_msg}')
        else:
            raise typer.BadParameter(f'"{', '.join(invalid_attrs)}" are not valid attributes to compare on. {options_msg}.')
    if not valid_attrs:
        raise typer.BadParameter(f"No valid attributes to compare on were passed. {options_msg}")
    return valid_attrs
