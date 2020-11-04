NGR_BASE_URL = "https://nationaalgeoregister.nl/geonetwork"
NGR_UUID_URL = "https://www.nationaalgeoregister.nl/geonetwork/srv/dut/xml.metadata.get?uuid="

CACHE_FILENAME = "../ngr_records_cache.json"
CACHE_EXPIRATION_IN_SECONDS = 86400  # is 1 day

REQUEST_HEADERS = {
    'User-Agent': 'pdok.nl (linkage-checker)'
}

NAMESPACE_PREFIXES = {
    'csw': 'http://www.opengis.net/cat/csw/2.0.2',
    'gmd': 'http://www.isotc211.org/2005/gmd',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'gco': 'http://www.isotc211.org/2005/gco',
    'gmx': 'http://www.isotc211.org/2005/gmx',
    'ows': 'http://www.opengis.net/ows',
}

LINKAGE_CHECKER_URL = "https://inspire-geoportal.ec.europa.eu/linkagechecker.html"

BROWSER_SCREENSHOT_PATH = "../browser-screenshot.png"

REMOTE_WEBDRIVER_CONNECTION_URL = "http://127.0.0.1:4444/wd/hub"
