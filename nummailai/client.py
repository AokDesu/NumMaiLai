from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
import urllib3
import requests

from nummailai.models import OutageEvent
from nummailai.parser import parse_raw_event

# Suppress InsecureRequestWarning if MWA has SSL certificate validation warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

MWA_SEARCH_URL = (
    "https://gisonline.mwa.co.th/GIS1125/SRC/src/06-Map%20MWA/rest/services/content-proxy-search.php"
)
MWA_FALLBACK_URL = (
    "https://gisonline.mwa.co.th/GIS1125/SRC/src/06-Map%20MWA/rest/services/content-proxy.php"
)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 NumMaiLai/1.0"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://gisonline.mwa.co.th/GIS1125/index-desktop.php",
}


class MWAClient:
    """Client to query real-time water outages and maintenance from MWA GIS."""

    def __init__(self, timeout: int = 15, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_raw_events(
        self,
        branch_param: str = "",
        start_param: str = "",
        finish_param: str = "",
    ) -> List[Dict[str, Any]]:
        """Fetch raw JSON array of events from MWA API endpoint."""
        params = {
            "branch_param": branch_param,
            "start_param": start_param,
            "finish_param": finish_param,
        }

        urls_to_try = [MWA_SEARCH_URL, MWA_FALLBACK_URL]
        last_exception: Optional[Exception] = None

        for url in urls_to_try:
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.debug("Fetching MWA data from %s (attempt %d/%d)", url, attempt, self.max_retries)
                    # verify=False ensures connectivity if MWA server SSL certificate has chain issues
                    response = self.session.get(
                        url,
                        params=params,
                        timeout=self.timeout,
                        verify=False,
                    )
                    response.raise_for_status()

                    data = response.json()
                    if isinstance(data, list):
                        logger.info("Successfully fetched %d events from MWA.", len(data))
                        return data
                    elif isinstance(data, dict):
                        # Some endpoints wrap in an object
                        items = data.get("data") or data.get("features") or data.get("results") or []
                        return items
                    return []
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        "Attempt %d/%d failed fetching from %s: %s",
                        attempt,
                        self.max_retries,
                        url,
                        e,
                    )
                    if attempt < self.max_retries:
                        time.sleep(1.5 * attempt)

        if last_exception:
            logger.error("All MWA endpoints failed. Last error: %s", last_exception)
            raise last_exception

        return []

    def fetch_events(
        self,
        branch_param: str = "",
        start_param: str = "",
        finish_param: str = "",
    ) -> List[OutageEvent]:
        """Fetch and parse all current outage events into OutageEvent models."""
        raw_items = self.fetch_raw_events(
            branch_param=branch_param,
            start_param=start_param,
            finish_param=finish_param,
        )
        events: List[OutageEvent] = []
        for item in raw_items:
            try:
                event = parse_raw_event(item)
                events.append(event)
            except Exception as e:
                logger.warning("Failed to parse MWA item %s: %s", item, e)
        return events
