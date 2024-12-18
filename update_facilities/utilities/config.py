# -*- coding: utf-8 -*-
import configparser
import errno
import getpass
import os.path
import platform
from qgis.core import QgsApplication


def get_config_path() -> str | os.PathLike:
    """search for config file, if it doesn't exist create"""
    config_file_path = os.path.join(
        QgsApplication.qgisSettingsDirPath(), "update_facilities", "config.ini"
    )

    if not os.path.isfile(config_file_path):  # If config.ini does not exist
        if not os.path.exists(
            os.path.dirname(config_file_path)
        ):  # If /update_facilities/ does not exist
            try:
                os.makedirs(os.path.dirname(config_file_path))
            except OSError as e:  # Catch OSError if that folder exists
                if e.errno != errno.EEXIST:
                    raise

        current_platform = platform.system()

        # create a config file with the current db as linz_db and user as postgres
        config = configparser.ConfigParser()
        config.add_section("database")
        config.set("database", "name", "linz_db")
        config.set("database", "host", "localhost")
        config.set("database", "user", "postgres")
        config.set("database", "password", "postgres")

        with open(config_file_path, "w") as configfile:
            config.write(configfile)

    return config_file_path


def read_config(
    config_file_path: str | os.PathLike, parser: configparser.ConfigParser
) -> tuple[str, str, str, str]:

    with open(config_file_path, "r") as f:
        parser.read_file(f)
    name = parser.get("database", "name")
    host = parser.get("database", "host")
    user = parser.get("database", "user")
    password = parser.get("database", "password")

    return name, host, user, password
