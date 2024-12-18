from datetime import datetime
import os.path

from update_facilities.sql import facilities_logging_sql
from update_facilities.utilities.dbconn import DBConnection

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class FacilitiesLogging(object):
    """Handles logging to the facilities_logging table.

    Logging via sql chosen as team has ability to eaisly query and modify."""

    def __init__(self, update_facilities_plugin):
        self.update_facilities_plugin = update_facilities_plugin

        # setup db connection

        self.dbconn = DBConnection(
            self.update_facilities_plugin.name,
            self.update_facilities_plugin.host,
            self.update_facilities_plugin.user,
            self.update_facilities_plugin.password,
        )

        try:
            self.dbconn.connect()
            # self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            #     "database connection created\n"
            # )
        except Exception as e:
            self.update_facilities_plugin.dlg.msgbox.insertHtml(
                '> <font color="red"><b>Error</b>: "failed to connect to database,<br>error:{}"</font><br>'.format(
                    str(e)
                )
            )

            warn_title = "Failed to connect to database"
            warn_message = "database error: {}".format(str(e))

            self.update_facilities_plugin.iface.messageBar().pushCritical(
                warn_title, warn_message
            )
            self.dbconn = None

        # test logging table exists

    def info(self, comment: str):
        "log an info level log - Confirmation that things are working as expected."
        sql = facilities_logging_sql.insert_facilities_task_log
        data = (
            "info",
            self.update_facilities_plugin.user,
            self.update_facilities_plugin.task,
            comment,
        )

        log_added_count = self.dbconn.select(sql, data)[0][0]

        if log_added_count != 1:
            msg = "Failed to update log\n"
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(msg)

    def warning(self, comment: str):
        """
        log a warning level log - An indication that something unexpected happened,
        or that a problem might occur in the near future. The software is still working as expected.
        """
        sql = facilities_logging_sql.insert_facilities_task_log
        data = (
            "warning",
            self.update_facilities_plugin.user,
            self.update_facilities_plugin.task,
            comment,
        )

        log_added_count = self.dbconn.select(sql, data)[0][0]
        if log_added_count != 1:
            msg = "Failed to update log\n"
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(msg)

    def error(self, comment: str):
        """
        log an error level log - Due to a more serious problem,
        the software has not been able to perform some function.
        """
        sql = facilities_logging_sql.insert_facilities_task_log
        data = (
            "error",
            self.update_facilities_plugin.user,
            self.update_facilities_plugin.task,
            comment,
        )

        log_added_count = self.dbconn.select(sql, data)[0][0]
        if log_added_count != 1:
            msg = "Failed to update log\n"
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(msg)

    def critical(self, comment: str):
        """
        log a critical level log - A serious error, indicating that the
        program itself may be unable to continue running.
        """
        sql = facilities_logging_sql.insert_facilities_task_log
        data = (
            "critical",
            self.update_facilities_plugin.user,
            self.update_facilities_plugin.task,
            comment,
        )

        log_added_count = self.dbconn.select(sql, data)[0][0]
        if log_added_count != 1:
            msg = "Failed to update log\n"
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(msg)

    def insert_facilities_result_log(
        self,
        added: int,
        removed: int,
        geom_updated: int,
        attr_updated: int,
        geom_attr_updated: int,
    ):
        sql = facilities_logging_sql.insert_facilities_result_log
        data = (
            self.update_facilities_plugin.user,
            added,
            removed,
            geom_updated,
            attr_updated,
            geom_attr_updated,
        )
        log_added_count = self.dbconn.select(sql, data)[0][0]
        if log_added_count != 1:
            msg = "Failed to update results log\n"
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(msg)
