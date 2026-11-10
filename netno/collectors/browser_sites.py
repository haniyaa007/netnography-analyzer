"""Logged-in browser collector (LinkedIn, Instagram, X, Facebook, G2, Capterra, Glassdoor, Yelp, ...).

How "sign in" works: `python main.py login <site>` opens a REAL browser window. YOU type your
credentials (and 2FA) there. We never see or store your password - Playwright only keeps the
resulting session cookies in .sessions/<site>/ on your machine (git-ignored).

Extraction is generic and best-effort: JSON-LD `Review` objects, schema.org `itemprop=reviewBody`,
plus the CSS selectors below. Social sites change their markup constantly - when a site returns
nothing, edit its `selectors` here (right-click > Inspect in the browser).

Compliance: LinkedIn, Instagram, X and Facebook prohibit automated collection in their terms and
may restrict accounts. Use a research account, low volume, and read the README before enabling.
"""
from __future__ import annotations

import json
from urllib.parse import quote_plus, urljoin

from ..browser import launch
from ..config import SESSIONS_DIR
from ..models import Company, CollectorResult, Review
from ..utils import log, parse_date, polite_sleep
from .base import Collector

GENERIC_REVIEW_SELECTORS = ["[itemprop='reviewBody']", "[data-testid*='review'] p", "article p"]

SITES: dict[str, dict] = {
    # ---- social networks (kind=post; texts must mention the brand to be kept) ----
    "linkedin": dict(kind="post", login_url="https://www.linkedin.com/login", needs_login=True,
        urls=["https://www.linkedin.com/search/results/content/?keywords={q}&sortBy=%22date_posted%22"],
        selectors=[".update-components-text", ".feed-shared-update-v2__description", "span.break-words"]),
    "instagram": dict(kind="post", login_url="https://www.instagram.com/accounts/login/", needs_login=True,
        urls=["https://www.instagram.com/explore/tags/{tag}/"],
        selectors=["article h1", "article ul span[dir='auto']", "span[dir='auto']"]),
    "x": dict(kind="post", login_url="https://x.com/i/flow/login", needs_login=True,
        urls=["https://x.com/search?q={q}&f=live"],
        selectors=["article[data-testid='tweet'] div[data-testid='tweetText']"]),
    "facebook": dict(kind="post", login_url="https://www.facebook.com/login", needs_login=True,
        urls=["https://www.facebook.com/search/posts/?q={q}"],
        selectors=["div[data-ad-preview='message']", "div[role='article'] div[dir='auto']"]),
    # ---- review / directory sites (kind=review) ----
    "glassdoor": dict(kind="review", login_url="https://www.glassdoor.com/profile/login_input.htm",
        needs_login=True, urls=["https://www.glassdoor.com/Search/results.htm?keyword={q}"],
        result_link="a[href*='/Reviews/']", selectors=GENERIC_REVIEW_SELECTORS),
    "g2": dict(kind="review", login_url="https://www.g2.com/login",
        urls=["https://www.g2.com/search?query={q}"], result_link="a[href*='/products/']",
        selectors=GENERIC_REVIEW_SELECTORS),
    "capterra": dict(kind="review", urls=["https://www.capterra.com/search/?query={q}"],
        result_link="a[href*='/p/']", selectors=GENERIC_REVIEW_SELECTORS),
    "yelp": dict(kind="review", urls=["https://www.yelp.com/search?find_desc={q}"],
        result_link="a[href*='/biz/']", selectors=["p[class*='comment'] span", *GENERIC_REVIEW_SELECTORS]),
    "sitejabber": dict(kind="review", urls=["https://www.sitejabber.com/reviews/{domain}"],
        selectors=GENERIC_REVIEW_SELECTORS),
    "bbb": dict(kind="review", urls=["https://www.bbb.org/search?find_text={q}"],
        result_link="a[href*='/profile/']", selectors=GENERIC_REVIEW_SELECTORS),
    "producthunt": dict(kind="review", urls=["https://www.producthunt.com/search?q={q}"],
        result_link="a[href*='/products/']", selectors=GENERIC_REVIEW_SELECTORS),
    # Add your own: copy a block, change the URL(s) and selectors.
}

LOGIN_WALL = ("login", "signin", "authwall", "checkpoint", "uas/login", "accounts/login")


def interactive_login(key: str) -> None:
    from playwright.sync_api import sync_playwright
    cfg = SITES[key]
    start = cfg.get("login_url") or cfg["urls"][0].split("{")[0]
    with sync_playwright() as p:
        ctx = launch(p, SESSIONS_DIR / key, headless=False, viewport=None)
        page = ctx.new_page()
        page.goto(start)
        print(f"\nA browser window opened for {key}. Log in manually (incl. 2FA), then come back here.")
        input("Press ENTER once you are fully logged in... ")
        ctx.close()
    print(f"Session saved to .sessions/{key}/")


_JS_TEXTS = """(sels) => { const out = [];
  for (const s of sels) document.querySelectorAll(s).forEach(e => {
    const t = (e.innerText || '').trim(); if (t.length > 40) out.push(t); });
  return out; }"""
_JS_LD = """() => [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => s.textContent)"""


def _walk_ld(node, found):
    if isinstance(node, list):
        for n in node:
            _walk_ld(n, found)
    elif isinstance(node, dict):
        t = node.get("@type")
        if t == "Review" or (isinstance(t, list) and "Review" in t):
            found.append(node)
        for v in node.values():
            if isinstance(v, (list, dict)):
                _walk_ld(v, found)


class BrowserSiteCollector(Collector):
    def __init__(self, key: str, headed: bool = False):
        super().__init__(headed)
        self.key, self.name, self.cfg = key, key, SITES[key]

    def collect(self, company: Company, max_items: int) -> CollectorResult:
        from playwright.sync_api import sync_playwright

        sess = SESSIONS_DIR / self.key
        logged_in = sess.exists() and any(sess.glob("*"))
        if self.cfg.get("needs_login") and not logged_in:
            return CollectorResult(self.name, status="skipped",
                                   note=f"Not logged in. Run: python main.py login {self.key}")
        out, notes = [], []
        fmt = dict(q=quote_plus(company.name), domain=company.domain,
                   tag=company.slug.replace("-", ""), slug=company.slug)
        with sync_playwright() as p:
            ctx = launch(p, sess, headless=not self.headed)
            try:
                page = ctx.new_page()
                for tpl in self.cfg["urls"]:
                    url = tpl.format(**fmt)
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    except Exception as e:
                        notes.append(f"load failed: {e.__class__.__name__}")
                        continue
                    polite_sleep(2, 4)
                    if any(k in page.url for k in LOGIN_WALL):
                        notes.append(f"login wall - run: python main.py login {self.key}")
                        continue
                    if self.cfg.get("result_link"):
                        link = page.locator(self.cfg["result_link"]).first
                        if link.count():
                            page.goto(urljoin(page.url, link.get_attribute("href")),
                                      wait_until="domcontentloaded", timeout=45000)
                            polite_sleep(2, 4)
                    for _ in range(8):  # scroll to trigger lazy loading
                        page.mouse.wheel(0, 2500)
                        polite_sleep(0.8, 1.6)
                    out += self._extract(page, company)
                    if len(out) >= max_items:
                        break
            finally:
                ctx.close()
        # dedupe
        seen, uniq = set(), []
        for r in out:
            k = r.text[:150]
            if k not in seen:
                seen.add(k)
                uniq.append(r)
        status = "ok" if uniq else "no_data"
        return CollectorResult(self.name, uniq[:max_items], status=status, note="; ".join(notes))

    def _extract(self, page, company: Company) -> list[Review]:
        out, url = [], page.url
        kind = self.cfg["kind"]
        # 1) structured data (most review sites publish schema.org Review JSON-LD)
        try:
            for blob in page.evaluate(_JS_LD):
                found = []
                try:
                    _walk_ld(json.loads(blob), found)
                except json.JSONDecodeError:
                    continue
                for r in found:
                    body = r.get("reviewBody") or r.get("description") or ""
                    if len(body) < 15:
                        continue
                    rating = r.get("reviewRating") or {}
                    author = r.get("author")
                    out.append(Review(
                        platform=self.name, content_type="review",
                        title=r.get("name") or "", text=f"{r.get('name') or ''}. {body}",
                        rating=float(rating["ratingValue"]) if isinstance(rating, dict) and rating.get("ratingValue") else None,
                        author=author.get("name", "") if isinstance(author, dict) else str(author or ""),
                        date=parse_date(r.get("datePublished")), source_url=url))
        except Exception:
            pass
        # 2) CSS selectors
        try:
            texts = page.evaluate(_JS_TEXTS, self.cfg["selectors"])
        except Exception:
            texts = []
        brand = company.name.lower()
        for t in texts:
            if kind == "post" and brand not in t.lower() and company.domain not in t.lower():
                continue   # drop UI chrome / unrelated posts
            out.append(Review(platform=self.name, content_type=kind, text=t, source_url=url))
        return out
