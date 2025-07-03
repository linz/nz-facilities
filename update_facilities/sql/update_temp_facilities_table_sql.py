# -*- coding: utf-8 -*-
"""SQL queries related to updating the temp facilities table"""

add_error_description_to_temp_facilities = """
UPDATE facilities.temp_facilities
SET error_description = CONCAT(error_description, %s)
WHERE fid =%s;
"""


clear_temp_facility_error_description = """
UPDATE facilities.temp_facilities SET error_description=null;
"""

insert_temp_facilities = """
INSERT INTO facilities.temp_facilities(
	fid, shape, facility_id, source_facility_id, name, source_name, use, use_type, use_subtype, estimated_occupancy, last_modified, change_action, change_description, sql, geometry_change, comments, new_source_name, new_source_use_type, new_source_occupancy)
	VALUES (%s, ST_SetSRID(ST_GeometryFromText(%s), 2193), %s, %s, %s, %s, %s, %s, %s, %s, TO_DATE(%s,'YYYYMMDD'), %s, %s, %s, %s, %s, %s, %s, %s)
    returning fid;
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

select_temp_facilities_error_description = """
SELECT
error_description
FROM facilities.temp_facilities
WHERE fid =%s;
"""

truncate_temp_facilities_table = """
TRUNCATE TABLE facilities.temp_facilities;
"""
