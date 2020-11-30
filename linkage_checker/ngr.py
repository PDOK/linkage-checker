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

CONFORMANCE_1089_2010_TITLE = "VERORDENING (EU) Nr. 1089/2010 VAN DE COMMISSIE van 23 november 2010 ter uitvoering van Richtlijn 2007/2/EG van het Europees Parlement en de Raad betreffende de interoperabiliteit van verzamelingen ruimtelijke gegevens en van diensten met betrekking tot ruimtelijke gegevens"
CONFORMANCE_INSPIRE_DATA_SPEC_TITLE = "INSPIRE Data Specification on"

logger = logging.getLogger(__name__)

def get_all_ngr_records(enable_caching):
    # if there is no cache file or it is expired, create it. otherwise read the cache file
    if not os.path.isfile(CACHE_FILENAME) or cache_is_expired() or not enable_caching:
        logger.debug("downloading ngr record data...")
        ngr_dataset_records = __get_all_ngr_records("type='dataset'")
        ngr_service_records = __get_all_ngr_records(
            "type='service'+AND+organisationName='Beheer+PDOK'"
        )
        __enrich_ngr_service_records(ngr_service_records)

        ngr_records_to_remove = []
        for ngr_record in ngr_dataset_records:
            record_info = get_ngr_record_info(
                ngr_record["uuid"], ngr_service_records
            )
            if len(record_info) == 1:
                warning = "only one PDOK service is coupled to datasets {}".format(ngr_record["title"])
                logger.warning(warning)
            if len(record_info) != 2:
                ngr_records_to_remove.append(ngr_record)
            else:
                ngr_record.update(record_info)
                __enrich_ngr_dataset_record(ngr_record)

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
    __validate_consistancy(ngr_dataset_records)
    return ngr_dataset_records

def __validate_consistancy(ngr_dataset_records):
    for ngr_dataset_record in ngr_dataset_records:
        validatie_identifiers(ngr_dataset_record, ngr_dataset_record["view_service"])
        validatie_identifiers(ngr_dataset_record, ngr_dataset_record["download_service"])


def validatie_identifiers(ngr_dataset_record, ngr_service_record):
    if not ngr_dataset_record["identifier"] or ngr_dataset_record["identifier"].startswith("\n"):
        warning = "no identifier was resolved for dataset '{}'. link: https://nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search#/metadata/{}.".format(
            ngr_dataset_record["title"], ngr_dataset_record["uuid"])
        logger.warning(warning)
    else:
        for coupled_data in ngr_service_record["coupled_datasets"]:
            if coupled_data["metadata_uuid"] == ngr_dataset_record["uuid"] and coupled_data["identifier"] != \
                    ngr_dataset_record["identifier"]:
                warning = "mismatch in identifier (expected: {}, actual: {}) in NGR for dataset '{}' and service '{}', service link: https://nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search#/metadata/{}".format(
                    ngr_dataset_record["identifier"], coupled_data["identifier"], ngr_dataset_record["title"],
                    ngr_service_record["title"], ngr_service_record["uuid"])
                logger.warning(warning)


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
        logger.info("fetching records_base_url: " + records_base_url)
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
            title = temp_record.find("dc:title", NAMESPACE_PREFIXES).text
            identifier = temp_record.find("dc:identifier", NAMESPACE_PREFIXES).text

            temp_record_result = {
                "uuid": identifier,
                "title": title,
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
        service_uuid = item.find("id").text
        ngr_service_record = __find_in_service_records(service_uuid, ngr_service_records)
        if ngr_service_record is not None:
            if ngr_service_record["service_type"] == "view":
                result["view_service"] = ngr_service_record
            if ngr_service_record["service_type"] == "download":
                result["download_service"] = ngr_service_record
    return result

def __enrich_ngr_dataset_record(ngr_data_record):
    response = __get_full_ngr_record(ngr_data_record["uuid"])
    document = ET.fromstring(response.content)

    identifier_element = document.find(
        ".//gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gmx:Anchor",
        NAMESPACE_PREFIXES,
    )
    if identifier_element is None:
        identifier_element = document.find(
            ".//gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code",
            NAMESPACE_PREFIXES,
        )
    else:
        ngr_data_record["identifier_namespace"] = identifier_element.get("{{{}}}href".format(NAMESPACE_PREFIXES["xlink"]))
    ngr_data_record["identifier"] = identifier_element.text

    conform_1089_2010_pass = document.find(
        './/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:specification/gmd:CI_Citation/gmd:title/*[.="{}"]/../../../../gmd:pass/gco:Boolean'.format(
            CONFORMANCE_1089_2010_TITLE),
        NAMESPACE_PREFIXES)
    conform_1089_2010 = (conform_1089_2010_pass is not None and conform_1089_2010_pass.text == 'true')
    ngr_data_record["harmonized"] = conform_1089_2010

    conformance_titles = document.findall(".//gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:specification/gmd:CI_Citation/gmd:title/*",
                     NAMESPACE_PREFIXES)
    for conformance_title in conformance_titles:
        if conformance_title.text is not None and CONFORMANCE_INSPIRE_DATA_SPEC_TITLE in conformance_title.text:
            ngr_data_record["conformance_data_spec"] = conformance_title.text
            break
        else:
            ref = conformance_title.get("{{{}}}href".format(NAMESPACE_PREFIXES["xlink"]))
            if ref is not None and ref.startswith("http://inspire.ec.europa.eu/id/document/tg"):
                ngr_data_record["conformance_data_spec"] = conformance_title.text
                break


    inspire_theme_element = document.find(".//gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:thesaurusName/gmd:CI_Citation/gmd:title[gmx:Anchor='GEMET - INSPIRE themes, version 1.0' ]/../../../gmd:keyword/gmx:Anchor", NAMESPACE_PREFIXES)
    if inspire_theme_element is not None:
        ngr_data_record["inspire_keyword_url"] = inspire_theme_element.attrib["{{{}}}href".format(NAMESPACE_PREFIXES["xlink"])]
        ngr_data_record["inspire_keyword"] = inspire_theme_element.text


def __find_in_service_records(uuid, ngr_service_records):
    for service_record in ngr_service_records:
        if service_record["uuid"] == uuid:
            return service_record
    return None


def __enrich_ngr_service_records(ngr_service_records):
    for ngr_record in ngr_service_records:
        response = __get_full_ngr_record(ngr_record["uuid"])
        document = ET.fromstring(response.content)

        service_access_point = document.find(
            ".//gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:linkage/gmd:URL",
            NAMESPACE_PREFIXES,
        ).text
        service_type = document.find(
            ".//srv:SV_ServiceIdentification/srv:serviceType/gco:LocalName",
            NAMESPACE_PREFIXES,
        ).text

        ngr_record["coupled_datasets"] = []
        for operates_on in document.findall(".//srv:SV_ServiceIdentification/srv:operatesOn", NAMESPACE_PREFIXES):
            href = operates_on.get("{{{}}}href".format(NAMESPACE_PREFIXES["xlink"]))
            dataset_metadata_uuid = __get_request_parameter_value(href, "id").split("#", 1)[0]
            dataset_identifier = operates_on.get("uuidref")
            dataset = {"metadata_uuid": dataset_metadata_uuid, "identifier": dataset_identifier}
            ngr_record["coupled_datasets"].append(dataset)

        ngr_record["service_type"] = service_type
        ngr_record["service_access_point"] = service_access_point
        if not __is_quality_conformance_met(document):
            warning = "not all quality conformances are met for service {} ref:https://nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search#/metadata/{}".format(ngr_record["title"], ngr_record["uuid"])
            logger.warning(warning)


def __get_full_ngr_record(uuid):
    record_info_base_url = "{}/srv/dut/csw?service=CSW&request=GetRecordById&version=2.0.2&outputSchema=http://www.isotc211.org/2005/gmd&elementSetName=full&id={}#MD_DataIdentification ".format(NGR_BASE_URL, uuid)
    logger.info("fetching record_info_base_url: " + record_info_base_url)
    response = requests.get(record_info_base_url, headers=REQUEST_HEADERS)
    return response


def __is_quality_conformance_met(document):
    for conformance_result in document.findall(".//gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:pass/gco:Boolean", NAMESPACE_PREFIXES):
        if conformance_result.text != "true":
            return False
    return True


def __get_request_parameter_value(url, parameter_name):
    if url is None:
        return ""
    request_parameters_part = url.split("?", 1)[1]
    request_parameters = request_parameters_part.split("&")
    for request_parameter in request_parameters:
        kvp = request_parameter.split("=", 1)
        if parameter_name == kvp[0]:
            return kvp[1]
    return ""
