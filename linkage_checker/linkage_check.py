import logging
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from linkage_checker.constants import LINKAGE_CHECKER_URL, BROWSER_SCREENSHOT_PATH, NGR_UUID_URL, TIMEOUT_SECONDS, \
    TIMEOUT_SECONDS_DEBUG_MODE

logger = logging.getLogger(__name__)

def query_dom(browser, search_term, css_selector):
    return search_term in browser.find_element_by_css_selector(
        css_selector
    ).get_attribute("data-icon")


def run_linkage_checker_with_selenium(
    ngr_record, browser_screenshots, remote_selenium_url, start_time, debug_mode
):
    logger.debug(
        'starting linkage check with dataset "'
        + ngr_record["title"]
        + '" (uuid_dataset = '
        + ngr_record["uuid"]
        + ")"
    )

    logger.debug("connecting to remote Firefox browser (in docker container)...")
    browser = webdriver.Remote(
        command_executor=remote_selenium_url,
        desired_capabilities=DesiredCapabilities.FIREFOX,
    )
    logger.debug("connected!")

    # this prevents some possible "element not interactable" exceptions
    # https://www.selenium.dev/docs/site/en/webdriver/waits/#implicit-wait
    browser.implicitly_wait(10)

    browser.get(LINKAGE_CHECKER_URL)
    logger.debug("webpage " + browser.current_url + " loaded")

    if browser_screenshots:
        browser.save_screenshot(BROWSER_SCREENSHOT_PATH)

    # accept coockies (if requested)
    #
    element = browser.find_element_by_css_selector("a.wt-link.cck-actions-button.ea_ignore")
    if element:
        element.click()
        browser.find_element_by_css_selector("div.cck-actions a.wt-link").click()

    if browser_screenshots:
        browser.save_screenshot(BROWSER_SCREENSHOT_PATH)

    # simulating webpage interaction
    # click on the "Check new metadata" button
    #
    browser.find_element_by_id("newMetadataBtn").click()
    # this second .click() ensures that the button is properly clicked (a single click is apparently not enough)
    browser.find_element_by_id("newMetadataBtn").click()
    if browser_screenshots:
        browser.save_screenshot(BROWSER_SCREENSHOT_PATH)

    # click on the three "URL to INSPIRE metadata" buttons
    element_present = expected_conditions.element_to_be_clickable(
        (By.CSS_SELECTOR, "#mdInputURL + label")
    )
    WebDriverWait(browser, 10, poll_frequency=1).until(element_present)
    browser.find_element_by_css_selector("#mdInputURL + label").click()
    browser.find_element_by_css_selector("#vwInputURL + label").click()
    browser.find_element_by_css_selector("#dwInputURL + label").click()
    if browser_screenshots:
        browser.save_screenshot(BROWSER_SCREENSHOT_PATH)

    # filling in the three textareas with the correct urls to nationaalgeoregister.nl
    browser.find_element_by_id("dataMetadata").send_keys(
        NGR_UUID_URL + ngr_record["uuid"]
    )
    browser.find_element_by_id("viewServiceMetadata").send_keys(
        NGR_UUID_URL + ngr_record["view_service"]["uuid"]
    )
    browser.find_element_by_id("downloadServiceMetadata").send_keys(
        NGR_UUID_URL + ngr_record["download_service"]["uuid"]
    )
    if browser_screenshots:
        browser.save_screenshot(BROWSER_SCREENSHOT_PATH)

    # click on the "Check Resources" button to start the linkage checker
    browser.find_element_by_id("checkLinkageBtn").click()
    if browser_screenshots:
        browser.save_screenshot(BROWSER_SCREENSHOT_PATH)

    logger.debug("linkage check started. waiting for results...")
    # https://pythonbasics.org/selenium-wait-for-page-to-load/
    # checking visibility of the resultsContainer element that indicates when the linkage checker is done
    element_present = expected_conditions.visibility_of_element_located(
        (By.ID, "resultsContainer")
    )
    # timeout_seconds = 1800  # = 0.5 hour, is hopefully enough time for the INSPIRE linkage checker doing its job and
    # delivering results?
    # poll_frequency=5 seconds. the INSPIRE linkage checker executes some ajax http requests every 5 seconds
    # to its backend to check if the linkage check is done, so a faster poll_frequency is not really useful
    try:
        WebDriverWait(browser, TIMEOUT_SECONDS if not debug_mode else TIMEOUT_SECONDS_DEBUG_MODE, poll_frequency=5).until(element_present)
    except TimeoutException:
        # if a TimeoutException happens, just move on (produces a negative test result)
        logger.debug(
            "TimeoutException with dataset: "
            + ngr_record["title"]
            + " (uuid_dataset = "
            + ngr_record["uuid"]
            + ")"
        )
        browser.quit()
        raise

    if browser_screenshots:
        browser.save_screenshot(BROWSER_SCREENSHOT_PATH)

    logger.debug("linkage check done. querying the DOM to retrieve results")
    linkage_check_results = {}

    # Linkage overview
    # -- View Service linkage
    linkage_check_results["view_service_linkage"] = query_dom(
        browser, "thumbs-up", "#resultsOverviewVwAssessment > svg:nth-child(1)"
    )
    # -- Download Service linkage
    linkage_check_results["download_service_linkage"] = query_dom(
        browser, "thumbs-up", "#resultsOverviewDwAssessment > svg:nth-child(1)"
    )

    # Main linkage aspects
    # -- Data Set metadata contains Unique Resource Identifier
    linkage_check_results[
        "data_set_metadata_contains_unique_resource_identifier"
    ] = query_dom(
        browser,
        "check-square",
        "#resultId_DATASET_METADATA_CONTAINS_UNIQUE_RESOURCE_IDENTIFIER > svg:nth-child(1)",
    )
    # -- Data Set metadata contains INSPIRE Spatial Data Theme
    linkage_check_results[
        "data_set_metadata_contains_inspire_spatial_data_theme"
    ] = query_dom(
        browser,
        "check-square",
        "#resultId_DATASET_METADATA_CONTAINS_INSPIRE_SPATIAL_DATA_THEME > svg:nth-child(1)",
    )
    # -- The View Service has been contacted
    linkage_check_results["the_view_service_has_been_contacted"] = query_dom(
        browser,
        "check-square",
        "#resultId_VIEW_SERVICE_HAS_BEEN_CONTACTED > svg:nth-child(1)",
    )
    # -- Linkage has been estabilished between the View Service and Data Set
    linkage_check_results[
        "linkage_has_been_estabilished_between_the_view_service_and_data_set"
    ] = query_dom(
        browser,
        "check-square",
        "#resultId_LINKAGE_FROM_VIEW_SERVICE_TO_DATASET_HAS_BEEN_FOUND > svg:nth-child(1)",
    )
    # -- The Download Service has been contacted
    linkage_check_results["the_download_service_has_been_contacted"] = query_dom(
        browser,
        "check-square",
        "#resultId_DOWNLOAD_SERVICE_HAS_BEEN_CONTACTED > svg:nth-child(1)",
    )
    # -- Linkage has been estabilished between the Download Service and Data Set
    linkage_check_results[
        "linkage_has_been_estabilished_between_the_download_service_and_data_set"
    ] = query_dom(
        browser,
        "check-square",
        "#resultId_LINKAGE_FROM_DOWNLOAD_SERVICE_TO_DATASET_HAS_BEEN_FOUND > svg:nth-child(1)",
    )
    # -- A Download link has been determined
    linkage_check_results["a_download_link_has_been_determined"] = query_dom(
        browser,
        "check-square",
        "#resultId_DOWNLOAD_LINK_HAS_BEEN_DETERMINED > svg:nth-child(1)",
    )

    # Linkage aspects related to the INSPIRE Geoportal
    # -- Data Set metadata exists in the INSPIRE Geoportal
    linkage_check_results[
        "data_set_metadata_exists_in_the_inspire_geoportal"
    ] = query_dom(
        browser,
        "check-square",
        "#resultId_DATASET_METADATA_EXISTS_IN_INSPIRE_GEOPORTAL > svg:nth-child(1)",
    )
    # -- View Service metadata exists in the INSPIRE Geoportal
    linkage_check_results[
        "view_service_metadata_exists_in_the_inspire_geoportal"
    ] = query_dom(
        browser,
        "check-square",
        "#resultId_VIEW_SERVICE_METADATA_EXISTS_IN_INSPIRE_GEOPORTAL > svg:nth-child(1)",
    )
    # -- Download Service metadata exists in the INSPIRE Geoportal
    linkage_check_results[
        "download_service_metadata_exists_in_the_inspire_geoportal"
    ] = query_dom(
        browser,
        "check-square",
        "#resultId_DOWNLOAD_SERVICE_METADATA_EXISTS_IN_INSPIRE_GEOPORTAL > svg:nth-child(1)",
    )

    # get the evaluation report url
    evaluation_report_url = browser.find_element_by_id(
        "resourceEvalReport"
    ).get_attribute("href")

    logger.debug("done querying DOM retrieving linkage check results")

    # storing ngr record information
    results = {
        "dataset_title": ngr_record["title"],
        "status": "PASSED" if all(linkage_check_results.values()) else "FAILED",
        "error": None,
        "dataset_uuid": ngr_record["uuid"],
        "endpoint_download_service": NGR_UUID_URL + ngr_record["download_service"]["uuid"],
        "endpoint_view_service": NGR_UUID_URL + ngr_record["view_service"]["uuid"],
        "endpoint_meta_data": NGR_UUID_URL + ngr_record["uuid"],
        "duration": str(datetime.now() - start_time),
        "evaluation_report_url": evaluation_report_url,
        "linkage_check_results": linkage_check_results,
    }

    browser.quit()
    return results
