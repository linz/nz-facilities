--Schema

CREATE SCHEMA IF NOT EXISTS facilities;

COMMENT ON SCHEMA facilities IS
'Schema that holds facilities data.';
-- Tables

-- facilities

-- The facilities table holds a multipolygon geometry, originating from the authoritative source data
CREATE TABLE IF NOT EXISTS facilities.facilities (
      facility_id serial PRIMARY KEY
    , external_facility_id character varying(80) DEFAULT ''
    , name character varying(250) DEFAULT ''
    , external_name character varying(250) DEFAULT ''
    , use character varying(40) NOT NULL DEFAULT ''
    , use_type character varying(150) DEFAULT ''
    , use_subtype character varying(150) DEFAULT ''
    , estimated_occupancy integer DEFAULT 0
    , last_modified date DEFAULT ('now'::text)::date
    , internal boolean NOT NULL DEFAULT false
    , internal_comments character varying(250) DEFAULT ''
    , shape public.geometry(MultiPolygon, 2193) NOT NULL
);

CREATE INDEX shx_facilities
    ON facilities.facilities USING gist (shape);

COMMENT ON TABLE facilities.facilities IS
'The facilities table holds geometries originating from authoritative source data.';
COMMENT ON COLUMN facilities.facilities.facility_id IS
'The unique identifier for each geometry.';
COMMENT ON COLUMN facilities.facilities.external_facility_id IS
'The unique identifier of this facility used by the authoritative source';
COMMENT ON COLUMN facilities.facilities.name IS
'The name of the facility.';
COMMENT ON COLUMN facilities.facilities.external_name IS
'The name of the facility used by the authoritative source.';
COMMENT ON COLUMN facilities.facilities.use IS
'The generic use of the facility.';
COMMENT ON COLUMN facilities.facilities.use_type IS
'Use type as defined by the authoritative source.';
COMMENT ON COLUMN facilities.facilities.use_subtype IS
'Use subtype as defined by the authoritative source.';
COMMENT ON COLUMN facilities.facilities.estimated_occupancy IS
'An approximation of the occupancy from the authoritative source. It may not include staff.';
COMMENT ON COLUMN facilities.facilities.last_modified IS
'The most recent date on which any attribute or geometry that is part of the facility was modified.';
COMMENT ON COLUMN facilities.facilities.internal IS
'Identifies features which will not be added to the LDS.';
COMMENT ON COLUMN facilities.facilities.internal_comments IS
'Internal information such as why being stored as internal only, when likely to open, where found information.';
COMMENT ON COLUMN facilities.facilities.shape IS
'The geometry of the facility represented as a MultiPolygon using NZTM2000 / EPSG 2193.';
