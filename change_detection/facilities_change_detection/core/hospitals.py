import re
from pathlib import Path
from urllib.parse import urljoin

import geopandas as gpd
import lxml.html
import openpyxl
import pandas as pd
import requests

from facilities_change_detection.core.io import download_file
from facilities_change_detection.core.log import get_logger
from facilities_change_detection.core.util import filter_df_columns, strip_column_values

logger = get_logger()

HPI_EXCEL_PAGE_URL = "https://www.tewhatuora.govt.nz/for-health-professionals/data-and-statistics/nz-health-statistics/data-references/code-tables/common-code-tables/"
HPI_COLUMNS_OF_INTEREST = {
    "name": "name",
    "hpi_facility_id": "hpi_facility_id",
    "address": "address",
    "facility_type_name": "type",
    "hpi_organisation_id": "hpi_organisation_id",
    "organisation_legal_name": "organisation_name",
    "nzgd2k_x": "x",
    "nzgd2k_y": "y",
}


def download_hpi_excel(output_folder: Path, overwrite: bool) -> Path:
    """
    Downloads the latest HPI Facilities Code Table Excel file from the
    Te Whatu Ora website. The file will be saved with a name in the format
    `hpi__{year}-{month}-{day}.xlsx`, where the date is parsed from the
    date last updated given in the filename.

    This function depends on being able to parse the download link from the
    HTML of the Te Whatu Ora website, as the URL of the file to download is not
    static over time. If the markup of the Te Whatu Ora website changes, this
    function will likely cease to work.

    Args:
        output_folder: folder to save the file into.
        overwrite: whether to overwrite an existing file with the same name
            in the specified output folder.

    Raises:
        ValueError: if the download link was unable to be parsed from the HTML,
            if the date was unable to be parsed from the URL, or a file with
            the same name already exists in the specified output folder and
            `overwrite` is not True.
        requests.RequestException [or child Exceptions]: if any network issues
            occur.

    Returns:
        The path where the file was saved.
    """
    # Download the landing page and raise exception for any errors
    print(logger.getEffectiveLevel())
    logger.info("Downloading HTML of landing page")
    r = requests.get(HPI_EXCEL_PAGE_URL)
    r.raise_for_status()
    # Parse HTML of landing page
    tree = lxml.html.fromstring(r.content)
    # Find all <a> elements with a class of "download__link" who are descendents
    # of a <div? element whose id value starts with "facility-code-table"
    els = tree.xpath('//div[starts-with(@id,"facility-code-table")]//a[@class="download__link"]')
    # If there isn't a single element, raise an exception
    if len(els) != 1:
        raise ValueError(f"Found {len(els)} matching download link xpath selector, expected 1")
    logger.info("Parsed download link from landing page")
    # Extract href attribute from <a> element and resolve full download URL
    href = els[0].attrib["href"]
    download_url = urljoin(HPI_EXCEL_PAGE_URL, href)
    # Extract date from filename and build standardised output filename
    download_filename = href.split("/")[-1]
    if name_match := re.match(r"Facilities(\d{4})(\d{2})(\d{2})", download_filename):
        year, month, day = name_match.groups()
        output_file = output_folder / f"hpi__{year}-{month}-{day}.xlsx"
    else:
        raise ValueError(f"Cannot parse date from filename {download_filename}")
    # Download the file to the output file, and return the path
    if overwrite is False and output_file.exists():
        raise ValueError(f"{output_file} already exists. To overwrite, rerun with --overwrite.")
    return download_file(download_url, output_file)


def standardise_hpi_type(col: pd.Series) -> pd.Series:
    """
    Standardises values in the "type" column of the HPI data by performing
    a series of replacement operations on the column.

    Args:
        col: The "type" column from an HPI DataFrame.

    Returns:
        The supplied "type" column with values standardised.
    """
    ops = [
        # Add space before and after forward slashes
        (r"(?<=\S)\/", " /", True),
        (r"\/(?=\S)", "/ ", True),
        # Replace en dash with hyphenminus. This would be better to use the
        # unicode character class \p{Dash_Punctuation}, but pandas uses the
        # builtin Python regex engine with doesn't support this, and given there
        # only seems to be an en dash in some older HPI Excel files, it seems
        # better just to search for that and still use pandas than have to drop
        # down to using the regex 3rd party library which doesn support unicode
        # character classes.
        ("–", "-", False),
        # All the others seem to be in the form of "thing - suffix", apart from
        # this one in the form "thing (suffix)"
        (" (not otherwise specified)$", "- not otherwise specified", True),
    ]
    for pattern, replacement, regex in ops:
        col = col.str.replace(pattern, replacement, regex=regex)
    return col


def load_hpi_excel(input_file: Path) -> gpd.GeoDataFrame:
    """
    Loads an HPI Excel file to a GeoPandas GeoDataFrame.

    To standardise the data, we perform the following actions:
    - Filter the dataset to contain only columns of interest, defined in
      `HPI_COLUMNS_OF_INTEREST`.
    - Strip leading and trailing whitespace from columns where this may be
      present.
    - Strip a trailing comma if present from the "address" column values.
    - Standarise values in the type column according to the operations described
      in the `standardise_hpi_type` function.
    - Convert the initial Pandas DataFrame to a GeoPandas GeoDataFrame using
      coordinates in the "x" and "y" columns, which are then dropped.

    Args:
        input_file: A path to an HPI Excel file.

    Returns:
        A GeoPandas GeoDataFrame of the HPI data from the supplied Excel file.
    """
    # Older versions of the file had the data in the first sheet, whereas
    # newer versions have the data in a second sheet named "Facilities".
    # To detect this we first open the file to see if it has a sheet named
    # "Facilities", and if so pass that to `pd.read_excel()`.
    wb = openpyxl.load_workbook(input_file, read_only=True)
    sheet_name = "Facilities" if "Facilities" in wb.sheetnames else 0
    wb.close()
    # Load the file using Pandas
    df = pd.read_excel(input_file, sheet_name=sheet_name)
    # Filter to just the columns we're interested in
    df = filter_df_columns(df, HPI_COLUMNS_OF_INTEREST)
    # Strip leading and trailing whitespace from these columns
    df = strip_column_values(df, ["name", "address", "type", "organisation_name"])
    # Strip a trailing comma from some address columns - this was present in
    # many rows in old data, so removing it helps remove false positives when
    # comparing that old data to new data
    df["address"] = df["address"].str.rstrip(",")
    df["type"] = standardise_hpi_type(df["type"])
    # Convert the Pandas DataFrame to a Geopandas GeoDataFrame
    gdf = gpd.GeoDataFrame(data=df, geometry=gpd.points_from_xy(df.x, df.y), crs=4167)
    gdf.drop(columns=["x", "y"], inplace=True)
    return gdf


def update_midwife_likelihood(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Updates the likelihood for features of type "Community Midwife".

    There are a large number of these, which generally represent individual
    midwifes. However some features of this type represent birthing centres
    which function like a maternity ward of a hospital, for women to give birth
    and be cared for in the following days, which we do want to capture.

    To try and target these, we increase the likelihood of any features of type
    "Community Midwife" which have either "birth" or "maternity" in their name.

    Args:
        gdf: An HPI GeoDataFrame.

    Returns:
        The supplied HPI GeoDataFrame with midwife likelihoods updated in place.
    """
    gdf.loc[
        (gdf["type"] == "Community Midwife")
        & (
            (gdf["name"].str.contains("birth", case=False, regex=False))
            | (gdf["name"].str.contains("maternity", case=False, regex=False))
        ),
        "likelihood",
    ] = 4
    return gdf


def assign_hpi_likelihood(gdf: gpd.GeoDataFrame, likelihood_file: Path):
    """
    Adds a column "likelihood" to the supplied GeoDataFrame, representing how
    likely it is that we would want to add a given feature to the Facilities
    dataset. Likelihood is a scale from 1-5, with the following meaning:

    5: Very likely
    4: Likely
    3: Maybe
    2: Unlikely
    1: Very unlikely

    Initial likelihoods are assigned to all features in a given HPI "type",
    based on values read in from the supplied likelihood CSV file. Likelihoods
    are further dynamically updated from there, before the supplied GeoDataFrame
    is returned with the added column updated to the appropriate value for all
    features.

    Args:
        gdf: A GeoDataFrame of the HPI data, from `load_hpi_excel`.
        likelihood_file: A path to a likelihood CSV file, with columns "type"
            representing each type present in the HPI data, and "likelihood"
            containing the initial likelihood to assign to features of that type.

    Returns:
        The supplied GeoDataFrame with an added likelihood column.
    """
    likelihood_df = pd.read_csv(likelihood_file)
    gdf = gdf.merge(likelihood_df, on="type", how="left")
    for func in [update_midwife_likelihood]:
        gdf = func(gdf)
    return gdf
