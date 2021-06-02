--Schema

CREATE SCHEMA IF NOT EXISTS facilities_lds;

COMMENT ON SCHEMA facilities_lds IS
'Schema that holds facilities data to publish on the LDS.';
-- Tables

-- nz_facilities

-- The nz_facilities table holds a copy of the facilities.facilities table
-- minus the internal and internal_comments fields.

DROP TABLE IF EXISTS facilities_lds.nz_facilities;

CREATE TABLE IF NOT EXISTS facilities_lds.nz_facilities (
      facility_id serial PRIMARY KEY
    , external_facility_id character varying(80) DEFAULT ''
    , name character varying(250) DEFAULT ''
    , external_name character varying(250) DEFAULT ''
    , use character varying(40) NOT NULL DEFAULT ''
    , use_type character varying(150) DEFAULT ''
    , use_subtype character varying(150) DEFAULT ''
    , estimated_occupancy integer DEFAULT 0
    , last_modified date DEFAULT ('now'::text)::date
    , shape public.geometry(MultiPolygon, 2193) NOT NULL
);

INSERT INTO facilities_lds.nz_facilities(
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
    )
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
WHERE internal IS FALSE;

CREATE INDEX shx_nz_facilities
    ON facilities_lds.nz_facilities USING gist (shape);
