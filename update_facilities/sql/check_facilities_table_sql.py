# -*- coding: utf-8 -*-
"""SQL queries related to checking the temporary table"""

check_temp_facilities_table_exists = """
SELECT EXISTS (SELECT *
                 FROM INFORMATION_SCHEMA.TABLES
                 WHERE TABLE_SCHEMA = 'facilities'
                 AND  TABLE_NAME = 'temp_facilities')
"""

check_temp_facilities_column_names = """
SELECT column_name
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = N'temp_facilities';
"""

check_facilities_table_exists = """
SELECT EXISTS (SELECT *
                 FROM INFORMATION_SCHEMA.TABLES
                 WHERE TABLE_SCHEMA = 'facilities'
                 AND  TABLE_NAME = 'facilities')
"""

check_facilities_column_names = """
SELECT column_name
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = N'facilities';
"""
