import os.path

from qgis.core import (
    QgsVectorLayerExporter,
    QgsWkbTypes,
)

from update_facilities.sql import update_temp_facilities_table_sql


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class UpdateTempFacilities(object):
    """Used to test a dbconn has been made and database contains expected schema"""

    def __init__(self, update_facilities):
        self.update_facilities = update_facilities

    def check_input_facilities_layer(self):
        """
        Checks input layer is valid, had correct geometry and crs, and correct fields
        """
        self.update_facilities.dlg.msgbox.insertPlainText(
            "checking input facilities layer\n"
        )

        invalid_input = False
        self.input_layer = (
            self.update_facilities.dlg.comboBox_update_temp_facilities.currentLayer()
        )

        if self.input_layer is None:
            self.update_facilities.dlg.msgbox.insertHtml(
                '> <font color="red"><b>Error: no input layer</b></font><br>'
            )
            invalid_input = True
            return False

        if not self.input_layer.isValid():
            self.update_facilities.dlg.msgbox.insertHtml(
                '> <font color="red"><b>Error: input layer is invalid</b></font><br>'
            )
            invalid_input = True

        wkbtype = QgsWkbTypes.displayString(self.input_layer.wkbType())
        if wkbtype != "MultiPolygon":
            self.update_facilities.dlg.msgbox.insertHtml(
                '> <font color="red"><b>Error: input layer is {}, MultiPolygon required"</b></font><br>'.format(
                    wkbtype
                )
            )
            invalid_input = True

        crs = self.input_layer.sourceCrs().authid()
        if crs != "EPSG:2193":
            self.update_facilities.dlg.msgbox.insertHtml(
                '> <font color="red"><b>Error: input layer is {} epsg:2193 required</b></font><br>'.format(
                    crs
                )
            )
            invalid_input = True

        field_names = [
            field.name() for field in self.input_layer.dataProvider().fields().toList()
        ]

        required_columns = [
            "facility_id",
            "source_facility_id",
            "name",
            "source_name",
            "use",
            "use_type",
            "use_subtype",
            "estimated_occupancy",
            "last_modified",
            "change_action",
            "change_description",
            "sql",
            "geometry_change",
            "comments",
            "new_source_name",
            "new_source_use_type",
            "new_source_occupancy",
        ]

        for column in required_columns:
            if column not in field_names:
                self.update_facilities.dlg.msgbox.insertHtml(
                    '> <font color="red"><b>Error: missing {} column</b></font><br>'.format(
                        column
                    )
                )
                invalid_input = True

        if invalid_input:
            return False

        self.update_facilities.dlg.msgbox.insertPlainText("input facilities checked\n")
        return True

    def update_temp_facilities(self):
        """
        Retrieve the current db from the config and inits a connection
        """

        def catch_NULL(variable):
            if not variable:
                return None
            else:
                return variable

        self.update_facilities.dlg.msgbox.insertPlainText(
            "truncating temp facilities table\n"
        )

        sql = update_temp_facilities_table_sql.truncate_temp_facilities_table
        self.update_facilities.dbconn.db_execute(sql, None)

        self.update_facilities.dlg.msgbox.insertPlainText(
            "uploading to temp facilities table\n"
        )
        # repaint before lng process os user can see upto date messages
        self.update_facilities.dlg.msgbox.repaint()

        sql = update_temp_facilities_table_sql.insert_temp_facilities

        # iterate through each feature and add to the temp facilities table
        count = 0
        for feature in self.input_layer.getFeatures():

            fid = catch_NULL(feature["fid"])
            shape = catch_NULL(feature.geometry().asWkt())
            facility_id = catch_NULL(feature["facility_id"])
            source_facility_id = catch_NULL(feature["source_facility_id"])
            name = catch_NULL(feature["name"])
            source_name = catch_NULL(feature["source_name"])
            use = catch_NULL(feature["use"])
            use_type = catch_NULL(feature["use_type"])
            use_subtype = catch_NULL(feature["use_subtype"])
            estimated_occupancy = catch_NULL(feature["estimated_occupancy"])
            last_modified = catch_NULL(feature["last_modified"].toString("yyyyMMdd"))
            change_action = catch_NULL(feature["change_action"])
            change_description = catch_NULL(feature["change_description"])
            feature_sql = catch_NULL(feature["sql"])
            geometry_change = catch_NULL(feature["geometry_change"])
            comments = catch_NULL(feature["comments"])
            new_source_name = catch_NULL(feature["new_source_name"])
            new_source_use_type = catch_NULL(feature["new_source_use_type"])
            new_source_occupancy = catch_NULL(feature["new_source_occupancy"])

            data = [
                fid,
                shape,
                facility_id,
                source_facility_id,
                name,
                source_name,
                use,
                use_type,
                use_subtype,
                estimated_occupancy,
                last_modified,
                change_action,
                change_description,
                feature_sql,
                geometry_change,
                comments,
                new_source_name,
                new_source_use_type,
                new_source_occupancy,
            ]

            fid_added = self.update_facilities.dbconn.select(sql, data)
            if not fid_added:
                self.update_facilities.dlg.msgbox.insertPlainText(
                    "failed to add feature fid {}\n".format(fid)
                )
            else:
                count += 1
            if count % 500 == 0:
                self.update_facilities.dlg.msgbox.insertPlainText(
                    "{} features have been added\n".format(count)
                )
                self.update_facilities.dlg.msgbox.repaint()

        self.update_facilities.dlg.msgbox.insertPlainText(
            "finished updating temp facilities table\n"
        )
