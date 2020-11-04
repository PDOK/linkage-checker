import json
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

from linkage_checker.constants import NGR_UUID_URL, BROWSER_SCREENSHOT_PATH, LINKAGE_CHECKER_URL, \
    REMOTE_WEBDRIVER_CONNECTION_URL
from linkage_checker.domain.dao_ngr import get_all_ngr_records


def run_linkage_checker_with_selenium(logger, ngr_record, browser_screenshots):
    start_time = datetime.now()

    logger.debug(
        'starting linkage check with dataset "' + ngr_record['dataset_title'] + '" (uuid_dataset = ' + ngr_record[
            'uuid_dataset'] + ')')

    logger.debug("connecting to remote Firefox browser (in docker container)...")
    browser = webdriver.Remote(command_executor=REMOTE_WEBDRIVER_CONNECTION_URL,
                               desired_capabilities=DesiredCapabilities.FIREFOX)
    logger.debug("connected!")

    browser.get(LINKAGE_CHECKER_URL)
    logger.debug("webpage " + browser.current_url + " loaded")

    # simulating webpage interaction
    # click on the "Check new metadata" button
    browser.find_element_by_id('newMetadataBtn').click()
    if browser_screenshots:
        browser.save_screenshot(BROWSER_SCREENSHOT_PATH)
    time.sleep(3)

    # click on the three "URL to INSPIRE metadata" buttons
    browser.find_element_by_css_selector(
        '#frm > div:nth-child(2) > div:nth-child(1) > div:nth-child(1) > label:nth-child(2)').click()
    browser.find_element_by_css_selector(
        '#frm > div:nth-child(5) > div:nth-child(1) > div:nth-child(1) > label:nth-child(2)').click()
    browser.find_element_by_css_selector(
        '#frm > div:nth-child(8) > div:nth-child(1) > div:nth-child(1) > label:nth-child(2)').click()
    if browser_screenshots:
        browser.save_screenshot(BROWSER_SCREENSHOT_PATH)
    time.sleep(1)

    # filling in the three textareas with the correct urls to nationaalgeoregister.nl
    browser.find_element_by_id('dataMetadata').send_keys(NGR_UUID_URL + ngr_record['uuid_dataset'])
    browser.find_element_by_id('viewServiceMetadata').send_keys(NGR_UUID_URL + ngr_record['uuid_viewer'])
    browser.find_element_by_id('downloadServiceMetadata').send_keys(NGR_UUID_URL + ngr_record['uuid_download'])
    if browser_screenshots:
        browser.save_screenshot(BROWSER_SCREENSHOT_PATH)
    time.sleep(1)

    # click on the "Check Resources" button to start the linkage checker
    browser.find_element_by_id('checkLinkageBtn').click()
    if browser_screenshots:
        browser.save_screenshot(BROWSER_SCREENSHOT_PATH)
    time.sleep(1)

    logger.debug("linkage check started")
    loop_counter = 0
    while True:
        time.sleep(4)
        logger.debug(f"({str(loop_counter)}) waiting for results...")
        loop_counter += 1
        # checking visibility of the resultsContainer element that indicates when the linkage checker is done
        results_container = browser.find_element_by_id('resultsContainer').value_of_css_property('display')
        if results_container == 'block':
            if browser_screenshots:
                browser.save_screenshot(BROWSER_SCREENSHOT_PATH)
            time.sleep(2)
            break

    logger.debug("linkage check done. querying the DOM to retrieve results")
    linkage_check_results = {}

    # Linkage overview
    # -- View Service linkage
    linkage_check_results['view_service_linkage'] \
        = __query_dom(browser, "thumbs-up", '#resultsOverviewVwAssessment > svg:nth-child(1)')
    # -- Download Service linkage
    linkage_check_results['download_service_linkage'] \
        = __query_dom(browser, "thumbs-up", '#resultsOverviewDwAssessment > svg:nth-child(1)')

    # Main linkage aspects
    # -- Data Set metadata contains Unique Resource Identifier
    linkage_check_results['data_set_metadata_contains_unique_resource_identifier'] \
        = __query_dom(browser, "check-square",
                      '#resultId_DATASET_METADATA_CONTAINS_UNIQUE_RESOURCE_IDENTIFIER > svg:nth-child(1)')
    # -- Data Set metadata contains INSPIRE Spatial Data Theme
    linkage_check_results['data_set_metadata_contains_inspire_spatial_data_theme'] \
        = __query_dom(browser, "check-square",
                      '#resultId_DATASET_METADATA_CONTAINS_INSPIRE_SPATIAL_DATA_THEME > svg:nth-child(1)')
    # -- The View Service has been contacted
    linkage_check_results['the_view_service_has_been_contacted'] \
        = __query_dom(browser, "check-square",
                      '#resultId_VIEW_SERVICE_HAS_BEEN_CONTACTED > svg:nth-child(1)')
    # -- Linkage has been estabilished between the View Service and Data Set
    linkage_check_results['linkage_has_been_estabilished_between_the_view_service_and_data_set'] \
        = __query_dom(browser, "check-square",
                      '#resultId_LINKAGE_FROM_VIEW_SERVICE_TO_DATASET_HAS_BEEN_FOUND > svg:nth-child(1)')
    # -- The Download Service has been contacted
    linkage_check_results['the_download_service_has_been_contacted'] \
        = __query_dom(browser, "check-square",
                      '#resultId_DOWNLOAD_SERVICE_HAS_BEEN_CONTACTED > svg:nth-child(1)')
    # -- Linkage has been estabilished between the Download Service and Data Set
    linkage_check_results['linkage_has_been_estabilished_between_the_download_service_and_data_set'] \
        = __query_dom(browser, "check-square",
                      '#resultId_LINKAGE_FROM_DOWNLOAD_SERVICE_TO_DATASET_HAS_BEEN_FOUND > svg:nth-child(1)')
    # -- A Download link has been determined
    linkage_check_results['a_download_link_has_been_determined'] \
        = __query_dom(browser, "check-square",
                      '#resultId_DOWNLOAD_LINK_HAS_BEEN_DETERMINED > svg:nth-child(1)')

    # Linkage aspects related to the INSPIRE Geoportal
    # -- Data Set metadata exists in the INSPIRE Geoportal
    linkage_check_results['data_set_metadata_exists_in_the_inspire_geoportal'] \
        = __query_dom(browser, "check-square",
                      '#resultId_DATASET_METADATA_EXISTS_IN_INSPIRE_GEOPORTAL > svg:nth-child(1)')
    # -- View Service metadata exists in the INSPIRE Geoportal
    linkage_check_results['view_service_metadata_exists_in_the_inspire_geoportal'] \
        = __query_dom(browser, "check-square",
                      '#resultId_VIEW_SERVICE_METADATA_EXISTS_IN_INSPIRE_GEOPORTAL > svg:nth-child(1)')
    # -- Download Service metadata exists in the INSPIRE Geoportal
    linkage_check_results['download_service_metadata_exists_in_the_inspire_geoportal'] \
        = __query_dom(browser, "check-square",
                      '#resultId_DOWNLOAD_SERVICE_METADATA_EXISTS_IN_INSPIRE_GEOPORTAL > svg:nth-child(1)')

    # get the evaluation report url
    linkage_check_results['evaluation_report_url'] = browser.find_element_by_id('resourceEvalReport').get_attribute(
        "href")

    logger.debug("done querying DOM retrieving linkage check results")

    # storing ngr record information
    results = {
        'dataset_title': ngr_record['dataset_title'],
        'dataset_uuid': ngr_record['uuid_dataset'],
        'endpoint_download_service': NGR_UUID_URL + ngr_record['uuid_download'],
        'endpoint_view_service': NGR_UUID_URL + ngr_record['uuid_viewer'],
        'endpoint_meta_data': NGR_UUID_URL + ngr_record['uuid_dataset'],
        'duration': str(datetime.now() - start_time),
        'linkage_check_results': linkage_check_results
    }

    browser.quit()
    return results


def __query_dom(browser, search_term, css_selector):
    if search_term in browser.find_element_by_css_selector(css_selector).get_attribute('data-icon'):
        return True
    else:
        return False


def main(logger, enable_caching, browser_screenshots):
    logger.debug("caching enabled = " + str(enable_caching))
    logger.debug("make browser screenshots = " + str(browser_screenshots))

    start_time = datetime.now()
    start_time_timestamp = time.time()

    all_ngr_records = get_all_ngr_records(logger, enable_caching)[:1]

    results = []
    for ngr_record in all_ngr_records:
        results.append(run_linkage_checker_with_selenium(logger, ngr_record, browser_screenshots))

    log_output(start_time, start_time_timestamp, datetime.now(), time.time(), results)


def log_output(start_time, start_time_timestamp, end_time, end_time_timestamp, results):
    # script_version = pkg_resources.require("linkage_checker")[0].version
    script_version = "0.1"
    duration = end_time - start_time
    print(
        json.dumps(
            {
                "linkage_checker_version": script_version,
                "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
                "start_time_timestamp": start_time_timestamp,
                "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
                "end_time_timestamp": end_time_timestamp,
                "total_duration": str(duration),
                "linkage_checker_endpoint": LINKAGE_CHECKER_URL,
                "results": results,
            },
            indent=4,
        )
    )
