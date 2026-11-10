from __future__ import annotations

import os

from ..models import Company, CollectorResult
from ..utils import http_get
from .base import Collector

BASE = "https://api.crunchbase.com/api/v4"
FIELDS = ("short_description,founded_on,num_employees_enum,funding_total,last_funding_type,"
          "last_funding_at,categories,location_identifiers,operating_status,rank_org,website_url")


class CrunchbaseCollector(Collector):
    """Crunchbase has no consumer reviews - this adds company context (funding, size, category)
    to the Company_Profile sheet. Requires a Crunchbase API plan."""
    name = "crunchbase"
    requires_env = ["CRUNCHBASE_API_KEY"]

    def collect(self, company: Company, max_items: int) -> CollectorResult:
        key = os.environ["CRUNCHBASE_API_KEY"]
        ac = http_get(f"{BASE}/autocompletes", params={
            "query": company.name, "collection_ids": "organizations", "limit": 5, "user_key": key}).json()
        ents = ac.get("entities", [])
        if not ents:
            return CollectorResult(self.name, status="no_data", note="Organization not found")
        pick = next((e for e in ents if company.slug.replace("-", "") in
                     e["identifier"]["permalink"].replace("-", "")), ents[0])
        permalink = pick["identifier"]["permalink"]
        props = http_get(f"{BASE}/entities/organizations/{permalink}",
                         params={"field_ids": FIELDS, "user_key": key}).json().get("properties", {})
        profile = {
            "crunchbase_url": f"https://www.crunchbase.com/organization/{permalink}",
            "cb_description": props.get("short_description"),
            "cb_founded_on": props.get("founded_on"),
            "cb_employees": props.get("num_employees_enum"),
            "cb_funding_total_usd": (props.get("funding_total") or {}).get("value_usd"),
            "cb_last_funding_type": props.get("last_funding_type"),
            "cb_last_funding_at": props.get("last_funding_at"),
            "cb_categories": ", ".join(c.get("value", "") for c in props.get("categories", []) or []),
            "cb_status": props.get("operating_status"),
            "cb_rank": props.get("rank_org"),
        }
        return CollectorResult(self.name, [], profile)
