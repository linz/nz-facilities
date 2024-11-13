import os.path

from update_facilities.utilities.dbconn import DBConnection
from update_facilities.sql import check_facilities_table_sql


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class TestDBConn(object):
    """Used to test a dbconn has been made and database contains expected schema"""

    def __init__(self, update_facilities):
        self.update_facilities = update_facilities

    def check_conn(self):
        """
        Retrieve the current db from the config and inits a connection
        """

        self.dbconn = DBConnection(
            self.update_facilities.name,
            self.update_facilities.host,
            self.update_facilities.user,
            self.update_facilities.password,
        )
        try:
            self.dbconn.connect()
            self.update_facilities.dlg.msgbox.insertPlainText(
                "database connection created\n"
            )
            return True
        except Exception as e:
            self.update_facilities.dlg.msgbox.insertHtml(
                '> <font color="red"><b>Error</b>: "{}"</font><br>'.format(str(e))
            )
            return False

    def check_temp_facilities_table(self):
        """
        Check the temp facilities tables exists and contains the required columns
        """

        # check temp_facilities table exists
        sql = check_facilities_table_sql.check_temp_facilities_table_exists
        facilities_table_exits = self.dbconn.select(sql, None)[0][0]
        if facilities_table_exits:
            self.update_facilities.dlg.msgbox.insertPlainText(
                "facilities table exits\n"
            )
        else:
            self.update_facilities.dlg.msgbox.insertPlainText(
                "No facilities table in the facilities schema\n"
            )
            return False

        # check facilities tabel has correct columns
        sql = check_facilities_table_sql.check_column_names
        column_names = self.dbconn.select(sql, None)

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
        ]

        for column in required_columns:
            # row[0] as the first column of a single column table
            if column not in column_names:
                self.update_facilities.dlg.msgbox.insertHtml(
                    "column <font> <b>{}</b></font> missing from input<br>".format(
                        str(column[0])
                    )
                )
