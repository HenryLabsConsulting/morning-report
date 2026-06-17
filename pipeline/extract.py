"""Extraction.

Pulls each source over HTTP from the mock vendor host, with a date window and
basic retry. Swapping the host for a real vendor base URL and adding an auth
header is all it would take to point this at production systems.
"""

import time

import requests
from sources import SOURCES


def fetch(host: str, source, since: str, until: str, retries: int = 3) -> list[dict]:
    url = f"{host.rstrip('/')}{source.path}"
    params = {"since": since, "until": until}
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json().get(source.envelope, [])
        except requests.RequestException as err:
            last_err = err
            time.sleep(0.5 * attempt)
    raise RuntimeError(f"failed to fetch {source.name} after {retries} tries: {last_err}")


def extract_all(host: str, since: str, until: str) -> dict[str, list[dict]]:
    return {s.name: fetch(host, s, since, until) for s in SOURCES}
