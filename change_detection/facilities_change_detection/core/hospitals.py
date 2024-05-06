import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import geopandas as gpd
import lxml.html
import openpyxl
import pandas as pd
import requests

from facilities_change_detection.core.facilities import DISTANCE_THRESHOLD, ChangeAction
from facilities_change_detection.core.io import download_file
from facilities_change_detection.core.log import get_logger
from facilities_change_detection.core.util import df_to_dict, dict_to_df, filter_df_columns, strip_column_values

logger = get_logger()

# The URL of the page which links to the HPI Excel files
HPI_EXCEL_PAGE_URL = (
    "https://www.tewhatuora.govt.nz/"
    "for-health-professionals/data-and-statistics/nz-health-statistics/"
    "data-references/code-tables/common-code-tables/"
)
# Columns to read from an HPI Excel file. The keys are the column names
# following standardisation using util.standardise_column_name, and the values
# are what the column will be renamed to.
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
# Columns to compare for changes when comparing NZ Facilities data to HPI data.
# Keys are column names in NZ Facilities, with values of column names to compare
# against in the HPI data.
FACILITIES_HPI_COMPARISON_COLUMNS = {"name": "name", "use_subtype": "type"}


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
    # of a <div> element whose id value starts with "facility-code-table"
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
        (r" \(not otherwise specified\)$", " - not otherwise specified", True),
    ]
    for pattern, replacement, regex in ops:
        col = col.str.replace(pattern, replacement, regex=regex)
    return col


def get_hpi_ids_to_ignore(ignore_file: Path) -> set[str]:
    """
    Loads a CSV of HPI ids to ignore. The CSV must have a column named
    "hpi_facility_id". Other columns can be present but are ignore by
    this function.

    Args:
        ignore_file: Path to the CSV file to read.

    Returns:
        Set of the ids to ignore.
    """
    df = pd.read_csv(ignore_file, usecols=["hpi_facility_id"])
    return set(df["hpi_facility_id"])


def load_hpi_excel(input_file: Path, ignore_file: Path | None = None) -> gpd.GeoDataFrame:
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
    - Reproject the GeoDataFrame to NZTM.

    If a path to an ignore file is passed, any features with an hpi_facility_id
    which appears in the ignore file will be filtered out.

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
    # If an ignore file was supplied,
    # load the IDS from that file and filter them out.
    if ignore_file is not None:
        ids_to_ignore = get_hpi_ids_to_ignore(ignore_file)
        df = df[~df["hpi_facility_id"].isin(ids_to_ignore)]
    # Strip a trailing comma from some address columns - this was present in
    # many rows in old data, so removing it helps remove false positives when
    # comparing that old data to new data
    df["address"] = df["address"].str.rstrip(",")
    df["type"] = standardise_hpi_type(df["type"])
    # Convert the Pandas DataFrame to a Geopandas GeoDataFrame
    gdf = gpd.GeoDataFrame(data=df, geometry=gpd.points_from_xy(df.x, df.y), crs=4167)
    gdf = gdf.to_crs(2193)
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


def compare_facilities_gdf_to_hpi_gdf(
    facilities_gdf: gpd.GeoDataFrame, hpi_gdf: gpd.GeoDataFrame
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Compares GeoDataFrames of hospitals from NZ Facilities data with HPI data.

    Args:
        facilities_gdf: GeoDataFrame of Hospitals in Facilities data, from
            `read_hospital_facilities`.
        hpi_gdf: GeoDataFrame of HPI data, from `load_hpi_excel`.

    Returns:
        Three GeoDataFrames:
        1. `updated_facilities_gdf`: the supplied `facilities_gdf` with added
           columns `change_action` and `change_description` describing whether
           a feature needs to be updated or removed.
        2. `hpi_new_gdf`: features from the HPI data not present in the
           Facilities data.
        3. `hpi_matched_gdf`: features from the HPI data which were present in
           the Falities data.
    """
    # Initialise these two columns with None
    facilities_gdf["change_action"] = None
    facilities_gdf["change_description"] = None
    # Convert the two GeoDataFrames to dictionarys
    facilities_dict = df_to_dict(facilities_gdf, "source_facility_id")
    hpi_dict = df_to_dict(hpi_gdf, "hpi_facility_id")
    # Initialise dicts to track HPI features which are new or which match
    # features in `facilities_gdf`
    new: dict[str, dict[str, Any]] = {}
    matched: dict[str, dict[str, Any]] = {}
    # Iterate through features from the HPI data
    for hpi_facility_id, hpi_attrs in hpi_dict.items():
        facilities_attrs = facilities_dict.get(hpi_facility_id)
        # If hpi_facility_id was not in the facilities dict,
        # add the feature to the new dict
        if facilities_attrs is None:
            new[hpi_facility_id] = hpi_attrs
        else:
            # Add the HPI feature to the matched dict
            matched[hpi_facility_id] = hpi_attrs
            # Get the geometries for the two features
            hpi_geom = hpi_attrs["geometry"]
            facilities_geom = facilities_attrs["geometry"]
            # Calculate the distance between the two. If `hpi_geom` is missing,
            # set the distance to be None.
            distance = facilities_geom.distance(hpi_geom) if hpi_geom else None
            # If the distance was None, update the change action and description
            # to say the geometry was missing.
            if distance is None:
                facilities_attrs["change_action"] = ChangeAction.UPDATE_GEOM
                facilities_attrs["change_description"] = "Geom: missing"
            # If the distance is greater than the threshold,
            # update the change action and description.
            elif distance > DISTANCE_THRESHOLD:
                facilities_attrs["change_action"] = ChangeAction.UPDATE_GEOM
                facilities_attrs["change_description"] = f"Geom: {distance:.1f}m"
            # Loop through the columns to compare, and if they are different,
            # add the old and new values to the changes.
            attr_changes: dict[str, tuple[str, str]] = {}
            for facilities_col, hpi_col in FACILITIES_HPI_COMPARISON_COLUMNS.items():
                if facilities_attrs[facilities_col] != hpi_attrs[hpi_col]:
                    attr_changes[facilities_col] = (facilities_attrs[facilities_col], hpi_attrs[hpi_col])
                    facilities_attrs[f"hpi_{hpi_col}"] = hpi_attrs[hpi_col]
            # If there were any changes to attributes in the columns we compared,
            # update the change action and description.
            if attr_changes:
                description = ";  ".join([f'{field}: "{old}" -> "{new}"' for field, (old, new) in attr_changes.items()])
                if facilities_attrs["change_action"] == ChangeAction.UPDATE_GEOM:
                    facilities_attrs["change_action"] = ChangeAction.UPDATE_GEOM_ATTR
                    facilities_attrs["change_description"] += f";  {description}"
                else:
                    facilities_attrs["change_action"] = ChangeAction.UPDATE_ATTR
                    facilities_attrs["change_description"] = description
    # Iterate through features from the Facilities data
    for source_facility_id, facilities_attrs in facilities_dict.items():
        # If any source_facility_id is not present in the HPI data,
        # mark it to be removed.
        if source_facility_id not in hpi_dict:
            facilities_attrs["change_action"] = ChangeAction.REMOVE
    # Convert the dictionaries back to GeoDataFrames
    updated_facilities_gdf = gpd.GeoDataFrame(dict_to_df(facilities_dict, "source_facility_id"), geometry="geometry", crs=2193)
    hpi_new_gdf = gpd.GeoDataFrame(dict_to_df(new, "hpi_facility_id"), geometry="geometry", crs=2193)
    hpi_matched_gdf = gpd.GeoDataFrame(dict_to_df(matched, "hpi_facility_id"), geometry="geometry", crs=2193)
    return updated_facilities_gdf, hpi_new_gdf, hpi_matched_gdf


def read_hospital_facilities(input_file: Path) -> gpd.GeoDataFrame:
    """
    Reads an input Facilities GeoPackage, and returns a GeoDataFrame of
    its contents, filtered to only include Hospital features.

    Args:
        input_file: The Path to the NZ Facilities GeoPackage

    Returns:
        A GeoDataFrame of Hospital features.
    """
    facilities_gdf = gpd.read_file(input_file)
    facilities_gdf = facilities_gdf[facilities_gdf["use"] == "Hospital"]
    return facilities_gdf
