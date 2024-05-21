from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely
from pandarallel import pandarallel

from facilities_change_detection.core.log import get_logger

TITLES_GDF = None
TITLE_DISTANCE_THRESHOLD = 50
TITLE_MERGE_MAX_ROUNDS = 20


logger = get_logger()


def find_matching_parcels(row: pd.Series) -> shapely.geometry.MultiPolygon | None:
    """
    Creates a polygon for a point feature by finding which parcels from the
    "Titles with Owners" dataset the point intersects with, then adding nearby
    parcels owned by the same owners incrementally.

    If the input geometry is null, or there are no intersecting parcels,
    we return None.

    Before applying this function to the input GeoDataFrame, the Titles with
    Owners file must be read and assigned to the TITLES_GDF global.
    [See `find_points_in_titles_with_owner`]

    Args:
        row: A row of a GeoDataFrame containing Point geometries.

    Raises:
        ValueError: If the Titles with Owners file has not been read into the
            TITLES_GDF global.

    Returns:
        Matched polygon geometry or None
    """
    # Raise an exception if the titles file hasn't been loaded
    if TITLES_GDF is None:
        raise ValueError("Global TITLES_GDF has not been set")
    # Return None for null geometries
    if row.geometry is None:
        return None
    # Query the spatial index to find parcels whose
    # bounding boxes intersect the point
    rough_matching_parcels = TITLES_GDF.loc[TITLES_GDF.sindex.query(row.geometry)]
    # Return None if there were no matches
    if len(rough_matching_parcels) == 0:
        return None
    # Refine the rough matches to actual geometry intersections
    matching_parcels = rough_matching_parcels[rough_matching_parcels.intersects(row.geometry)]
    # Return None if there were no matches
    if len(matching_parcels) == 0:
        return None
    # Build a set of all unique owners for all the matched parcels
    all_owners = set(matching_parcels["owners"])
    # Remove None from set if present
    try:
        all_owners.remove(None)
    except KeyError:
        pass
    # Union all matching parcels together
    geom = shapely.union_all(matching_parcels.geometry)
    # Track how many times we've looped
    rounds = 1
    # Track which parcels we've merged into our geom
    merged_ids = set()
    # Find parcels with the same owner as those we unioned together
    parcels_with_same_owner = TITLES_GDF[
        TITLES_GDF["owners"].isin(all_owners) & ~TITLES_GDF["id"].isin(matching_parcels["id"])
    ]
    # Start loop
    while True:
        # Find all parcels with the same owner, within the distance threshold,
        # which we haven't already merged into our geom
        nearby_parcels_with_same_owner = parcels_with_same_owner[
            ~parcels_with_same_owner["id"].isin(merged_ids)
            & (parcels_with_same_owner.geometry.distance(geom) < TITLE_DISTANCE_THRESHOLD)
        ]
        # Update the set of parcels we have merged
        merged_ids.update(nearby_parcels_with_same_owner["id"])
        # Break out of the loop if there are no nearby parcels with the same
        # owner we haven't already merged, or we'vew reached the maximum number
        # of rounds through the loop
        if len(nearby_parcels_with_same_owner) == 0 or rounds >= TITLE_MERGE_MAX_ROUNDS:
            break
        # Merge any nearby parcels with the same owner into our geom
        geom = shapely.union_all([geom, *nearby_parcels_with_same_owner.geometry])
        rounds += 1
    # Return the geom
    return geom


def find_points_in_titles_with_owners(gdf: gpd.GeoDataFrame, titles_file: Path) -> gpd.GeoDataFrame:
    """
    Replaces the geometry of the supplied GeoDataFrame with a polygon created by
    the `find_matching_parcels` function.

    Args:
        gdf: GeoDataFrame with point geometries.
        titles_file: Path to the Titles with Owners file.

    Returns:
        The supplied GeoDataFrame with its geometry updated.
    """
    global TITLES_GDF
    logger.info(f"Reading Titles with Owners file from {titles_file}")
    TITLES_GDF = gpd.read_file(titles_file, engine="pyogrio", use_arrow=True)
    TITLES_GDF.sindex
    pandarallel.initialize(progress_bar=True, verbose=0)
    logger.info("Finding polygon for each input point")
    gdf["geometry"] = gdf.parallel_apply(find_matching_parcels, axis=1)
    return gdf
