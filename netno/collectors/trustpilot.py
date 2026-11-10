from __future__ import annotations

import json

from ..browser import launch
from ..config import SESSIONS_DIR
from ..models import Company, CollectorResult, Review
from ..utils import parse_date, polite_sleep
from .base import Collector


class TrustpilotCollector(Collector):
    """Reads the review JSON that Trustpilot embeds in each public page (__NEXT_DATA__).
    NOTE: Trustpilot's terms restrict automated access. Use for research at low volume,
    or use their official Business API if you own the profile."""
    name = "trustpilot"

    def collect(self, company: Company, max_items: int) -> CollectorResult:
        from playwright.sync_api import sync_playwright

        out, profile = [], {}
        pages = max(1, -(-max_items // 20))
        with sync_playwright() as p:
            ctx = launch(p, SESSIONS_DIR / "trustpilot", headless=not self.headed)
            try:
                page = ctx.new_page()
                for n in range(1, pages + 1):
                    url = f"https://www.trustpilot.com/review/{company.domain}?page={n}&sort=recency"
                    resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    if resp and resp.status == 404:
                        return CollectorResult(self.name, status="no_data",
                                               note=f"No Trustpilot profile for {company.domain}")
                    node = page.locator("script#__NEXT_DATA__")
                    if node.count() == 0:
                        return CollectorResult(self.name, out, profile, status="error" if not out else "ok",
                                               note="Page had no embedded data (CAPTCHA? retry with --headed)")
                    pp = json.loads(node.first.text_content()).get("props", {}).get("pageProps", {})
                    if n == 1:
                        bu = pp.get("businessUnit") or {}
                        nr = bu.get("numberOfReviews")
                        profile = {"trustpilot_score": bu.get("trustScore"),
                                   "trustpilot_total_reviews": nr.get("total") if isinstance(nr, dict) else nr,
                                   "trustpilot_name": bu.get("displayName")}
                    reviews = pp.get("reviews") or []
                    if not reviews:
                        break
                    for r in reviews:
                        out.append(Review(
                            platform="trustpilot", title=r.get("title") or "",
                            text=f"{r.get('title') or ''}. {r.get('text') or ''}",
                            rating=r.get("rating"), engagement=int(r.get("likes") or 0),
                            author=(r.get("consumer") or {}).get("displayName", ""),
                            date=parse_date((r.get("dates") or {}).get("publishedDate")),
                            source_url=f"https://www.trustpilot.com/reviews/{r.get('id')}",
                            extra={"company_replied": bool(r.get("reply")),
                                   "country": (r.get("consumer") or {}).get("countryCode")},
                        ))
                    polite_sleep(2, 4)
            finally:
                ctx.close()
        return CollectorResult(self.name, out[:max_items], profile)
