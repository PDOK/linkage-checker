import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pkg_resources
from selenium.common.exceptions import TimeoutException

from linkage_checker.constants import (
    NGR_UUID_URL,
    LINKAGE_CHECKER_URL,
)
from linkage_checker.ngr import get_all_ngr_records
from linkage_checker.linkage_check import run_linkage_checker_with_selenium

logger = logging.getLogger(__name__)


def main(
    output_path, remote_selenium_url, enable_caching, browser_screenshots, debug_mode, uuid
):
    logger.info("output path = " + str(output_path))
    logger.info("remote_selenium_url = " + str(remote_selenium_url))
    logger.info("caching enabled = " + str(enable_caching))
    logger.info("make browser screenshots = " + str(browser_screenshots))
    logger.info("debug_mode = " + str(debug_mode))
    if uuid:
        logger.info("uuid = " + ', '.join(uuid))
    else:
        logger.info("uuid = None")

    start_time = datetime.now()

    all_ngr_records = get_all_ngr_records(enable_caching)

    if debug_mode:
        all_ngr_records = all_ngr_records[:3]

    results = []
    number_off_ngr_records = len(all_ngr_records)

    logger.info("number of ngr records found: %d", number_off_ngr_records)

    if uuid:
        only_uuids = set(uuid)
    else:
        only_uuids = None

    for index in range(number_off_ngr_records):
        ngr_record = all_ngr_records[index]

        if only_uuids and not ngr_record["uuid"] in only_uuids:
            logger.info(
                "%s/%s skipping dataset %s (%s)",
                index + 1,
                number_off_ngr_records,
                ngr_record["title"],
                ngr_record["uuid"]
            )
            continue

        logger.info(
            "%s/%s validating dataset %s (%s)",
            index + 1,
            number_off_ngr_records,
            ngr_record["title"],
            ngr_record["uuid"]
        )

        start_time_detail = datetime.now()

        try:
            result = run_linkage_checker_with_selenium(ngr_record, browser_screenshots, remote_selenium_url, start_time_detail, debug_mode)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            trace = [t.strip("\n") for t in traceback.format_exception(exc_type, exc_value, exc_traceback)]
            result = {
                "dataset_title": ngr_record["title"],
                "status": "TIMEOUT" if exc_type == TimeoutException else "ERROR",
                "error": trace,
                "dataset_uuid": ngr_record["uuid"],
                "endpoint_download_service": NGR_UUID_URL + ngr_record["download_service"]["uuid"],
                "endpoint_view_service": NGR_UUID_URL + ngr_record["view_service"]["uuid"],
                "endpoint_meta_data": NGR_UUID_URL + ngr_record["uuid"],
                "duration": str(datetime.now() - start_time_detail),
                "evaluation_report_url": None,
                "linkage_check_results": None
            }

            logger.error(
                "failed to validate dataset %s (%s): %s",
                ngr_record["title"],
                ngr_record["uuid"],
                trace)

        results.append(result)

        write_output(output_path, start_time, results)


def write_output(output_path, start_time, results):
    end_time = datetime.now()
    duration = end_time - start_time

    json_output = json.dumps(
        {
            "linkage_checker_version": pkg_resources.require("linkage_checker")[
                0
            ].version,
            "start_time": start_time.strftime("%d-%m-%Y %H:%M:%S"),
            "start_time_timestamp": start_time.timestamp(),
            "end_time": end_time.strftime("%d-%m-%Y %H:%M:%S"),
            "end_time_timestamp": end_time.timestamp(),
            "total_duration": str(duration),
            "linkage_checker_endpoint": LINKAGE_CHECKER_URL,
            "results": results,
        },
        indent=4,
    )

    if output_path is not None:
        # write json output to file
        Path(output_path).write_text(json_output)
    else:
        # write json output to console
        print(json_output)
