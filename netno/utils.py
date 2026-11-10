from __future__ import annotations

import logging
import random
import re
import time
from datetime import datetime, timezone

import requests
from dateutil import parser as dtparser

from .config import USER_AGENT

log = logging.getLogger("netno")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_TAGS = re.compile(r"<[^>]+>")


def clean_text(s: str | None) -> str:
    if not s:
        return ""
    s = _TAGS.sub(" ", str(s))
    s = _CTRL.sub("", s)
    return re.sub(r"\s+", " ", s).strip()[:30000]  # Excel cell limit is 32,767


def parse_date(value) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        return dtparser.parse(str(value))
    except (ValueError, OverflowError, TypeError):
        return None


def polite_sleep(lo: float = 1.5, hi: float = 3.5) -> None:
    time.sleep(random.uniform(lo, hi))


def http_get(url: str, **kw) -> requests.Response:
    headers = kw.pop("headers", {}) or {}
    headers.setdefault("User-Agent", USER_AGENT)
    kw.setdefault("timeout", 30)
    r = None
    for attempt in range(3):
        r = requests.get(url, headers=headers, **kw)
        if r.status_code == 429:
            time.sleep(2 ** attempt * 2)
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()
    return r
