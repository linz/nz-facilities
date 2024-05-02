import re
from pathlib import Path
from urllib.parse import urljoin

import lxml.html
import requests

from facilities_change_detection.core.io import download_file
from facilities_change_detection.core.log import get_logger

logger = get_logger()

HPI_EXCEL_PAGE_URL = "https://www.tewhatuora.govt.nz/for-health-professionals/data-and-statistics/nz-health-statistics/data-references/code-tables/common-code-tables/"


def download_hpi_excel(output_folder: Path, overwrite: bool) -> Path:
    """
    Downloads the latest HPI Facilities Code Table Excel file from the
    Te Whatu Ora website. The file will be saved with a name in the format
    `hpi__{year}-{month}-{day}.xlsx`, where the date is parsed from the
    date last updated given in the filename.

    This function depends on being able to parse the download link from the
    HTML of the Te Whatu Ora website, as the URL of the file to download is not
    static over time. If the markup of the Te Whatu Ora website changes, this
    function will likely cease to work.

    Args:
        output_folder: folder to save the file into.
        overwrite: whether to overwrite an existing file with the same name
            in the specified output folder.

    Raises:
        ValueError: if the download link was unable to be parsed from the HTML,
            if the date was unable to be parsed from the URL, or a file with
            the same name already exists in the specified output folder and
            `overwrite` is not True.
        requests.RequestException [or child Exceptions]: if any network issues
            occur.

    Returns:
        The path where the file was saved.
    """
    # Download the landing page and raise exception for any errors
    print(logger.getEffectiveLevel())
    logger.info("Downloading HTML of landing page")
    r = requests.get(HPI_EXCEL_PAGE_URL)
    r.raise_for_status()
    # Parse HTML of landing page
    tree = lxml.html.fromstring(r.content)
    # Find all <a> elements with a class of "download__link" who are descendents
    # of a <div? element whose id value starts with "facility-code-table"
    els = tree.xpath('//div[starts-with(@id,"facility-code-table")]//a[@class="download__link"]')
    # If there isn't a single element, raise an exception
    if len(els) != 1:
        raise ValueError(f"Found {len(els)} matching download link xpath selector, expected 1")
    logger.info("Parsed download link from landing page")
    # Extract href attribute from <a> element and resolve full download URL
    href = els[0].attrib["href"]
    download_url = urljoin(HPI_EXCEL_PAGE_URL, href)
    # Extract date from filename and build standardised output filename
    download_filename = href.split("/")[-1]
    if name_match := re.match(r"Facilities(\d{4})(\d{2})(\d{2})", download_filename):
        year, month, day = name_match.groups()
        output_file = output_folder / f"hpi__{year}-{month}-{day}.xlsx"
    else:
        raise ValueError(f"Cannot parse date from filename {download_filename}")
    # Download the file to the output file, and return the path
    if overwrite is False and output_file.exists():
        raise ValueError(f"{output_file} already exists. To overwrite, rerun with --overwrite.")
    return download_file(download_url, output_file)
