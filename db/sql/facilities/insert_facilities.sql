CREATE SCHEMA IF NOT EXISTS temp_facilities;

-- manually add gpkg into the database
-- copy from gpkg table into the internal facilities table

INSERT INTO facilities.facilities(
      external_facility_id
    , name
    , external_name
    , use
    , use_type
    , use_subtype
    , estimated_occupancy
    , internal
    , internal_comments
    , shape
    )
SELECT
      external_facility_id
    , name
    , external_name
    , use
    , use_type
    , use_subtype
    , estimated_occupancy
    , internal
    , internal_comments
    , shape
FROM temp_facilities.temp_facilities;
