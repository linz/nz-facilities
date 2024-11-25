from datetime import datetime
import os.path

from update_facilities.sql import update_facilities_table_sql


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class UpdateFacilitiesTable(object):
    """Updates the temp facilities table to update the update facilities table"""

    def __init__(self, update_facilities_plugin):
        self.update_facilities_plugin = update_facilities_plugin

    def update_temp_facilities_error_description(
        self, msg_box_message, error_description, fid
    ):
        self.update_facilities_plugin.dlg.msgbox.insertPlainText(msg_box_message)

        # rollback connection so no changes saved, save error message and commit.
        self.update_facilities_plugin.dbconn.conn.rollback()

        sql = update_facilities_table_sql.add_error_description_to_temp_facilities
        data = [
            error_description,
            fid,
        ]
        self.update_facilities_plugin.dbconn.db_execute_without_commit(sql, data)
        self.update_facilities_plugin.dbconn.conn.commit()

    def update_facilities_table(self):
        """
        Retrieve the current db from the config and inits a connection
        """

        def catch_NULL(variable):
            if not variable:
                return None
            else:
                return variable

        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "starting update of the facilities table\n"
        )

        db_correct = self.update_facilities_plugin.run_test_dbconn()
        if not db_correct:
            message = (
                "\nThe facilities table has not been updated.\n"
                "Please fix errors in the facilites or temp facilities table\n"
            )
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(message)
            return False

        self.update_facilities_plugin.dlg.msgbox.insertPlainText("\n")

        # check_temp_facilities_table

        sql = update_facilities_table_sql.facilities_table_row_count
        rows = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql
            )
        )

        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "\nrows count before update: {}\n\n".format(rows[0][0])
        )

        # iterate through temp facilities table and adjust row by row
        sql = update_facilities_table_sql.select_temp_facilities
        temp_facilities_table = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql
            )
        )

        update_error = False

        no_change = 0
        added = 0
        deleted = 0
        geom_changed = 0
        attributes_changed = 0
        geom_and_attributes_changed = 0

        count = 0
        self.update_facilities_plugin.dlg.msgbox.repaint()

        if len(temp_facilities_table) == 0:
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(
                "the temp facilities table is empty,\n"
                "please load the new NZ facilities.\n"
            )
            self.update_facilities_plugin.dbconn.conn.rollback()
            return False

        for row in temp_facilities_table:
            count += 1
            # if count > 200:
            #     break
            if count % 500 == 0:
                self.update_facilities_plugin.dlg.msgbox.insertPlainText(
                    "-- {} features have been processed\n".format(count)
                )
                self.update_facilities_plugin.dlg.msgbox.repaint()

            fid = row[0]
            facility_id = row[1]
            source_facility_id = row[2]
            name = row[3]
            source_name = row[4]
            use = row[5]
            use_type = row[6]
            use_subtype = row[7]
            estimated_occupancy = row[8]
            change_action = row[10]
            change_description = row[11]
            change_sql = row[12]
            geometry_change = row[13]
            comments = row[14]
            new_source_name = row[15]
            new_source_use_type = row[16]
            new_source_occupancy = row[17]
            shape_wkt = row[18]

            if change_action == "add":
                sql = update_facilities_table_sql.add_facility_count

                data = [
                    source_facility_id,
                    name,
                    source_name,
                    use,
                    use_type,
                    use_subtype,
                    estimated_occupancy,
                    False,
                    None,
                    shape_wkt,
                ]

                added_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                    sql, data
                )[
                    0
                ][
                    0
                ]

                if added_count != 1:
                    update_error = True

                    msg_box_message = (
                        "failed to add new facility with \n"
                        "source_facility_id: {}\n"
                        "{} features added\n"
                        "when 1 feature should have been added\n"
                    ).format(facility_id, added_count)

                    error_description = "Failed to add facility, added {} features when 1 should have been added. ".format(
                        added_count
                    )

                    self.update_temp_facilities_error_description(
                        msg_box_message, error_description, fid
                    )
                added += 1

            elif change_action == "remove":
                sql = update_facilities_table_sql.delete_facility_count
                data = [facility_id]

                deleted_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                    sql, data
                )[
                    0
                ][
                    0
                ]

                if deleted_count != 1:
                    update_error = True

                    msg_box_message = (
                        "failed to deleted facility id: {}\n"
                        "{} features deleted\n"
                        "when 1 feature should have been deleted\n"
                    ).format(facility_id, deleted_count)

                    error_description = "Failed to delete facility, deleted {} features when 1 should have been deleted. ".format(
                        deleted_count
                    )

                    self.update_temp_facilities_error_description(
                        msg_box_message, error_description, fid
                    )
                deleted += 1

            elif change_action == "update_geom":

                sql = update_facilities_table_sql.select_geom
                data = data = [facility_id]
                orig_wkt = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                    sql, data
                )[
                    0
                ][
                    0
                ]

                sql = update_facilities_table_sql.update_facility_geom
                data = [shape_wkt, facility_id]

                modified_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                    sql, data
                )[
                    0
                ][
                    0
                ]

                if modified_count != 1:
                    update_error = True

                    msg_box_message = (
                        "failed to modify facility id: {}\n"
                        "{} features modified\n"
                        "when 1 feature should have been modified\n"
                    ).format(facility_id, modified_count)

                    error_description = "Failed to update geometry, updated {} features when 1 should have been updated. ".format(
                        modified_count
                    )

                    self.update_temp_facilities_error_description(
                        msg_box_message, error_description, fid
                    )

                if orig_wkt == shape_wkt:
                    update_error = True

                    msg_box_message = (
                        "geom for facility id {} has not been modified\n".format(
                            facility_id
                        )
                    )

                    error_description = (
                        "Failed to update geometry, old and new geometries the same. "
                    )

                    self.update_temp_facilities_error_description(
                        msg_box_message, error_description, fid
                    )

                geom_changed += 1

            elif change_action == "update_attr":
                # -1 to remove the ; from end of script as it is inserted into script

                sql = update_facilities_table_sql.update_facility_attribute.format(
                    change_sql[:-1]
                )

                attribute_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                    sql
                )[
                    0
                ][
                    0
                ]

                if attribute_count != 1:
                    update_error = True

                    msg_box_message = (
                        "failed to modify facility id: {}\n" "sql: {}\n"
                    ).format(facility_id, change_sql)

                    error_description = "Failed to modify facility using change_sql. "

                    self.update_temp_facilities_error_description(
                        msg_box_message, error_description, fid
                    )

                attributes_changed += 1

            elif change_action == "update_geom_attr":
                sql = update_facilities_table_sql.select_geom
                data = data = [facility_id]
                orig_wkt = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                    sql, data
                )[
                    0
                ][
                    0
                ]

                # -1 to remove the ; from end of script
                sql = update_facilities_table_sql.update_facility_attribute.format(
                    change_sql[:-1]
                )

                attribute_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                    sql
                )[
                    0
                ][
                    0
                ]

                if attribute_count != 1:
                    update_error = True

                    msg_box_message = (
                        "failed to modify facility id: {}\n" "sql: {}\n"
                    ).format(facility_id, change_sql)

                    error_description = "Failed to modify facility using change_sql. "

                    self.update_temp_facilities_error_description(
                        msg_box_message, error_description, fid
                    )

                sql = update_facilities_table_sql.update_facility_geom
                data = [shape_wkt, facility_id]

                modified_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                    sql, data
                )[
                    0
                ][
                    0
                ]

                if modified_count != 1:
                    update_error = True

                    msg_box_message = (
                        "failed to modify facility id: {}\n"
                        "{} features modified\n"
                        "when 1 feature should have been modified\n"
                    ).format(facility_id, modified_count)

                    error_description = "Failed to update geometry, updated {} features when 1 should have been updated. ".format(
                        modified_count
                    )

                    self.update_temp_facilities_error_description(
                        msg_box_message, error_description, fid
                    )

                if orig_wkt == shape_wkt:
                    update_error = True

                    msg_box_message = (
                        "geom for facility id {} has not been modified\n".format(
                            facility_id
                        )
                    )

                    error_description = (
                        "Failed to update geometry, old and new geometries the same. "
                    )

                    self.update_temp_facilities_error_description(
                        msg_box_message, error_description, fid
                    )
                geom_and_attributes_changed += 1

            elif not change_action:

                no_change += 1

            else:
                msg_box_message = (
                    "change action: {} \n"
                    "is not valid, please correct so it is either:\n"
                    "add, remove, update_attr, update_geom, update_geom_attr or null\n".format(
                        change_action
                    )
                )
                update_error = True

        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "\n\n{} features added\n".format(added)
        )
        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "{} features deleted\n".format(deleted)
        )
        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "{} geometries modified\n".format(geom_changed)
        )
        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "{} attributes changed\n".format(attributes_changed)
        )

        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "{} features had both geometries and attributes changed\n".format(
                geom_and_attributes_changed
            )
        )

        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "{} feature unchanged\n".format(no_change)
        )

        sql = update_facilities_table_sql.facilities_table_row_count
        rows = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql
            )
        )
        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "\nrows count after update: {}\n\n".format(rows[0][0])
        )

        if update_error:
            message = (
                "\nThe facilities table has not been updated.\n"
                "Please check errors listed in this window.\n"
                "The error_description column of the \n"
                "temp facilities table has been appended with \n"
                "any errors found for the feature it relates to.\n"
            )
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(message)
            self.update_facilities_plugin.dbconn.conn.rollback()
        else:
            message = "\nThe facilities table has successfully been updated.\n"
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(message)

            self.update_facilities_plugin.dbconn.conn.commit()
