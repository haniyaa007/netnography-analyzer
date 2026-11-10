"""Free / key-light sources: Hacker News, YouTube comments, Google News RSS."""
from __future__ import annotations

import os
from urllib.parse import quote_plus

import requests

from ..models import Company, CollectorResult, Review
from ..utils import clean_text, http_get, parse_date
from .base import Collector


class HackerNewsCollector(Collector):
    name = "hackernews"

    def collect(self, company: Company, max_items: int) -> CollectorResult:
        out, seen = [], set()
        for q in {company.name, company.domain}:
            for tag in ("story", "comment"):
                data = http_get("https://hn.algolia.com/api/v1/search_by_date", params={
                    "query": f'"{q}"', "tags": tag, "hitsPerPage": min(100, max_items)}).json()
                for h in data.get("hits", []):
                    if h["objectID"] in seen:
                        continue
                    seen.add(h["objectID"])
                    body = h.get("comment_text") or h.get("story_text") or ""
                    out.append(Review(
                        platform="hackernews", content_type="comment" if tag == "comment" else "post",
                        title=h.get("title") or h.get("story_title") or "",
                        text=f"{h.get('title') or ''}. {clean_text(body)}", author=h.get("author", ""),
                        date=parse_date(h.get("created_at")), engagement=int(h.get("points") or 0),
                        source_url=f"https://news.ycombinator.com/item?id={h['objectID']}"))
        return CollectorResult(self.name, out)


class YouTubeCollector(Collector):
    name = "youtube"
    requires_env = ["YOUTUBE_API_KEY"]

    def collect(self, company: Company, max_items: int) -> CollectorResult:
        key = os.environ["YOUTUBE_API_KEY"]
        s = requests.get("https://www.googleapis.com/youtube/v3/search", timeout=30, params={
            "part": "snippet", "q": f"{company.name} review", "type": "video",
            "maxResults": 10, "key": key}).json()
        out = []
        for item in s.get("items", []):
            vid, sn = item["id"]["videoId"], item["snippet"]
            url = f"https://www.youtube.com/watch?v={vid}"
            out.append(Review(platform="youtube", content_type="video", title=sn["title"],
                              text=f"{sn['title']}. {sn.get('description', '')}", author=sn["channelTitle"],
                              date=parse_date(sn["publishedAt"]), source_url=url))
            r = requests.get("https://www.googleapis.com/youtube/v3/commentThreads", timeout=30, params={
                "part": "snippet", "videoId": vid, "maxResults": 50, "order": "relevance",
                "textFormat": "plainText", "key": key})
            if r.status_code != 200:   # comments disabled etc.
                continue
            for c in r.json().get("items", []):
                top = c["snippet"]["topLevelComment"]["snippet"]
                out.append(Review(platform="youtube", content_type="comment", title=sn["title"],
                                  text=top["textDisplay"], author=top["authorDisplayName"],
                                  date=parse_date(top["publishedAt"]), engagement=int(top.get("likeCount", 0)),
                                  source_url=url))
            if len(out) >= max_items:
                break
        return CollectorResult(self.name, out[:max_items * 2])


class NewsCollector(Collector):
    """Press coverage via Google News RSS - gives the 'official/media discourse' to contrast with users."""
    name = "news"

    def collect(self, company: Company, max_items: int) -> CollectorResult:
        import feedparser
        feed = feedparser.parse(f"https://news.google.com/rss/search?q={quote_plus(chr(34) + company.name + chr(34))}")
        out = [Review(platform="news", content_type="article", title=e.get("title", ""),
                      text=f"{e.get('title', '')}. {clean_text(e.get('summary', ''))}",
                      author=(e.get("source") or {}).get("title", ""), date=parse_date(e.get("published")),
                      source_url=e.get("link", "")) for e in feed.entries[:max_items]]
        return CollectorResult(self.name, out)
