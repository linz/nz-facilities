--Schema

CREATE SCHEMA IF NOT EXISTS facilities_lds;

COMMENT ON SCHEMA facilities_lds IS
'Schema that holds facilities data to publish on the LDS.';
-- Tables

-- nz_facilities

-- The nz_facilities table holds a copy of the facilities.facilities table
-- minus the internal and internal_comments fields.

CREATE TABLE IF NOT EXISTS facilities_lds.nz_facilities as
SELECT
      facility_id
    , external_facility_id
    , name
    , external_name
    , use
    , use_type
    , use_subtype
    , estimated_occupancy
    , last_modified
    , shape
FROM facilities.facilities
WHERE internal IS NULL;

CREATE INDEX shx_nz_facilities
ON facilities_lds.nz_facilities USING gist (shape);
