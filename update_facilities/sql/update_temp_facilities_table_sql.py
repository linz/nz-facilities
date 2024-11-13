# -*- coding: utf-8 -*-
"""SQL queries related to updating the temp facilities table"""

truncate_temp_facilities_table = """
TRUNCATE TABLE facilities.temp_facilities;
"""

insert_temp_facilities = """
INSERT INTO facilities.temp_facilities(
	fid, shape, facility_id, source_facility_id, name, source_name, use, use_type, use_subtype, estimated_occupancy, last_modified, change_action, change_description, sql, geometry_change, comments, new_source_name, new_source_use_type, new_source_occupancy)
	VALUES (%s, ST_SetSRID(ST_GeometryFromText(%s), 2193), %s, %s, %s, %s, %s, %s, %s, %s, TO_DATE(%s,'YYYYMMDD'), %s, %s, %s, %s, %s, %s, %s, %s)
    returning fid;
"""
