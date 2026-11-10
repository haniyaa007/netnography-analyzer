from __future__ import annotations

import os

import requests

from ..models import Company, CollectorResult, Review
from ..utils import parse_date
from .base import Collector

SEARCH = "https://places.googleapis.com/v1/places:searchText"
DETAIL = "https://places.googleapis.com/v1/places/{pid}"


class GooglePlacesCollector(Collector):
    """Google reviews via the official Places API (New).
    Limitation: Google returns at most 5 'most relevant' reviews per place. For full history use a
    licensed provider (e.g. SerpApi / Outscraper) and feed the CSV in with --import-csv."""
    name = "google_reviews"
    requires_env = ["GOOGLE_PLACES_API_KEY"]

    def collect(self, company: Company, max_items: int) -> CollectorResult:
        key = os.environ["GOOGLE_PLACES_API_KEY"]
        r = requests.post(SEARCH, timeout=30, json={"textQuery": company.name}, headers={
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.websiteUri",
        })
        r.raise_for_status()
        places = r.json().get("places", [])
        if not places:
            return CollectorResult(self.name, status="no_data", note="No Google Place found")
        place = next((p for p in places if company.domain in (p.get("websiteUri") or "")), places[0])
        d = requests.get(DETAIL.format(pid=place["id"]), timeout=30, headers={
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": "id,displayName,rating,userRatingCount,reviews,googleMapsUri",
        })
        d.raise_for_status()
        d = d.json()
        out = []
        for rv in d.get("reviews", []):
            txt = (rv.get("text") or rv.get("originalText") or {}).get("text", "")
            out.append(Review(
                platform="google_reviews", text=txt, rating=rv.get("rating"),
                author=(rv.get("authorAttribution") or {}).get("displayName", ""),
                date=parse_date(rv.get("publishTime")), source_url=d.get("googleMapsUri", ""),
            ))
        profile = {"google_rating": d.get("rating"), "google_rating_count": d.get("userRatingCount"),
                   "google_place_name": (d.get("displayName") or {}).get("text")}
        return CollectorResult(self.name, out, profile, note="API returns max 5 reviews")
