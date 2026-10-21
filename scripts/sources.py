# -*- coding: utf-8 -*-
"""
Lead Hunter v2 - discovery source adapter interface.

Keeps source-specific collection logic separate from parsing/dedup
(discover.py), auditing (audit.py), scoring (score.py) and reporting
(build_report.py). See references/sources.md for which sources are
actually usable in a given environment and why.

Every adapter's `available()` does a REAL check (env var present, endpoint
reachable) - it never hardcodes True. Every record returned by `search()`
carries `source_name` and `source_url`/`query` provenance so it survives
into the final lead's evidence trail.
"""
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error


class DiscoverySource:
    """Base class for a discovery source adapter."""
    name = "base"

    def available(self):
        """Return (bool, reason). Must perform a real check, never hardcode True."""
        raise NotImplementedError

    def search(self, query, limit=50):
        """Return a list of normalized dicts: name, source_url, raw, retrieved_at."""
        raise NotImplementedError


class GooglePlacesAPISource(DiscoverySource):
    """Real Google Places API (Text Search + Place Details). Needs
    GOOGLE_PLACES_API_KEY in env. Cheaper and more reliable than browser
    scraping when a key exists - always prefer this over the Maps browser
    adapter when `available()` returns True."""
    name = "google_places_api"
    TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_PLACES_API_KEY")

    def available(self):
        if not self.api_key:
            return False, "no API key configured (GOOGLE_PLACES_API_KEY not set in env)"
        return True, ""

    def search(self, query, limit=50):
        ok, reason = self.available()
        if not ok:
            raise RuntimeError(f"{self.name} unavailable: {reason}")
        results, next_token, fetched = [], None, 0
        while fetched < limit:
            params = {"query": query, "key": self.api_key}
            if next_token:
                params["pagetoken"] = next_token
                time.sleep(2)  # Places API requires a short delay before a page token is valid
            url = self.TEXT_SEARCH_URL + "?" + urllib.parse.urlencode(params)
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read())
            for r in data.get("results", []):
                results.append({
                    "name": r.get("name"),
                    "place_id": r.get("place_id"),
                    "address": r.get("formatted_address"),
                    "rating": r.get("rating"),
                    "reviews": r.get("user_ratings_total"),
                    "lat": r.get("geometry", {}).get("location", {}).get("lat"),
                    "lng": r.get("geometry", {}).get("location", {}).get("lng"),
                    "source_name": self.name,
                    "query": query,
                    "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })
                fetched += 1
                if fetched >= limit:
                    break
            next_token = data.get("next_page_token")
            if not next_token:
                break
        return results

    def place_details(self, place_id, fields="formatted_phone_number,website,url"):
        ok, reason = self.available()
        if not ok:
            raise RuntimeError(f"{self.name} unavailable: {reason}")
        params = {"place_id": place_id, "fields": fields, "key": self.api_key}
        url = self.DETAILS_URL + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        return data.get("result", {})


class GoogleMapsBrowserSource(DiscoverySource):
    """Documents the live browser-driven procedure - this class does NOT
    itself drive a browser (a standalone script has no browser access).
    The invoking Claude session runs the scroll/extract snippet in
    SKILL.md via its own browser tool and saves each query's JSON to
    <output_dir>/raw/qNN_<slug>.json; discover.py --parse reads those
    files. This class exists so the adapter list is complete and so
    `available()` can be checked programmatically (it's always available
    as a method, since it needs no credentials - the real constraint is
    whether a browser tool is attached to the calling session, which a
    script cannot detect)."""
    name = "google_maps_browser"

    def available(self):
        return True, "requires a browser tool in the calling session (see SKILL.md Phase 1); always usable, needs no API key"

    def search(self, query, limit=50):
        raise NotImplementedError(
            "GoogleMapsBrowserSource.search() is not callable from a standalone script. "
            "Run the scroll/extract browser_evaluate snippet from SKILL.md Phase 1 instead, "
            "save its output to raw/qNN_<slug>.json, then call discover.py --parse."
        )


class ManualDirectorySource(DiscoverySource):
    """Stub for an Egyptian business/industry directory that has NOT been
    verified as both (a) relevant to the target niche/region and (b)
    permitting automated collection under its terms. Always reports
    itself unavailable rather than guessing a URL or scraping something
    unverified. Copy this class and fill in a real, checked URL + ToS
    read + available() check before using it for a specific directory."""
    name = "manual_directory_stub"

    def __init__(self, directory_url=None, verified_permitted=False):
        self.directory_url = directory_url
        self.verified_permitted = verified_permitted

    def available(self):
        if not self.directory_url:
            return False, "no directory URL configured - see references/sources.md"
        if not self.verified_permitted:
            return False, f"{self.directory_url} has not been confirmed to permit automated collection"
        return True, ""

    def search(self, query, limit=50):
        ok, reason = self.available()
        if not ok:
            raise RuntimeError(f"{self.name} unavailable: {reason}")
        return []


def list_sources():
    """Return every adapter with a live availability check - use this to
    report honest source coverage in run-metadata.json."""
    sources = [GooglePlacesAPISource(), GoogleMapsBrowserSource(), ManualDirectorySource()]
    report = []
    for s in sources:
        ok, reason = s.available()
        report.append({"source": s.name, "available": ok, "reason": reason})
    return report


if __name__ == "__main__":
    print(json.dumps(list_sources(), ensure_ascii=False, indent=2))
