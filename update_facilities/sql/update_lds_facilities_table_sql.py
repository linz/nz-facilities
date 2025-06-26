# -*- coding: utf-8 -*-
"""SQL queries related to updating the nz_facilities table in the facilities_lds schema"""

nz_facilities_table_row_count = """
SELECT COUNT(*) FROM facilities_lds.nz_facilities;
"""

nz_facilities_ids = """
SELECT facility_id FROM facilities_lds.nz_facilities limit 10;
"""

facilities_ids = """
SELECT facility_id FROM facilities.facilities;
"""
