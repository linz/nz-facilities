import datetime
import json
import csv
import typing
from io import StringIO, BytesIO
from dataclasses import dataclass
from pathlib import Path

import pyproj
import requests
import openpyxl
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, transform
from tqdm import tqdm

from facilities_change_detection.core.facilities import ChangeAction, ExternalSource
from facilities_change_detection.core.log import get_logger


logger = get_logger()

MOH_PUBLIC_HOSPITALS_URL = "https://www.health.govt.nz/sites/default/files/prms/pst_csvs/LegalEntitySummaryPublicHospital.csv"
MOH_FACILITY_CODE_TABLE_URL = (
    "https://www.tewhatuora.govt.nz/assets/Our-health-system/Data-and-statistics/Common-code-tables/Facilities20240201.xlsx"
)


class MoHHospital(ExternalSource):
    @classmethod
    def from_external(cls) -> typing.Self:
        pass


def parse_public_hospitals_csv(text: str) -> list[dict[str, str]]:
    # Strip trailing commas
    lines = [line.rstrip(",") for line in text.splitlines()]
    # Strip leading and trailing whitespace from column names
    keys = [key.strip() for key in lines.pop(0).split(",")]
    # Build reader object
    reader = csv.DictReader(StringIO("\n".join(lines)), fieldnames=keys)
    # Return list of rows
    return list(reader)


def parse_facility_code_xlsx(content: bytes):
    wb = openpyxl.load_workbook(BytesIO(content), read_only=True)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    rows = [dict(zip(headers, row)) for row in ws.iter_rows(min_row=2, values_only=True)]
    existing = set()
    duplicate = []
    for row in rows:
        name = row["Name"]
        if name in existing:
            duplicate.append(name)
        else:
            existing.add(name)
    ...
    rowdict = {row["Name"]: row for row in rows}
    ...


def request_moh_data():
    logger.info("Downloading MoH Public Hospitals CSV")
    public_hospitals_response = requests.get(MOH_PUBLIC_HOSPITALS_URL)
    public_hospitals_response.raise_for_status()
    logger.info("Parsing MoH Public Hospitals CSV")
    public_hospitals = parse_public_hospitals_csv(public_hospitals_response.text)
    logger.info("Downloading MoH Facility Codes XLSX")
    facility_code_response = requests.get(MOH_FACILITY_CODE_TABLE_URL)
    facility_code_response.raise_for_status()
    logger.info("Parsing MoH Facility Codes XLSX")
    facility_codes = parse_facility_code_xlsx(facility_code_response.content)
    ...
