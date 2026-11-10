from __future__ import annotations

import os
from datetime import datetime, timezone

from ..models import Company, CollectorResult, Review
from .base import Collector


class RedditCollector(Collector):
    """Official Reddit API via PRAW. Searches all subreddits for the brand + domain."""
    name = "reddit"
    requires_env = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"]

    def collect(self, company: Company, max_items: int) -> CollectorResult:
        import praw

        kw = dict(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
            user_agent=os.getenv("REDDIT_USER_AGENT") or "netnography-analyzer/0.1",
        )
        if os.getenv("REDDIT_USERNAME") and os.getenv("REDDIT_PASSWORD"):
            kw.update(username=os.environ["REDDIT_USERNAME"], password=os.environ["REDDIT_PASSWORD"])
        reddit = praw.Reddit(**kw)

        out, seen = [], set()
        for q in (f'"{company.name}"', company.domain):
            for s in reddit.subreddit("all").search(q, sort="relevance", time_filter="all", limit=max_items):
                if s.id in seen:
                    continue
                seen.add(s.id)
                out.append(Review(
                    platform="reddit", content_type="post", title=s.title,
                    text=f"{s.title}. {s.selftext or ''}", author=str(s.author or "[deleted]"),
                    date=datetime.fromtimestamp(s.created_utc, tz=timezone.utc),
                    engagement=int(s.score), source_url=f"https://reddit.com{s.permalink}",
                    extra={"subreddit": s.subreddit.display_name, "num_comments": s.num_comments},
                ))
                try:
                    s.comments.replace_more(limit=0)
                    for c in list(s.comments)[:8]:
                        out.append(Review(
                            platform="reddit", content_type="comment", title=s.title, text=c.body,
                            author=str(c.author or "[deleted]"),
                            date=datetime.fromtimestamp(c.created_utc, tz=timezone.utc),
                            engagement=int(c.score), source_url=f"https://reddit.com{c.permalink}",
                            extra={"subreddit": s.subreddit.display_name},
                        ))
                except Exception:
                    pass
                if len(out) >= max_items * 4:
                    break
        return CollectorResult(self.name, out, note=f"{len(seen)} threads")
