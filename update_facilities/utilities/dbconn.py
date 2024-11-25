# -*- coding: utf-8 -*-

import os
import psycopg2

from update_facilities.utilities.database_warning import database_warning

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class DBConnection:
    def __init__(self, dbname, host, user, password):
        self.dbname = dbname
        self.host = host
        self.user = user
        self.password = password
        self.conn = None

    def connect(self):
        """Connect to DB"""
        try:
            self.conn = psycopg2.connect(
                "dbname='{}' host='{}' port='{}' user='{}' password='{}' ".format(
                    self.dbname, self.host, 5432, self.user, self.password
                )
            )
            return True
        except psycopg2.DatabaseError as error:
            self.conn = None
            raise

    def db_execute(self, sql, data=None):
        """
        Execute an sql statement

        @param  sql:    sql statement
        @type   sql:    string
        @param  data:   data inserted into SQL statement
        @type   data:   tuple

        @return:    Cursor object
        @rtype:     psycopg2.extensions.cursor
        """
        # Set cursor
        cursor = self.conn.cursor()

        # Execute query
        try:
            cursor.execute(sql, data)
            self.conn.commit()
        except psycopg2.DatabaseError as db_error:
            database_warning("Database Error", str(db_error), "warning")
            self.conn.rollback()
            return None

        except psycopg2.InterfaceError as error:
            # Raise the error
            cursor.close()
            self.conn.rollback()
            raise error
            return None

        return cursor

    def execute(self, sql, data=None):
        """Execute an update or insert statement with no return

        @param  sql:    sql statement
        @type   sql:    string
        @param  data:    data inserted into SQL statement
        @type   data:    tuple

        @return:    Boolean if no error was raised
        @rtype:     bool
        """
        cursor = self.db_execute(sql, data)
        if cursor:
            cursor.close()
        return None

    def execute_sql_from_file(self, sql_file):
        sql_path = os.path.join(__location__, "..", "sql", sql_file)
        with open(sql_path) as f:
            sql = f.read()
        f.closed
        self.execute(sql)

    def copy_from_csv(self, csv_path, table):
        copy_sql = """
            COPY {} FROM stdin WITH CSV HEADER
            DELIMITER as ','
            """.format(
            table
        )
        cursor = self.conn.cursor()
        with open(csv_path, "r") as f:
            try:
                cursor.copy_expert(sql=copy_sql, file=f)
                self.conn.commit()
            except psycopg2.DatabaseError as db_error:
                self.conn.rollback()
                database_warning("Database Error", str(db_error), "warning")
                return None
            cursor.close()

    def select(self, sql, data=None):
        """Execute a Select statement and return results

        @param  sql:    SQL statement (must be Select)
        @type   sql:    string
        @param  data:    data inserted into SQL statement
        @type   data:    tuple

        @return:        List of rows returned from query
        @rtype:         list
        """
        cursor = self.db_execute(sql, data)
        if cursor:
            try:
                rows = [list(row) for row in cursor]
                cursor.close()
                return rows
            except psycopg2.ProgrammingError as p_error:
                database_warning("Programming Error", str(p_error), "warning")
                # This occurs if a DatabaseError has been raised in db_execute()
                cursor.close()
        return None

    def db_execute_and_return_without_commit(self, sql, data=None):
        """Execute, return result, but do not commit

        @param  sql:    sql statement
        @type   sql:    string
        @param  data:    data inserted into SQL statement
        @type   data:    tuple

        @return:    Boolean if no error was raised
        @rtype:     bool
        """
        # Set cursor
        cursor = self.conn.cursor()

        # Execute query
        try:
            cursor.execute(sql, data)
            rows = [list(row) for row in cursor]
            cursor.close()
            return rows
        except psycopg2.DatabaseError as db_error:
            database_warning("Database Error", str(db_error), "warning")
            self.conn.rollback()
            raise db_error

        except psycopg2.InterfaceError as error:
            # Raise the error
            cursor.close()
            self.conn.rollback()
            raise error

    def db_execute_without_commit(self, sql, data=None):
        """Execute but do not commit

        @param  sql:    sql statement
        @type   sql:    string
        @param  data:    data inserted into SQL statement
        @type   data:    tuple

        @return:    Boolean if no error was raised
        @rtype:     bool
        """
        # Set cursor
        cursor = self.conn.cursor()

        # Execute query
        try:
            cursor.execute(sql, data)
            if cursor:
                cursor.close()
            return None
        except psycopg2.DatabaseError as db_error:
            database_warning("Database Error", str(db_error), "warning")
            self.conn.rollback()
            raise db_error

        except psycopg2.InterfaceError as error:
            # Raise the error
            cursor.close()
            self.conn.rollback()
            raise error
