from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse


def extract_domain(url: str) -> str:
    if "//" not in url:
        url = "https://" + url
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


@dataclass
class Company:
    name: str
    website: str

    @property
    def domain(self) -> str:
        return extract_domain(self.website)

    @property
    def slug(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")


@dataclass
class Review:
    """One unit of discourse: a review, post, comment, article or video."""
    platform: str
    text: str
    source_url: str = ""
    author: str = ""
    date: datetime | None = None
    rating: float | None = None        # normalised to a 1-5 scale when the platform has stars
    title: str = ""
    engagement: int = 0                # likes / upvotes / points
    content_type: str = "review"       # review | post | comment | article | video
    extra: dict = field(default_factory=dict)


@dataclass
class CollectorResult:
    source: str
    reviews: list[Review] = field(default_factory=list)
    profile: dict = field(default_factory=dict)   # company-level facts (e.g. Crunchbase)
    status: str = "ok"                            # ok | skipped | no_data | error
    note: str = ""
