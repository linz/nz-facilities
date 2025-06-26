# -*- coding: utf-8 -*-
"""SQL queries related to checking the temporary table"""

check_facilities_logging_table_exists = """
SELECT EXISTS (SELECT *
                 FROM INFORMATION_SCHEMA.TABLES
                 WHERE TABLE_SCHEMA = 'facilities'
                 AND  TABLE_NAME = 'facilities_logging')
"""

check_facilities_logging_table_column_names = """
SELECT column_name
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = N'facilities_logging';
"""

check_facilities_table_column_names = """
SELECT column_name
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = N'facilities';
"""

check_facilities_table_exists = """
SELECT EXISTS (SELECT *
                 FROM INFORMATION_SCHEMA.TABLES
                 WHERE TABLE_SCHEMA = 'facilities'
                 AND  TABLE_NAME = 'facilities')
"""

check_lds_facilities_table_column_names = """
SELECT column_name
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'facilities_lds'
AND TABLE_NAME = N'nz_facilities';
"""

check_lds_facilities_table_exists = """
SELECT EXISTS (SELECT *
                 FROM INFORMATION_SCHEMA.TABLES
                 WHERE TABLE_SCHEMA = 'facilities_lds'
                 AND  TABLE_NAME = 'nz_facilities')
"""

check_temp_facilities_table_column_names = """
SELECT column_name
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = N'temp_facilities';
"""

check_temp_facilities_table_exists = """
SELECT EXISTS (SELECT *
                 FROM INFORMATION_SCHEMA.TABLES
                 WHERE TABLE_SCHEMA = 'facilities'
                 AND  TABLE_NAME = 'temp_facilities')
"""
