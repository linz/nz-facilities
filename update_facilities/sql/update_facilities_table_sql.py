# -*- coding: utf-8 -*-
"""SQL queries related to updating the facilities table"""

facilities_table_row_count = """
SELECT COUNT(*) FROM facilities.facilities;
"""

select_facilities = """
SELECT
facility_id,
source_facility_id,
name,
source_name,
use,
use_type,
use_subtype,
estimated_occupancy,
last_modified,
internal,
internal_comments,
ST_AsText(shape) as shape_wkt
FROM facilities.facilities;
"""

select_temp_facilities = """
SELECT
fid,
facility_id,
source_facility_id,
name,
source_name,
use,
use_type,
use_subtype,
estimated_occupancy,
last_modified,
change_action,
change_description,
sql,
geometry_change,
comments,
new_source_name,
new_source_use_type,
new_source_occupancy,
ST_AsText(shape) as shape_wkt
FROM facilities.temp_facilities;
"""
add_facility_count = """
with a as (INSERT INTO facilities.facilities(
	source_facility_id, name, source_name, use, use_type, use_subtype, estimated_occupancy, last_modified, internal, internal_comments, shape)
	VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_DATE, %s, %s, ST_GeomFromText(%s, 2193)) returning 1)
select count(*) from a;
"""

delete_facility = """
DELETE FROM facilities.temp_facilities
WHERE facility_id = %s;
"""

delete_facility_count = """
with a as (DELETE FROM facilities.facilities WHERE facility_id = %s returning 1)
select count(*) from a;
"""

update_facility_geom = """
with a as (UPDATE facilities.facilities
	SET shape = ST_GeomFromText(%s, 2193),last_modified=CURRENT_DATE
	WHERE facility_id =%s returning 1)
select count(*) from a;
"""

select_area = """
SELECT
ST_Area(shape)
FROM facilities.facilities
WHERE facility_id = %s;
"""

select_geom = """
SELECT
ST_AsText(shape) as shape_wkt
FROM facilities.facilities
WHERE facility_id = %s;
"""

update_facility_attribute = """
with a as ({} returning 1)
select count(*) from a;
"""

add_error_description_to_temp_facilities = """
UPDATE facilities.temp_facilities
SET error_description = CONCAT(error_description, %s)
WHERE fid =%s;
"""

select_error_description = """
SELECT
error_description
FROM facilities.temp_facilities
WHERE fid =%s;
"""
