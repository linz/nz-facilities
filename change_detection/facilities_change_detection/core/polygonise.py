from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import shapely
from pandarallel import pandarallel

from facilities_change_detection.core.log import get_logger

TITLES_GDF = None
TITLE_MERGE_MAX_ROUNDS = 20


logger = get_logger()


def standardise_corporate_name(s: pd.Series) -> pd.Series:
    """
    Standardise corporate names.

    Each step to be applied is explained via in-line comments above it.

    Args:
        s: A Series of corporate names.

    Returns:
        The input series with values standardised.
    """
    # Normalise unicode characters
    s = s.str.normalize("NFD")
    # Encode to ASCII and ignore errors:
    # converts non-ASCII characters to closest ASCII equivilant
    s = s.str.encode("ascii", errors="ignore")
    # Convert back to string type
    s = s.astype("string[pyarrow]")
    # Lowercase
    s = s.str.lower()
    for pattern, replacement, regex in [
        # Replace Quotes, comma, hash, dots, and brackets with a space
        (r"[',+#\"\.\(\)\[\]]", " ", True),
        # Replace more than one space with a single space
        (r" +", " ", True),
        # Replace ampersand with and
        (r" ?& ?", " and ", True),
        # Replace en dash with hyphenminus
        ("–", "-", False),
        # Replace hyphen with optional leading or trailing space with
        # single space
        (r" ?- ?", " ", True),
        # Replace `no1` with `no 1`
        (r"no ?(\d)", r"no \1", True),
        # Spell limited in full
        (r" ltd(?:$| )", " limited ", True),
        # Spell incorporated in full
        (r" inc(?:$| )", " incorporated ", True),
        # Spell company in full
        (r" co(?:$| )", " company ", True),
        # Spell road abbreviated
        (r" road(?:$| )", " rd ", True),
        # Spell street abbreviated
        (r" street(?:$| )", " st ", True),
        # Spell avenue abbreviated
        (r" avenue(?:$| )", " ave ", True),
        # Replace `abc123` with `abc123`
        (r"([a-z])(\d)", r"\1 \2", True),
        # Replace `123abc` with `123 abc`
        (r"(\d)([a-z])", r"\1 \2", True),
    ]:
        s = s.str.replace(pattern, replacement, regex=regex)
    # Strip leading and trailing whitespace
    s = s.str.strip()
    return s


def standardise_individual_name(s: pd.Series) -> pd.Series:
    """
    Standardise individual names.

    Each step to be applied is explained via in-line comments above it.

    Args:
        s: A Series of individual names.

    Returns:
        The input series with values standardised.
    """
    # Normalise unicode characters
    s = s.str.normalize("NFD")
    # Encode to ASCII and ignore errors:
    # converts non-ASCII characters to closest ASCII equivilant
    s = s.str.encode("ascii", errors="ignore")
    # Convert back to string type
    s = s.astype("string[pyarrow]")
    # Lowercase
    s = s.str.lower()
    # Strip leading and trailing whitespace
    s = s.str.strip()
    return s


def build_titles_with_owners(titles_file: Path, owners_file: Path, should_standardise_names: bool) -> gpd.GeoDataFrame:
    """
    Combines the NZ Property Titles spatial dataset from LDS with the
    NZ Property Titles Owners List non-spatial table from LDS to add title
    owners to title geometries.

    We use these two input files rather than the NZ Property Titles Including
    Owners dataset from LDS as the NZ Property Titles Owners List separates out
    indivdual owners (i.e. natual persons) from corporate owners (i.e. trusts,
    companies, government entities, etc).

    This is helpful as it allows us to more easily apply different
    standardisation to these different types of owner names.

    The standardisation we apply removes a number of common inconsistencies
    and spelling differences between different owners which exist in the
    ownership records, which prevent direct string comparison. Standardising
    in this way is a middle-road between exact comparison of the name with no
    changes (simple, but will fail on minor typos such as "St George's Hospital
    Incorporated" vs "St. George's Hospital Incorporated") and fuzzy string
    matching (using a library such as RapidFuzz), which adds ambiguity
    (requiring specifying a threshold of similarity) and much greater
    computation required.

    Args:
        titles_file: Path to the NZ Property Titles GeoPackage exported from LDS.
        owners_file: Path to the NZ Property Titles Owners List CSV exported from LDS.
        should_standardise_names: Whether we should add an additional column
            "standardised_owner_name" to the returned DataFrame with
            standardised names.

    Returns:
        A GeoDataFrame of titles merged with owners.
    """
    # Load NZ Property Titles dataset
    logger.info(f"Loading NZ Property Titles from {titles_file}")
    titles_gdf = gpd.read_file(titles_file, columns=["id", "title_no"], engine="pyogrio", use_arrow=True)
    titles_gdf = titles_gdf.to_crs(2193)
    # Load NZ Property Titles Owners List dataset
    logger.info(f"Loading NZ Property Titles Owners List from {owners_file}")
    owners_df = pd.read_csv(
        owners_file,
        engine="pyarrow",
        dtype_backend="pyarrow",
        usecols=[
            "title_no",
            "estate_share",
            "owner_type",
            "prime_surname",
            "prime_other_names",
            "corporate_name",
            "name_suffix",
        ],
    )
    # Combine individual name parts into a single string, and assign it to a new
    # singular "owner_name" column where present, or the corporate name if not
    logger.info("Building individual owner names")
    owners_df.fillna({col: "" for col in ["prime_other_names", "prime_surname", "name_suffix"]}, inplace=True)
    individual_name = owners_df["prime_other_names"] + " " + owners_df["prime_surname"] + " " + owners_df["name_suffix"]
    individual_name = individual_name.str.strip()
    individual_name = individual_name.replace("", pa.NA)
    owners_df["owner_name"] = np.where(individual_name.isna(), owners_df["corporate_name"], individual_name)
    owners_df["owner_name"] = owners_df["owner_name"].astype("string[pyarrow]")
    if should_standardise_names is True:
        # Add a "standardised_owner_name" column to increase likelihood that names
        # from similar owners with typos etc will be detected as being the same
        logger.info("Standardising owner names")
        owners_df["standardised_owner_name"] = np.where(
            individual_name.isna(),
            standardise_corporate_name(owners_df["corporate_name"]),
            standardise_individual_name(individual_name),
        )
        owners_df["standardised_owner_name"] = owners_df["standardised_owner_name"].astype("string[pyarrow]")
    # Drop unneeded columns
    owners_df.drop(columns=["prime_other_names", "prime_surname", "name_suffix", "corporate_name"], inplace=True)
    # Merge owners dataset to titles dataset on title_no
    logger.info("Merging owner names to title geometries")
    merged_gdf = titles_gdf.merge(owners_df, on="title_no", how="left")
    return merged_gdf


def find_matching_titles(row: pd.Series, use_standardised_names: bool, distance_threshold: int) -> pd.Series:
    """
    Creates a polygon for a point feature by finding which title geometries the
    point intersects with, then adding nearby titles owned by the same owners
    incrementally.

    We initially find all polygons the input point intersects with, and create
    an initial new polygon geometry which is the union of these. We then create
    a set of the owners of each of those polygons, and find any other polygons
    within the supplied threshold distance (in metres) which are owner by any
    owners from our initial set of owners, and union those polygons with our
    new polygon. We then continue this step, up to a limit set by the global
    variable TITLE_MERGE_MAX_ROUNDS, incrementally continuing outwards adding
    any polygons within the threshold distance of our new polygon which are
    which have an owner in our initial set of owners. We do not add any new
    owners to our owners set over time: we only use the owners from the initial
    intersecting titles for each round of incrementally adding nearby titles.

    If the input geometry is null, or there are no intersecting titles,
    we return None.

    This function is intended to be passed to the `apply` method of a DataFrame,
    rather than called directly.

    Before applying this function, the titles GeoDataFrame (as created by the
    `build_titles_with_owners` function) must be assigned to the TITLES_GDF
    global variable, which is done by the function
    `find_points_in_titles_with_owner`.

    Args:
        row: A row of a GeoDataFrame containing Point geometries.
        use_standardised_names: If True, the combining of nearby owners will
            use values from the "standardised_owner_name" column of TITLES_GDF,
            otherwise it will use the "owner_name" column.
        distance_threshold: how far away nearby titles can be from the starting
            title before they are no longer combined, in metres. I.e. a value
            of 10 will combine all titles with the same owners within 10m.

    Raises:
        ValueError: If the Titles with Owners file has not been read into the
            TITLES_GDF global.

    Returns:
        A Pandas Series with 3 values (which, if this function is called as
        intended via df.apply(), will become a DataFrame with 3 columns for all
        results together). The first column is the polygon geometry we have
        found, the second is a string value of all the owner names joined with
        commas, and the third is a count of the number of owner names. If the
        input geometry is null, or the input geometry does not intersect with
        any titles, we return None for the first geometry column and pd.NA for
        the second and third columns.
    """
    # Raise an exception if the titles file hasn't been loaded
    if TITLES_GDF is None:
        raise ValueError("Global TITLES_GDF has not been set")
    if use_standardised_names is True:
        owner_column = "standardised_owner_name"
    else:
        owner_column = "owner_name"
    none_return_value = pd.Series([None, pd.NA, pd.NA])
    # Return early for null geometries
    if row.geometry is None:
        return none_return_value
    # Query the spatial index to find titles whose bounding boxes intersect the point
    rough_matching_titles = TITLES_GDF.loc[TITLES_GDF.sindex.query(row.geometry)]
    # Return early if there were no matches
    if len(rough_matching_titles) == 0:
        return none_return_value
    # Refine the rough matches to actual geometry intersections
    matching_titles = rough_matching_titles[rough_matching_titles.intersects(row.geometry)]
    # Return early if there were no matches
    if len(matching_titles) == 0:
        return none_return_value
    # Build a set of all unique owners for all the matched titles
    all_owners = set(matching_titles[owner_column])
    # Remove None and NA from set if present
    try:
        all_owners.remove(pd.NA)
    except KeyError:
        pass
    # Union all matching titles together
    geom = shapely.union_all(matching_titles.geometry)
    # Track how many times we've looped
    rounds = 1
    # Track which titles we've merged into our geom
    merged_ids = set()
    # Find titles with the same owner as those we unioned together
    titles_with_same_owner = TITLES_GDF[
        TITLES_GDF[owner_column].isin(all_owners) & ~TITLES_GDF["id"].isin(matching_titles["id"])
    ]
    # Start loop
    while True:
        # Find all titles with the same owner, within the distance threshold,
        # which we haven't already merged into our geom
        nearby_titles_with_same_owner = titles_with_same_owner[
            ~titles_with_same_owner["id"].isin(merged_ids)
            & (titles_with_same_owner.geometry.distance(geom) <= distance_threshold)
        ]
        # Update the set of titles we have merged
        merged_ids.update(nearby_titles_with_same_owner["id"])
        # Break out of the loop if there are no nearby titles with the same
        # owner we haven't already merged, or we'vew reached the maximum number
        # of rounds through the loop
        if len(nearby_titles_with_same_owner) == 0 or rounds >= TITLE_MERGE_MAX_ROUNDS:
            break
        # Merge any nearby titles with the same owner into our geom
        geom = shapely.union_all([geom, *nearby_titles_with_same_owner.geometry])
        rounds += 1
    # Return the geom
    return pd.Series([geom, ", ".join(sorted(all_owners)), len(all_owners)])


def find_points_in_titles_with_owners(
    input_gdf: gpd.GeoDataFrame, titles_gdf: gpd.GeoDataFrame, use_standardised_names: bool, distance_threshold: int
) -> gpd.GeoDataFrame:
    """
    Replaces the geometry of the supplied GeoDataFrame with a polygon created by
    the `find_matching_titles` function.

    Args:
        input_gdf: GeoDataFrame with point geometries.
        titles_file: Path to the Titles with Owners file.
        use_standardised_names: If True, the combining of nearby owners will
            use values from the "standardised_owner_name" column of TITLES_GDF,
            otherwise it will use the "owner_name" column.
        distance_threshold: how far away nearby titles can be from the starting
            title before they are no longer combined, in metres. I.e. a value
            of 10 will combine all titles with the same owners within 10m.

    Returns:
        The supplied GeoDataFrame with its geometry updated.
    """
    global TITLES_GDF
    TITLES_GDF = titles_gdf
    TITLES_GDF.sindex
    pandarallel.initialize(progress_bar=True, verbose=0)
    logger.info("Finding polygon for each input point")
    matching_titles_df = input_gdf.parallel_apply(
        find_matching_titles, axis=1, use_standardised_names=use_standardised_names, distance_threshold=distance_threshold
    )
    input_gdf["geometry"] = gpd.GeoSeries(matching_titles_df[0])
    input_gdf["owner_names"] = matching_titles_df[1]
    input_gdf["owner_count"] = matching_titles_df[2]
    return input_gdf
