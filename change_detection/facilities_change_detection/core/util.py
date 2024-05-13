import re
import unicodedata
from typing import Any

import geopandas as gpd
import pandas as pd


def standardise_column_name(name: str):
    """
    Standardises a supplied name to use column name.

    The standardised form will be lowercase with underscores between words,
    with non-ascii characters converted to their closest ascii equivilant,
    and brackets removed.

    Args:
        name: The original name to standardise.

    Returns:
        The name, standardised according to the above procedure.
    """
    new_name = ""
    # Normalise to Unicode Canonical Decomposition
    name = unicodedata.normalize("NFD", name)
    # Round trip encode to ascii and back to utf-8
    name = name.encode("ascii", "ignore").decode("utf-8")
    # Add space in between CamelCase words
    for n, char in enumerate(name):
        if n != 0:
            prev_char = name[n - 1]
            if char.isupper() and prev_char.islower():
                new_name += " "
        new_name += char
    # Strip leading and trailing whitespace and convert to lowercase
    new_name = new_name.strip().lower()
    # Replace any whitespace characters or forward slash with an underscore
    new_name = re.sub(r"[\s/]", "_", new_name)
    # Remove any brackets
    new_name = re.sub(r"[\(\)]", "", new_name)
    return new_name


def filter_df_columns(df: pd.DataFrame, columns: dict[str, str]) -> pd.DataFrame:
    """
    Filters a Pandas DataFrame to keep only the columns specified in a supplied
    dictionary, renaming the according to the value of that name in the
    dictionary.

    Args:
        df: The Pandas DataFrame to filter.
        columns: A dictionary of {old_name: new_name} key: value pairs,
            where old_name is the standardised name after it has been
            passed through `standardise_column_name`, and new_name is a string
            to rename the column to.

    Raises:
        ValueError: If any of the columns specified in the `columns` dict are
            not present in the supplied DataFrame `df`.

    Returns:
        A DataFrame containing only the desired columns.
    """
    df.columns = [standardise_column_name(col) for col in df.columns]
    missing_cols = columns.keys() - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing columns {missing_cols}")
    df = df[columns.keys()]
    df.columns = list(columns.values())
    return df


def strip_column_values(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Perform a string strip operation to remove leading and trailing whitespace
    from a supplied list of columns in a supplied Pandas DataFrame.

    Args:
        df: The Pandas DataFrame to perform the operations on.
        cols: The columns to perform the operation on.

    Returns:
        The supplied DataFrame with leading and trailing whitespace removed from
        the specified columns.
    """
    df[cols] = df[cols].apply(lambda col: col.str.strip())
    return df


def df_to_dict(df: pd.DataFrame | gpd.GeoDataFrame, key_column: str) -> dict[str, dict[str, Any]]:
    """
    Converts a DataFrame to a dictionary.

    The keys of the returned dictionary will be the values from the column in the
    DataFrame named `key_column`. The values of the returned dictionary will be
    a dictionary mapping column name to value for each row in the DataFrame.
    For example, a DataFrame like this:

    | col_1 | col_2 | col_3 |
    |-------|-------|-------|
    |   "a" |   1.0 | "foo" |
    |   "b" |   2.0 | "bar" |
    |   "c" |   3.0 | "baz" |

    Using col_1 as the `key_column`, would be turned into the following dictionary:

    {
        "a": {"col_2": 1.0, "col_3", "foo"},
        "b": {"col_2": 2.0, "col_3", "bar"},
        "c": {"col_2": 3.0, "col_3", "baz"}
    }

    Args:
        df: The DataFrame to convert to a dictionary.
        key_column: A column in the DataFrame which contains unique values,
            the values from which will be used as keys in the returned
            dictionary.

    Raises:
        ValueError: If the key_column in the supplied DataFrame contains
            duplicated values.

    Returns:
        A dictionary derived from the supplied DataFrame.
    """
    if not df[key_column].is_unique:
        raise ValueError(f"Cannot convert DataFrame to a dict, column {key_column} contains duplicated values")
    d = {}
    for row in df.itertuples():
        key = getattr(row, key_column)
        row_dict = row._asdict()
        del row_dict["Index"]
        del row_dict[key_column]
        d[key] = row_dict
    return d


def dict_to_df(d: dict[str, dict[str, Any]], key_column: str) -> pd.DataFrame:
    """
    Converts a dictionary of the format produced by `df_to_dict` to a DataFrame

    Args:
        d: The dictionary to convert.
        key_column: The name of the column which the keys of the supplied
            dictionary will be added to as values.

    Returns:
        A DataFrame derived from the supplied Dictionary.
    """
    return pd.DataFrame([{key_column: k, **v} for k, v in d.items()])


def gdf_concat(gdfs: list[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
    """
    Concatenates a list of GeoPandas GeoDataFrames. If the list contains a
    single item, it will be returned, else each GeoDataFrame in the list
    will be concatenated together.

    Args:
        gdfs: A list of GeoDataFrames to concatenate.

    Raises:
        ValueError: If an empty list was passed.

    Returns:
        A single GeoDataFrame.
    """
    match len(gdfs):
        case 0:
            raise ValueError("Received empty list")
        case 1:
            return gdfs[0]
        case _:
            return gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
