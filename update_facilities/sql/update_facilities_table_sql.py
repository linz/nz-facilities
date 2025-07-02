# -*- coding: utf-8 -*-
"""SQL queries related to updating the facilities table"""

add_error_description_to_temp_facilities = """
UPDATE facilities.temp_facilities
SET error_description = CONCAT(error_description, %s)
WHERE fid =%s;
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

duplicate_facilities_count = """
SELECT COUNT(*)
FROM facilities.facilities t1
  JOIN facilities.facilities t2
    ON (t1.source_facility_id,t1.name,
t1.source_name) is not distinct from (t2.source_facility_id,t2.name,
t2.source_name)
where t1.facility_id = %s;
"""

facilities_table_row_count = """
SELECT COUNT(*) FROM facilities.facilities;
"""

select_area = """
SELECT
ST_Area(shape)
FROM facilities.facilities
WHERE facility_id = %s;
"""

select_error_description = """
SELECT
error_description
FROM facilities.temp_facilities
WHERE fid =%s;
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

select_facility_with_id = """
SELECT
facility_id,
source_facility_id,
name,
source_name,
use,
use_type,
use_subtype,
estimated_occupancy,
internal,
internal_comments,
ST_AsText(shape) as shape_wkt
FROM facilities.facilities
WHERE facility_id = %s;
"""
select_facilities_attributes_with_attributes = """
SELECT
source_facility_id,
name,
source_name,
use,
use_type,
use_subtype,
estimated_occupancy,
internal,
internal_comments
FROM facilities.facilities
WHERE
source_facility_id = %s AND
name = %s AND
source_name = %s AND
use = %s AND
use_type = %s AND
use_subtype = %s AND
estimated_occupancy = %s AND
internal = %s AND
internal_comments = %s;
"""

select_facilities_attributes_with_id = """
SELECT
source_facility_id,
name,
source_name,
use,
use_type,
use_subtype,
estimated_occupancy,
internal,
internal_comments
FROM facilities.facilities
WHERE facility_id = %s;
"""

select_facilities_with_attributes_count = """
SELECT COUNT(*)
FROM facilities.facilities
WHERE (
source_facility_id,
name,
source_name
) is not distinct from (%s,
%s,
%s);
"""

select_facilities_with_geom_count = """
SELECT COUNT(*)
FROM facilities.facilities
WHERE
ST_AsText(shape) is not distinct from %s
"""

select_geom = """
SELECT
ST_AsText(shape) as shape_wkt
FROM facilities.facilities
WHERE facility_id = %s;
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

select_temp_facilities_change_count = """
select case when change_action is null then 'no_change' else change_action end, count(*)
from facilities.temp_facilities
where change_action in ('add', 'remove', 'update_geom', 'update_attr', 'update_geom_attr') or change_action is NULL
group by change_action;
"""

update_facility_attribute = """
with a as ({} returning 1)
select count(*) from a;
"""

update_facility_geom = """
with a as (UPDATE facilities.facilities
	SET shape = ST_GeomFromText(%s, 2193),last_modified=CURRENT_DATE
	WHERE facility_id =%s and ST_AsText(shape) != %s returning 1)
select count(*) from a;
"""
