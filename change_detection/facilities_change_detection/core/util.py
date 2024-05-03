import re
import unicodedata

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
