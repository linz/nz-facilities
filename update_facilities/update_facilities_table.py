from datetime import datetime
import os.path

from update_facilities.sql import update_facilities_table_sql
from update_facilities.sql import update_temp_facilities_table_sql

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

class UpdateFacilitiesTable(object):
    """Updates the temp facilities table to update the update facilities table"""

    def __init__(self, update_facilities_plugin):
        self.update_facilities_plugin = update_facilities_plugin

    def run_update_facilities_table(self) -> bool:
        """Updates facilities table using the temp_facilities table in the database"""
        self.update_facilities_plugin.facilities_logging.info(
            "start run_update_facilities_table"
        )

        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "\n--------------------\n\n"
        )

        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "starting update of the facilities table\n\n"
        )

        # check connection and temp facilities table in db?
        connection_and_tables_correct = (
            self.update_facilities_plugin.test_dbconn.run_test_dbconn()
        )

        if not connection_and_tables_correct:
            message = (
                "\nThe facilities table has not been updated.\n"
                "The DB connection test failed.\n"
                "Please fix errors in the facilites or temp facilities table.\n"
            )
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(message)
            return False

        # check_temp_facilities_table
        row_count_before = self.check_and_report_temp_facilities_table()

        self.clear_temp_table_error_description()

        # return

        # iterate through temp facilities table and adjust row by row
        sql = update_temp_facilities_table_sql.select_temp_facilities
        temp_facilities_table = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql
            )
        )

        self.update_error = False

        unchanged = 0
        added = 0
        deleted = 0
        geom_changed = 0
        attributes_changed = 0
        geom_and_attributes_changed = 0

        count = 0
        self.update_facilities_plugin.dlg.msgbox.repaint()

        if len(temp_facilities_table) == 0:
            self.update_facilities_plugin.facilities_logging.error(
                "the temp_facilities table is empty, the facilities table has not been updated",
            )

            self.update_facilities_plugin.dlg.msgbox.insertPlainText(
                "the temp facilities table is empty,\n"
                "please load the new NZ facilities.\n"
            )
            self.update_facilities_plugin.dbconn.conn.rollback()
            return False

        for row in temp_facilities_table:
            count += 1
            if count % 500 == 0:
                self.update_facilities_plugin.dlg.msgbox.insertPlainText(
                    "-- {} features have been processed\n".format(count)
                )
                self.update_facilities_plugin.dlg.msgbox.repaint()

            self.fid = row[0]
            self.facility_id = row[1]
            self.source_facility_id = row[2]
            self.name = row[3]
            self.source_name = row[4]
            self.use = row[5]
            self.use_type = row[6]
            self.use_subtype = row[7]
            self.estimated_occupancy = row[8]
            self.change_action = row[10]
            change_description = row[11]
            self.change_sql = row[12]
            geometry_change = row[13]
            comments = row[14]
            self.new_source_name = row[15]
            self.new_source_use_type = row[16]
            new_source_occupancy = row[17]
            self.shape_wkt = row[18]

            if self.change_action == "add":
                succesfully_added = self.add_facility()

                if succesfully_added:

                    no_duplicates = self.add_facility_duplicate_check()

                    no_overlaps = self.check_overlapping_geom()

                    if no_duplicates and no_overlaps:
                        added += 1

            elif self.change_action == "remove":
                succesfully_removed = self.remove_facility()

                if succesfully_removed:
                    deleted += 1

            elif self.change_action == "update_geom":
                successfully_updated_geom = self.update_geom()
                no_overlaps = self.check_overlapping_geom()

                if successfully_updated_geom and no_overlaps:
                    geom_changed += 1

            elif self.change_action == "update_attr":
                successfully_updated_attr = self.update_attr()

                if successfully_updated_attr:
                    attributes_changed += 1

            elif self.change_action == "update_geom_attr":
                successfully_updated_geom_attr = self.update_geom_attr()
                no_overlaps = self.check_overlapping_geom()

                if successfully_updated_geom_attr and no_overlaps:
                    # if went through modified attributes step and the modified geom step with no errors
                    geom_and_attributes_changed += 1

            elif not self.change_action:

                unchanged += 1

            else:
                msg_box_message = "Facility ID {}: Failed to change, change action '{}' not valid".format(self.facility_id, self.change_action)

                self.update_temp_facilities_error_description(
                    msg_box_message, self.fid
                )

                self.update_facilities_plugin.facilities_logging.error(msg_box_message)

                self.update_error = True

        if not self.update_error:
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(
                "\n{} features added\n".format(added)
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
                "{} feature unchanged\n".format(unchanged)
            )

        sql = update_facilities_table_sql.facilities_table_row_count
        rows = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql
            )
        )
        row_count_after = rows[0][0]
        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "\nfacilities table row count after update: {}\n\n".format(row_count_after)
        )

        if self.update_error:
            self.update_facilities_plugin.facilities_logging.error(
                "update failed, no changes made to the facilities table"
            )
            self.update_facilities_plugin.dlg.msgbox.insertHtml(
                '> <font color="red"><b>update failed</b></font><br>'
            )
            message = (
                "The facilities table has not been updated.\n"
                "Please check errors listed in this window.\n"
                "The error_description column of the \n"
                "temp facilities table has been appended with \n"
                "any errors found for the feature it relates to.\n"
            )
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(message)
            self.update_facilities_plugin.dbconn.conn.rollback()
        else:
            self.update_facilities_plugin.facilities_logging.insert_facilities_result_log(
                added,
                deleted,
                geom_changed,
                attributes_changed,
                geom_and_attributes_changed,
                unchanged,
                row_count_before,
                row_count_after
            )

            self.update_facilities_plugin.facilities_logging.info(
                "update successful, now {} features in the facilities table".format(
                    rows[0][0]
                ),
            )

            self.update_facilities_plugin.facilities_logging.info(
                "facilities table updated, {} features inserted".format(count),
            )

            self.update_facilities_plugin.dlg.msgbox.insertHtml(
                '> <font color="green"><b>update successful</b></font><br>'
            )
            message = "The facilities table has successfully been updated.\n"
            self.update_facilities_plugin.dlg.msgbox.insertPlainText(message)

            self.update_facilities_plugin.dbconn.conn.commit()

    def add_facility(self):
        # add a new facility and return the count of number added to check if was successful

        sql = update_facilities_table_sql.add_facility_count

        data = [
            self.source_facility_id,
            self.name,
            self.source_name,
            self.use,
            self.use_type,
            self.use_subtype,
            self.estimated_occupancy,
            False,
            None,
            self.shape_wkt,
        ]

        added_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
            sql, data
        )[
            0
        ][
            0
        ]

        if added_count != 1:
            msg_box_message = "Source Facility ID {}: Failed to add".format(self.source_facility_id)
            log_msg = ("{}, {} feature{} added when 1 feature should have been added".format(msg_box_message, added_count, self.get_plural(added_count)))

            self.update_facilities_plugin.facilities_logging.error(log_msg)

            self.update_error = True

            self.update_temp_facilities_error_description(
                msg_box_message, self.fid
            )
            added_successfully = False
        else:
            added_successfully = True

        return added_successfully

    def add_facility_duplicate_check(self):
        # check no duplicate added
        # check geom and attributes separately in case it is not an addition but a modify
        # check db first as update_temp_facilities_error_description also rolls back changes

        no_duplicates = True

        # check for duplicate attributes
        sql = update_facilities_table_sql.select_facilities_with_attributes_count
        data = [
            self.source_facility_id,
            self.name,
            self.source_name,
        ]

        attr_row_count = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql, data
            )
        ) [0][0]

        # check for duplicate geometries
        sql = update_facilities_table_sql.select_facilities_with_geom_count
        data = [self.shape_wkt,]

        geom_row_count = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql, data
            )
        ) [0][0]

        if attr_row_count != 1:
            msg_box_message = "Source Facility ID {}: Failed to add, duplicate attributes".format(self.source_facility_id)
            log_msg = ("{}, {} feature{} had duplicate attributes".format(msg_box_message, attr_row_count - 1, self.get_plural(attr_row_count - 1)))

            self.update_facilities_plugin.facilities_logging.error(log_msg)

            self.update_error = True

            self.update_temp_facilities_error_description(
                msg_box_message, self.fid
            )

            no_duplicates = False

        if geom_row_count != 1:
            msg_box_message = "Source Facility ID {}: Failed to add, duplicate geometry".format(self.source_facility_id)
            log_msg = ("{}, {} feature{} had duplicate geometry".format(msg_box_message, geom_row_count -1 , self.get_plural(geom_row_count - 1)))

            self.update_facilities_plugin.facilities_logging.error(log_msg)

            self.update_error = True

            self.update_temp_facilities_error_description(
                msg_box_message, self.fid
            )

            no_duplicates = False

        return no_duplicates

    def check_and_report_temp_facilities_table(self):
        # read temp table and reports what changes are expected
        # along with the row count of the facilities.facilities table

        # add in count of expected change which should be made
        sql = update_temp_facilities_table_sql.select_temp_facilities_change_count
        rows = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql
            )
        )

        rows.sort()
        message = '\nExpected changes:\n'

        change_dic = { "add" : "adding", "remove" :"removing", "update_geom":"updating the geometry of", "update_attr":"updating the attributes of", "update_geom_attr":"updating the geometry and attributes of", "unchanged":"not changing"}

        for change_type, change_count in rows:
            change_text = change_dic[change_type]
            message += "{} {} features\n".format(change_text, change_count)

        self.update_facilities_plugin.dlg.msgbox.insertPlainText(message)

        sql = update_facilities_table_sql.facilities_table_row_count
        rows = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql
            )
        )

        self.update_facilities_plugin.facilities_logging.info(
            "row count before update: {}".format(rows[0][0]),
        )

        row_count_before = rows[0][0]
        self.update_facilities_plugin.dlg.msgbox.insertPlainText(
            "\nfacilities table row count before update: {}\n\n".format(row_count_before)
        )

        return row_count_before

    def check_overlapping_geom(self):
        # check new geometry does not overlap existing geometries
        sql = update_facilities_table_sql.select_facilities_with_overlapping_geom_count
        data = [self.shape_wkt,]

        overlapping_geom_row_count = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql, data
            )
        ) [0][0]

        if overlapping_geom_row_count != 0:
            if self.change_action == 'add':
                id_value = self.source_facility_id
                msg_box_id_text = 'Source Facility ID'
                msg_box_change = 'add'

            elif self.change_action in ('update_geom', 'update_geom_attr'):
                 id_value = self.facility_id
                 msg_box_id_text = 'Facility ID'
                 msg_box_change = 'modify'

            msg_box_message = "{} {}: Failed to {}, overlapping geoms".format(msg_box_id_text, id_value, msg_box_change)
            log_msg = ("{}, {} feature{} had overlapping geometry".format(msg_box_message, overlapping_geom_row_count, self.get_plural(overlapping_geom_row_count)))

            self.update_facilities_plugin.facilities_logging.error(log_msg)

            self.update_error = True

            self.update_temp_facilities_error_description(
                msg_box_message, self.fid
            )

            return False
        else:
            return True

    def clear_temp_table_error_description(self):
        # clear out previous error descriptions from temp table

        sql = update_temp_facilities_table_sql.clear_temp_facility_error_description
        self.update_facilities_plugin.dbconn.execute(
            sql
        )

    def get_plural(self, count):
        if count > 1:
            return 's'
        else:
            return ''

    def remove_facility(self):

        succesfully_removed = False

        # check id exists
        sql = update_facilities_table_sql.select_facility_with_id
        data = [self.facility_id]
        rows = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql, data
            )
        )
        row_count = len(rows)
        if row_count == 0:
            msg_box_message = "Facility ID {}: Failed to delete. No matching id".format(self.facility_id)

            self.update_facilities_plugin.facilities_logging.error(msg_box_message)

            self.update_error = True

            self.update_temp_facilities_error_description(
                msg_box_message, self.fid
            )
        elif row_count > 1:
            # should not be possible as it is the primary id
            msg_box_message = "Facility ID {}: Failed to delete".format(self.facility_id)

            log_msg = (
                "{}, {} feature{} deleted when 1 feature should have been deleted".format(
                    msg_box_message, row_count, self.get_plural(row_count)
                )
            )

            self.update_facilities_plugin.facilities_logging.error(log_msg)

            self.update_error = True

            self.update_temp_facilities_error_description(
                msg_box_message, self.fid
            )

        else:
            # single id found, remove facility
            sql = update_facilities_table_sql.delete_facility_count
            data = [self.facility_id]

            deleted_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql, data
            )[
                0
            ][
                0
            ]

            if deleted_count != 1:
                # this section should no longer be used as the check for id's / row count will notify the
                # user when there is not a 1 to 1 match.
                # Kept incase fails for unexpected reasons
                msg_box_message = "Facility ID {}: Failed to delete".format(self.facility_id)
                log_msg = (
                    "{}, {} feature{} deleted when 1 feature should have been deleted".format(
                        msg_box_message, self.facility_id, deleted_count, self.get_plural(deleted_count)
                    )
                )

                self.update_facilities_plugin.facilities_logging.error(log_msg)

                self.update_error = True

                self.update_temp_facilities_error_description(
                    msg_box_message, self.fid
                )
            else:
                succesfully_removed = True

        return succesfully_removed

    def update_attr(self):
        successfully_updated_attr = False

        # get original feature so can compare after the change
        sql = update_facilities_table_sql.select_facilities_attributes_with_id
        data = [self.facility_id]

        original_feature_rows = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql, data
            )
        )

        original_feature_count = len(original_feature_rows)

        if original_feature_count != 1:
            msg_box_message = "Facility ID {}: Failed to modify attributes. No matching id".format(self.facility_id)

            self.update_facilities_plugin.facilities_logging.error(msg_box_message)

            self.update_error = True

            self.update_temp_facilities_error_description(
                msg_box_message, self.fid
            )

            return successfully_updated_attr

        original_feature_attr = original_feature_rows[0]

        # -1 to remove the ; from end of script as it is inserted into script
        sql = update_facilities_table_sql.update_facility_attribute.format(
            self.change_sql[:-1]
        )

        attribute_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
            sql
        )[
            0
        ][
            0
        ]

        # only a single feature shoudl have its attributes modified
        if attribute_count != 1:
            msg_box_message = "Facility ID {}: Failed to modify attr".format(self.facility_id)
            log_msg = "{}. Change_sql: {}".format(
                msg_box_message, self.change_sql
            )
            self.update_facilities_plugin.facilities_logging.error(log_msg)

            self.update_error = True

            self.update_temp_facilities_error_description(
                msg_box_message, self.fid
            )

        else:
            # check features attributes have changed
            sql = update_facilities_table_sql.select_facilities_attributes_with_id
            data = [self.facility_id]

            new_feature_attr = (
                self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                    sql, data
                )
            )[0]

            if new_feature_attr == original_feature_attr:
                # there has been no changes in attributes
                msg_box_message = "Facility ID {}: Failed to modify attr, new matches old".format(self.facility_id)
                log_msg = (
                    "{}. Change_sql: {}".format(
                        msg_box_message, self.change_sql
                    )
                )

                self.update_facilities_plugin.facilities_logging.error(log_msg)

                self.update_error = True

                self.update_temp_facilities_error_description(
                    msg_box_message, self.fid
                )

            else:
                # check no duplicates after modification

                sql = update_facilities_table_sql.duplicate_facilities_count
                data = [self.facility_id]

                duplicate_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                    sql, data
                )[
                    0
                ][
                    0
                ]

                if duplicate_count != 1:
                    msg_box_message = "Facility ID {}: Failed to modify attr, duplicate features".format(self.facility_id)
                    log_msg = (
                        "{}, {} duplicate feature{} created."
                        " Change_sql: {}".format(
                            msg_box_message, duplicate_count - 1, self.get_plural(duplicate_count - 1), self.change_sql
                        )
                    )

                    self.update_facilities_plugin.facilities_logging.error(log_msg)

                    self.update_error = True

                    self.update_temp_facilities_error_description(
                        msg_box_message, self.fid
                    )

                else:
                    successfully_updated_attr = True

        return successfully_updated_attr

    def update_geom(self):
        successfully_updated_geom = False

        # get original geometry to compare change against
        sql = update_facilities_table_sql.select_geom
        data = [self.facility_id]
        rows = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
            sql, data
        )

        # check rows returned, if not rows or more than 1 will not be updating a single feature
        row_count = len(rows)
        if row_count == 0:
            msg_box_message = "Facility ID {}: Failed to modify geometry. No matching id".format(self.facility_id)

            self.update_facilities_plugin.facilities_logging.error(msg_box_message)

            self.update_error = True

            self.update_temp_facilities_error_description(
                msg_box_message, self.fid
            )
        elif row_count > 1:
            # should not be possible as it is the primary id
            msg_box_message = "Facility ID {}: Failed to modify geometry, multiple matching ids".format(self.facility_id)
            log_msg = (
                "{}, {} feature{} with matching id when 1 feature should have been identified".format(
                    msg_box_message, row_count, self.get_plural(row_count)
                )
            )

            self.update_facilities_plugin.facilities_logging.error(log_msg)

            self.update_error = True

            self.update_temp_facilities_error_description(
                msg_box_message, self.fid
            )

        else:
            orig_wkt = rows[0][0]
            # modify the geometry
            sql = update_facilities_table_sql.update_facility_geom
            data = [self.shape_wkt, self.facility_id, self.shape_wkt]

            modified_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql, data
            )[
                0
            ][
                0
            ]

            if modified_count != 1:
                # if a singe record has not been modified, check if due to old and enw geoms matching and report
                if orig_wkt == self.shape_wkt:
                    msg_box_message = "Facility ID {}: Failed to modify geometry, new matches old".format(self.facility_id)
                    self.update_facilities_plugin.facilities_logging.error(msg_box_message)

                    self.update_error = True

                    self.update_temp_facilities_error_description(
                        msg_box_message, self.fid
                    )

                else:
                    msg_box_message = "Facility ID {}: Failed to modify geom".format(self.facility_id)
                    log_msg = (
                        "{}, {} feature{} modified when 1 feature should have been modified".format(
                            msg_box_message, modified_count, self.get_plural(modified_count)
                        )
                    )
                    self.update_facilities_plugin.facilities_logging.error(log_msg)

                    self.update_error = True

                    self.update_temp_facilities_error_description(
                        msg_box_message, self.fid
                    )
            else:
                successfully_updated_geom = True

        return successfully_updated_geom

    def update_geom_attr(self):
        successfully_updated_geom_attr = True

        # get original geometry and attributes so can compare after the change
        # modified_attributes = True

        sql = update_facilities_table_sql.select_geom
        data = data = [self.facility_id]
        orig_wkt = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
            sql, data
        )[
            0
        ][
            0
        ]

        sql = update_facilities_table_sql.select_facilities_attributes_with_id
        data = [self.facility_id]

        original_feature_attr = (
            self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                sql, data
            )
        )[0]

        # -1 to remove the ; from end of script as it is inserted into script

        sql = update_facilities_table_sql.update_facility_attribute.format(
            self.change_sql[:-1]
        )

        attribute_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
            sql
        )[
            0
        ][
            0
        ]

        if attribute_count != 1:
            successfully_updated_geom_attr = False

            msg_box_message = "Facility ID {}: Failed to modify attr".format(self.facility_id)
            log_msg = "{}. Change sql: {}".format(
                msg_box_message, self.change_sql
            )
            self.update_facilities_plugin.facilities_logging.error(log_msg)

            self.update_error = True

            self.update_temp_facilities_error_description(
                msg_box_message, self.fid
            )

        else:
            # check features attributes have changed
            sql = update_facilities_table_sql.select_facilities_attributes_with_id
            data = [self.facility_id]

            new_feature_attr = (
                self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                    sql, data
                )
            )[0]

            if new_feature_attr == original_feature_attr:
                successfully_updated_geom_attr = False

                # there has been no changes in attributes
                msg_box_message = "Facility ID {}: Failed to modify attr, new matches old".format(self.facility_id)
                log_msg = (
                    "{}. Change_sql: {}".format(
                        msg_box_message, self.change_sql
                    )
                )

                self.update_facilities_plugin.facilities_logging.error(log_msg)

                self.update_error = True

                self.update_temp_facilities_error_description(
                    msg_box_message, self.fid
                )

            else:
                # check no duplicates after modification

                sql = update_facilities_table_sql.duplicate_facilities_count
                data = [self.facility_id]

                duplicate_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
                    sql, data
                )[
                    0
                ][
                    0
                ]

                if duplicate_count != 1:
                    successfully_updated_geom_attr = False
                    msg_box_message = "Facility ID {}: Failed to modify attr, duplicate features".format(self.facility_id)

                    log_msg = (
                        "{}, {} duplicate feature{} created."
                        " Change_sql: {}".format(
                            msg_box_message, duplicate_count -1 , self.get_plural(duplicate_count - 1), self.change_sql
                        )
                    )

                    self.update_facilities_plugin.facilities_logging.error(log_msg)

                    self.update_error = True

                    self.update_temp_facilities_error_description(
                        msg_box_message, self.fid
                    )

        sql = update_facilities_table_sql.update_facility_geom
        data = [self.shape_wkt, self.facility_id, self.shape_wkt]

        modified_count = self.update_facilities_plugin.dbconn.db_execute_and_return_without_commit(
            sql, data
        )[
            0
        ][
            0
        ]

        if modified_count != 1:
            if orig_wkt == self.shape_wkt:
                successfully_updated_geom_attr = False

                msg_box_message = "Facility ID {}: Failed to modify geom, new matches old".format(self.facility_id)

                self.update_facilities_plugin.facilities_logging.error(msg_box_message)

                self.update_error = True

                self.update_temp_facilities_error_description(
                    msg_box_message, self.fid
                )

            else:
                successfully_updated_geom_attr = False

                msg_box_message = "Facility ID {}: Failed to modify geom".format(self.facility_id)

                log_msg = (
                    "{}, {} feature{} modified when 1 feature should have been modified".format(
                        msg_box_message, modified_count, self.get_plural(modified_count)
                    )
                )
                self.update_facilities_plugin.facilities_logging.error(log_msg)

                self.update_error = True

                self.update_temp_facilities_error_description(
                    msg_box_message, self.fid
                )

        return successfully_updated_geom_attr

    def update_temp_facilities_error_description(
        self, msg_box_message: str, fid: int
    ):
        self.update_facilities_plugin.dlg.msgbox.insertPlainText(msg_box_message+"\n")

        # rollback connection so no changes saved, save error message and commit.
        self.update_facilities_plugin.dbconn.conn.rollback()

        sql = update_temp_facilities_table_sql.add_error_description_to_temp_facilities
        data = [
            msg_box_message,
            fid,
        ]
        self.update_facilities_plugin.dbconn.db_execute_without_commit(sql, data)
        self.update_facilities_plugin.dbconn.conn.commit()
