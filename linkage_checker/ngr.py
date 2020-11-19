import json
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import requests

from linkage_checker.constants import (
    CACHE_FILENAME,
    CACHE_EXPIRATION_IN_SECONDS,
    REQUEST_HEADERS,
    NAMESPACE_PREFIXES,
    NGR_BASE_URL,
)

logger = logging.getLogger(__name__)

URL_NGR = "https://nationaalgeoregister.nl/geonetwork"


def get_all_ngr_records(enable_caching):
    # if there is no cache file or it is expired, create it. otherwise read the cache file
    if not os.path.isfile(CACHE_FILENAME) or cache_is_expired() or not enable_caching:
        logger.debug("downloading ngr record data...")
        ngr_dataset_records = __get_all_ngr_records("type='dataset'")
        ngr_service_records = __get_all_ngr_records(
            "type='service'+AND+organisationName='Beheer+PDOK'"
        )

        ngr_records_to_remove = []
        for ngr_record in ngr_dataset_records:
            record_info = get_ngr_record_info(
                ngr_record["uuid_dataset"], ngr_service_records
            )
            if len(record_info) != 2:
                ngr_records_to_remove.append(ngr_record)
            else:
                ngr_record.update(record_info)

        for ngr_record_to_remove in ngr_records_to_remove:
            ngr_dataset_records.remove(ngr_record_to_remove)

        if enable_caching:
            logger.debug("writing all ngr record data to cache file " + CACHE_FILENAME)
            with open(CACHE_FILENAME, "w", encoding="utf-8") as f:
                json.dump(ngr_dataset_records, f, ensure_ascii=False, indent=4)
    else:
        logger.debug("reading ngr records from cache file " + CACHE_FILENAME)
        with open(CACHE_FILENAME) as infile:
            ngr_dataset_records = json.load(infile)

    return ngr_dataset_records


def cache_is_expired():
    file_mod_time = datetime.fromtimestamp(
        os.stat(CACHE_FILENAME).st_mtime
    )  # This is a datetime.datetime object!
    now = datetime.today()
    max_delay = timedelta(seconds=CACHE_EXPIRATION_IN_SECONDS)
    return now - file_mod_time > max_delay


def __get_all_ngr_records(constraint):

    ngr_metadata_records = []

    start_position = "1"
    while True:
        records_base_url = (
            NGR_BASE_URL
            + "/srv/dut/csw-inspire?request=GetRecords&Service=CSW&Version=2.0.2&typeNames"
            "=gmd:MD_Metadata&resultType=results&constraintLanguage=CQL_TEXT"
            "&constraint_language_version=1.1.0&constraint="
            + constraint
            + "&startPosition="
            + start_position
        )
        logger.debug("fetching records_base_url: " + records_base_url)
        response = requests.get(records_base_url, headers=REQUEST_HEADERS)
        document = ET.fromstring(response.content)

        ex_node = document.findall("./ows:ExceptionReport", NAMESPACE_PREFIXES)
        if len(ex_node) > 0:
            exception_code = document.find(
                "./ows:ExceptionReport/ows:Exception/[@exceptionCode]",
                NAMESPACE_PREFIXES,
            ).text
            if exception_code is not None:
                raise Exception(
                    "Exception in CSW response, exceptionCode: " + exception_code
                )

        start_position = document.find(
            ".//csw:SearchResults/[@nextRecord]", NAMESPACE_PREFIXES
        ).attrib["nextRecord"]

        temp_records = document.findall(".//csw:SummaryRecord", NAMESPACE_PREFIXES)
        for temp_record in temp_records:
            dataset_title = temp_record.find("dc:title", NAMESPACE_PREFIXES).text
            identifier = temp_record.find("dc:identifier", NAMESPACE_PREFIXES).text

            temp_record_result = {
                "uuid_dataset": identifier,
                "dataset_title": dataset_title,
            }
            ngr_metadata_records.append(temp_record_result)

        if start_position == "0":
            break

    return ngr_metadata_records


def get_ngr_record_info(uuid_dataset, ngr_service_records):
    result = {}

    record_info_base_url = (
        NGR_BASE_URL
        + "/srv/api/0.1/records/"
        + uuid_dataset
        + "/related?type=services&start=1&rows=100"
    )
    logger.debug("fetching record_info_base_url: " + record_info_base_url)
    response = requests.get(record_info_base_url, headers=REQUEST_HEADERS)
    document = ET.fromstring(response.content)

    items = document.iter("item")
    for item in items:
        uuid = item.find("id").text
        if __uuid_in_service_records(uuid, ngr_service_records):
            title = item.find("title/value").text
            if "wms" in title.lower() or "view" in title.lower():
                result["uuid_viewer"] = uuid
            if "atom" in title.lower() or "download" in title.lower():
                result["uuid_download"] = uuid
            if "uuid_download" not in result and "wfs" in title.lower():
                result["uuid_download"] = uuid
    return result


def __uuid_in_service_records(uuid, ngr_service_records):
    for service_record in ngr_service_records:
        if service_record["uuid_dataset"] == uuid:
            return True
    return False
