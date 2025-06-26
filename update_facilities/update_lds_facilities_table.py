from datetime import datetime
import os.path

from update_facilities.sql import update_lds_facilities_table_sql
from update_facilities.sql import update_facilities_table_sql


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class UpdateLDSFacilitiesTable(object):
    """Updates the temp facilities table to update the update facilities table"""

    def __init__(self, update_facilities_plugin):
        self.update_facilities_plugin = update_facilities_plugin

    def check_tables_duplicated(self):
        """
        compares the nz_facilitiies table with the the facilities table which is used to update it
        this helps us be certain we are actually updating the table and not just replacing with
        exactly the same
        """

        sql = update_lds_facilities_table_sql.nz_facilities_table_row_count
        nz_facilities_row_count = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql
            )
        )[0][0]

        # self.update_facilities_plugin.dlg.msgbox.insertPlainText(
        #     "tables_duplicated {}\n".format(nz_facilities_row_count)
        # )
        # nz_facilities_row_count = 2684

        sql = update_facilities_table_sql.facilities_table_row_count
        facilities_row_count = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql
            )
        )[0][0]

        # self.update_facilities_plugin.dlg.msgbox.insertPlainText(
        #     "tables_duplicated {}\n".format(facilities_row_count)
        # )

        # facilities_row_count = 2684

        if not nz_facilities_row_count == facilities_row_count:
            return False

        sql = update_facilities_table_sql.facilities_ids
        facilities_ids = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql
            )
        )

        sql = update_facilities_table_sql.facilities_ids
        nz_facilities_ids = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql
            )
        )

    def run_update_lds_facilities_table(self) -> bool:
        """Updates nz_facilities table in the facilities_lds schema using the facilities table in the faciltiies schema"""
        self.update_facilities_plugin.facilities_logging.info(
            "start run_update_lds_facilities_table"
        )

        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "\n--------------------\n\n"
        )

        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "starting update of the LDS facilities table\n\n"
        )

        # check connection and temp facilities table in db?
        connection_and_tables_correct = (
            self.update_facilities_plugin.test_dbconn.run_test_dbconn()
        )

        if not connection_and_tables_correct:
            message = (
                "\nThe nz_facilities table has not been updated.\n"
                "The DB connection test failed.\n"
                "Please fix errors in the facilites, nz_facilities or temp_facilities tables.\n"
            )
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(message)
            return False

        # check_nz_facilities_table

        sql = update_lds_facilities_table_sql.nz_facilities_table_row_count
        rows = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql
            )
        )

        self.update_facilities_plugin.facilities_logging.info(
            "row count before update: {}".format(rows[0][0]),
        )

        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "\n\nrow count before update: {}\n\n\n".format(rows[0][0])
        )

        tables_duplicated = self.check_tables_duplicated()

        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "tables_duplicated {}".format(tables_duplicated)
        )
        # # iterate through temp facilities table and adjust row by row
        # sql = update_facilities_table_sql.select_temp_facilities
        # temp_facilities_table = (
        #     self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
        #         sql
        #     )
        # )
