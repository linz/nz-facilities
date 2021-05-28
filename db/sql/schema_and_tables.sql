--Schema

CREATE SCHEMA IF NOT EXISTS facilities_lds;

COMMENT ON SCHEMA facilities_lds IS
'Schema that holds facilities data to publish on the LDS.';
-- Tables

-- nz facilities

-- The nz_facilities table holds a multipolygon geometry, originating from National Map facility polygons and authoritative source data
CREATE TABLE IF NOT EXISTS facilities_lds.nz_facilities (
      facility_id integer PRIMARY KEY
    , external_facility_id character varying(80) DEFAULT ''
    , name character varying(250) DEFAULT ''
    , external_name character varying(250) DEFAULT ''
    , use character varying(40) NOT NULL DEFAULT ''
    , use_type character varying(150) DEFAULT ''
    , use_subtype character varying(150) DEFAULT ''
    , estimated_occupancy integer DEFAULT 0
    , last_modified date
    , internal boolean NOT NULL DEFAULT false
    , internal_comments character varying(100) DEFAULT ''
    , shape public.geometry(MultiPolygon, 2193) NOT NULL
);

CREATE INDEX shx_nz_facilities
    ON facilities_lds.nz_facilities USING gist (shape);

COMMENT ON TABLE facilities_lds.nz_facilities IS
'The nz_facilities table holds geometries originating from National Map facility polygons '
'and authoritative source data.';
COMMENT ON COLUMN facilities_lds.nz_facilities.facility_id IS
'Unique identifier for each geometry.';
COMMENT ON COLUMN facilities_lds.nz_facilities.external_facility_id IS
'The unique identifier of this facility used by the authoritative source';
COMMENT ON COLUMN facilities_lds.nz_facilities.name IS
'The name of the facility.';
COMMENT ON COLUMN facilities_lds.nz_facilities.external_name IS
'The name of the facility used by the authoritative source.';
COMMENT ON COLUMN facilities_lds.nz_facilities.use IS
'The generic use of the facility.';
COMMENT ON COLUMN facilities_lds.nz_facilities.use_type IS
'Use type as defined by the authoritative source.';
COMMENT ON COLUMN facilities_lds.nz_facilities.use_subtype IS
'Use subtype as defined by the authoritative source.';
COMMENT ON COLUMN facilities_lds.nz_facilities.estimated_occupancy IS
'An approximation of the occupancy from the authoritative source. It may not include staff.';
COMMENT ON COLUMN facilities_lds.nz_facilities.last_modified IS
'The most recent date on which any attribute or geometry that is part of the facility was modified.';
COMMENT ON COLUMN facilities_lds.nz_facilities.internal IS
'Used to identify features which will not be added to the LDS, such as teen parenting units which are part of a school.';
COMMENT ON COLUMN facilities_lds.nz_facilities.internal_comments IS
'Used to internal information such as why being stored as internal only, when likely to open, where found information.';
COMMENT ON COLUMN facilities_lds.nz_facilities.shape IS
'The geometry of the feature.';
