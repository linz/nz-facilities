# -*- coding: utf-8 -*-
"""SQL queries related to logging for the facilities"""

insert_facilities_task_log = """
with a as (INSERT INTO facilities.facilities_task_logging(
	log_level, "user", task, comment)
	VALUES (%s, %s, %s, %s) returning 1)
select count(*) from a;
"""
