CREATE OR REPLACE FUNCTION facilities_lds.nz_facilities_insert()
RETURNS integer AS
$$

    WITH populate_nz_facilities AS (
        INSERT INTO facilities_lds.nz_facilities (
              facility_id
            , source_facility_id
            , name
            , source_name
            , use
            , use_type
            , use_subtype
            , estimated_occupancy
            , last_modified
            , shape
        )
        SELECT
              facility_id
            , source_facility_id
            , name
            , source_name
            , use
            , use_type
            , use_subtype
            , estimated_occupancy
            , last_modified
            , shape
        FROM facilities.facilities
        RETURNING *
    )
    SELECT count(*)::integer FROM populate_nz_facilities;

$$
LANGUAGE sql VOLATILE;

CREATE OR REPLACE FUNCTION facilities_lds.populate_facilities_lds()
RETURNS TABLE(
      table_name text
    , rows_inserted integer
) AS
$$

    TRUNCATE facilities_lds.nz_facilities;

    VALUES
          ('nz_facilities' , facilities_lds.nz_facilities_insert())
    ;

$$
LANGUAGE sql VOLATILE;