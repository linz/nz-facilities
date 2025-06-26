import os.path
from psycopg2 import sql as psycopg_sql

from update_facilities.utilities.dbconn import DBConnection
from update_facilities.sql import check_facilities_table_sql


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class TestDBConn(object):
    """Used to test a dbconn has been made and database contains expected schema"""

    def __init__(self, update_facilities_plugin):
        self.update_facilities_plugin = update_facilities_plugin

    def run_test_dbconn(self) -> bool:
        """Checks able to connect to the database and contains assumed schema"""

        self.update_facilities_plugin.facilities_logging.info("start run_test_dbconn")

        connection_created = self.check_conn()

        if connection_created:
            self.update_facilities_plugin.facilities_logging.info("connection created")

            temp_facilities_table_correct = self.check_temp_facilities_table()

            facilities_table_correct = self.check_facilities_table()

            lds_facilities_table_correct = self.check_lds_facilities_table()

            if (
                not temp_facilities_table_correct
                or not facilities_table_correct
                or not lds_facilities_table_correct
            ):
                self.update_facilities_plugin.dbconn = None
                return False
            else:
                return True

        else:
            self.update_facilities_plugin.dbconn = None
            return False

    def check_conn(self) -> bool:
        """
        Retrieve the current db from the config and inits a connection
        """

        self.update_facilities_plugin.dbconn = DBConnection(
            self.update_facilities_plugin.name,
            self.update_facilities_plugin.host,
            self.update_facilities_plugin.user,
            self.update_facilities_plugin.password,
        )
        try:
            self.update_facilities_plugin.dbconn.connect()
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(
                "database connection created\n"
            )
            return True
        except Exception as e:
            self.update_facilities_plugin.dlg.msgbox.insertHtml(
                '> <font color="red"><b>Error</b>: "{}"</font><br>'.format(str(e))
            )
            return False

    def check_facilities_table(self) -> bool:
        """
        Check the facilities tables exists and contains the required columns
        """

        # check temp_facilities table exists
        sql = check_facilities_table_sql.check_facilities_table_exists

        facilities_table_exits = self.update_facilities_plugin.dbconn.select(sql, None)[
            0
        ][0]

        if facilities_table_exits:
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(
                "facilities table exits\n"
            )
        else:
            self.update_facilities_plugin.facilities_logging.error(
                "No facilities table in the facilities schema"
            )

            self.update_facilities_plugin.dlg.msgbox.insertPlainText(
                "No facilities table in the facilities schema\n"
            )
            return False

        # check facilities tabel has correct columns
        sql = check_facilities_table_sql.check_facilities_table_column_names

        column_names = self.update_facilities_plugin.dbconn.select(sql, None)

        required_columns = [
            ["facility_id"],
            ["source_facility_id"],
            ["name"],
            ["source_name"],
            ["use"],
            ["use_type"],
            ["use_subtype"],
            ["estimated_occupancy"],
            ["last_modified"],
            ["internal"],
            ["internal_comments"],
            ["shape"],
        ]

        missing_column = False
        for column in required_columns:
            # row[0] as the first column of a single column table
            if column not in column_names:
                self.update_facilities_plugin.facilities_logging.error(
                    "Column '{}' missing from input".format(str(column[0])),
                )

                self.update_facilities_plugin.dlg.msgbox.insertHtml(
                    "column <font> <b>{}</b></font> missing from input<br>".format(
                        str(column[0])
                    )
                )
                missing_column = True
        if missing_column:
            return False
        else:
            return True

    def check_lds_facilities_table(self) -> bool:
        """
        Check the nz_facilities tables in the facilities_lds schema exists
        and contains the required columns
        """

        # check temp_facilities table exists
        sql = check_facilities_table_sql.check_lds_facilities_table_exists

        nz_facilities_table_exits = self.update_facilities_plugin.dbconn.select(
            sql, None
        )[0][0]

        if nz_facilities_table_exits:
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(
                "nz_facilities table exits\n"
            )
        else:
            self.update_facilities_plugin.facilities_logging.error(
                "No nz_facilities table in the facilities_lds schema"
            )

            self.update_facilities_plugin.dlg.msgbox.insertPlainText(
                "No nz_facilities table in the facilities_lds schema\n"
            )
            return False

        # check facilities tabel has correct columns
        sql = check_facilities_table_sql.check_lds_facilities_table_column_names

        column_names = self.update_facilities_plugin.dbconn.select(sql, None)

        required_columns = [
            ["facility_id"],
            ["source_facility_id"],
            ["name"],
            ["source_name"],
            ["use"],
            ["use_type"],
            ["use_subtype"],
            ["estimated_occupancy"],
            ["last_modified"],
            ["shape"],
        ]

        missing_column = False
        for column in required_columns:
            # row[0] as the first column of a single column table
            if column not in column_names:
                self.update_facilities_plugin.facilities_logging.error(
                    "Column '{}' missing from nz_facilities".format(str(column[0])),
                )

                self.update_facilities_plugin.dlg.msgbox.insertHtml(
                    "column <font> <b>{}</b></font> missing from nz_facilities<br>".format(
                        str(column[0])
                    )
                )
                missing_column = True
        if missing_column:
            return False
        else:
            return True

    def check_temp_facilities_table(self) -> bool:
        """
        Check the temp facilities tables exists and contains the required columns
        """

        # check temp_facilities table exists
        sql = check_facilities_table_sql.check_temp_facilities_table_exists

        facilities_table_exits = self.update_facilities_plugin.dbconn.select(sql, None)[
            0
        ][0]

        if facilities_table_exits:
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(
                "temp facilities table exits\n"
            )
        else:
            self.update_facilities_plugin.facilities_logging.error(
                "Column '{}' missing from input".format(str(column[0])),
            )

            self.update_facilities_plugin.dlg.msgbox.insertPlainText(
                "No temp facilities table in the facilities schema\n"
            )
            return False

        # check facilities tabel has correct columns
        sql = check_facilities_table_sql.check_temp_facilities_table_column_names

        column_names = self.update_facilities_plugin.dbconn.select(sql, None)

        required_columns = [
            ["fid"],
            ["shape"],
            ["facility_id"],
            ["source_facility_id"],
            ["name"],
            ["source_name"],
            ["use"],
            ["use_type"],
            ["use_subtype"],
            ["estimated_occupancy"],
            ["last_modified"],
            ["change_action"],
            ["change_description"],
            ["sql"],
            ["geometry_change"],
            ["comments"],
            ["new_source_name"],
            ["new_source_use_type"],
            ["new_source_occupancy"],
            ["error_description"],
        ]

        missing_column = False
        for column in required_columns:
            # row[0] as the first column of a single column table
            if column not in column_names:
                self.update_facilities_plugin.facilities_logging.error(
                    "Column '{}' missing from input".format(str(column[0])),
                )

                self.update_facilities_plugin.dlg.msgbox.insertHtml(
                    "column <font> <b>{}</b></font> missing from input<br>".format(
                        str(column[0])
                    )
                )
                missing_column = True
        if missing_column:
            return False
        else:
            return True
