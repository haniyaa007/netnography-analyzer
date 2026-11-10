"""Import reviews you exported yourself (CSV) from ANY platform (Outscraper, SerpApi, app-store exports...).
Required column: text. Optional: platform, rating, date, author, url, title, engagement."""
from __future__ import annotations

import pandas as pd

from ..models import CollectorResult, Review
from ..utils import parse_date


def import_csv(path: str) -> CollectorResult:
    df = pd.read_csv(path)
    out = []
    for _, r in df.iterrows():
        g = lambda k, d="": (r.get(k) if k in df.columns and pd.notna(r.get(k)) else d)
        out.append(Review(
            platform=str(g("platform", "manual_import")), text=str(g("text")), title=str(g("title")),
            rating=float(g("rating")) if g("rating", None) not in (None, "") else None,
            date=parse_date(g("date", None)), author=str(g("author")), source_url=str(g("url")),
            engagement=int(g("engagement", 0) or 0)))
    return CollectorResult("manual_import", out, note=f"{len(out)} rows from {path}")
