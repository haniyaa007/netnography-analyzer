"""Netnography-specific layers: community profiles, authenticity screening, timeline,
representative voices, cross-platform triangulation and auto-drafted field notes."""
from __future__ import annotations

from datetime import date

import pandas as pd

PLATFORM_TYPES = {
    "trustpilot": "Consumer review platform", "google_reviews": "Map/local review platform",
    "sitejabber": "Consumer review platform", "yelp": "Local review platform", "bbb": "Complaint/consumer directory",
    "g2": "B2B software review platform", "capterra": "B2B software review platform",
    "producthunt": "Product community", "glassdoor": "Employer review platform",
    "reddit": "Forum / interest communities", "hackernews": "Tech forum", "youtube": "Video + comments",
    "x": "Microblog", "linkedin": "Professional network", "instagram": "Visual social network",
    "facebook": "General social network", "news": "Press / media", "manual_import": "Researcher-imported",
}


def platform_profile(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("platform")
    prof = g.agg(items=("text", "size"), unique_authors=("author", "nunique"),
                 avg_rating=("rating", "mean"), avg_sentiment=("sentiment", "mean"),
                 pct_negative=("sentiment_label", lambda s: (s == "negative").mean()),
                 pct_positive=("sentiment_label", lambda s: (s == "positive").mean()),
                 avg_words=("word_count", "mean"), total_engagement=("engagement", "sum"),
                 first_date=("date", "min"), last_date=("date", "max")).reset_index()
    prof.insert(1, "community_type", prof["platform"].map(PLATFORM_TYPES).fillna("Other"))
    for c in ("avg_rating", "avg_sentiment", "pct_negative", "pct_positive", "avg_words"):
        prof[c] = prof[c].round(3)
    return prof.sort_values("items", ascending=False).reset_index(drop=True)


def timeline(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["date"]).copy()
    if d.empty:
        return pd.DataFrame(columns=["month", "items", "avg_sentiment", "avg_rating"])
    d["month"] = d["date"].dt.to_period("M").astype(str)
    t = d.groupby("month").agg(items=("text", "size"), avg_sentiment=("sentiment", "mean"),
                               avg_rating=("rating", "mean")).round(3).reset_index()
    return t.sort_values("month")


def representative_quotes(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for p, g in df.groupby("platform"):
        picks = [("Most positive", g.nlargest(3, "sentiment")), ("Most negative", g.nsmallest(3, "sentiment"))]
        if g["engagement"].max() > 0:
            picks.append(("Most engaged", g.nlargest(2, "engagement")))
        for label, sub in picks:
            for _, r in sub.iterrows():
                rows.append({"platform": p, "voice_type": label, "sentiment": r["sentiment"], "rating": r["rating"],
                             "engagement": r["engagement"], "author": r["author"], "date": r["date"],
                             "quote": r["text"][:700], "url": r["source_url"]})
    return pd.DataFrame(rows)


def flag_authenticity(df: pd.DataFrame) -> pd.DataFrame:
    """Heuristic screening for astroturfing / low-information posts. Flags are *prompts for human
    review*, not verdicts."""
    df = df.copy()
    norm = df["text"].str.lower().str.replace(r"\W+", " ", regex=True).str.strip()
    f = pd.DataFrame(index=df.index)
    f["duplicate_text"] = norm.duplicated(keep=False) & (norm.str.len() > 20)
    f["very_short"] = df["text"].str.len() < 30
    letters = df["text"].map(lambda t: sum(c.isalpha() for c in t))
    upper = df["text"].map(lambda t: sum(c.isupper() for c in t))
    f["shouting"] = (letters > 20) & (upper / letters.clip(lower=1) > 0.6)
    f["extreme_rating_no_detail"] = df["rating"].isin([1.0, 5.0]) & (df["text"].str.len() < 40)
    day = df["date"].dt.strftime("%Y-%m-%d")
    size = df.groupby(["platform", day])["text"].transform("size")
    f["burst_day"] = size.fillna(0) >= 8
    df["flags"] = f.apply(lambda r: ", ".join(c for c in f.columns if r[c]), axis=1)
    df["authenticity_risk"] = f.sum(axis=1)
    return df


def authenticity_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["platform", "date", "author", "rating", "authenticity_risk", "flags", "text", "source_url"]
    t = df[df["authenticity_risk"] > 0][cols].sort_values("authenticity_risk", ascending=False).copy()
    t["text"] = t["text"].str[:300]
    return t


def _d(x) -> str:
    return x.strftime("%Y-%m-%d") if pd.notna(x) else "n/a"


def executive_summary(company, df: pd.DataFrame, themes: pd.DataFrame) -> pd.DataFrame:
    top = ", ".join(themes["theme"].head(3)) if not themes.empty else "n/a"
    rows = [
        ("Company", company.name), ("Website", company.website), ("Report date", str(date.today())),
        ("Items analysed", len(df)), ("Platforms with data", df["platform"].nunique()),
        ("Date range", f"{_d(df['date'].min())} to {_d(df['date'].max())}"),
        ("Average star rating (rated items)", round(df["rating"].mean(), 2) if df["rating"].notna().any() else "n/a"),
        ("Average sentiment (-1..1)", round(df["sentiment"].mean(), 3)),
        ("% positive", f"{(df['sentiment_label'] == 'positive').mean():.1%}"),
        ("% negative", f"{(df['sentiment_label'] == 'negative').mean():.1%}"),
        ("Top 3 themes", top),
        ("% items with authenticity flags", f"{(df['authenticity_risk'] > 0).mean():.1%}"),
        ("% items in English (sentiment reliable)", f"{df['sentiment_reliable'].mean():.1%}"),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def field_notes(company, df, prof, themes, emo, results) -> pd.DataFrame:
    notes: list[tuple[str, str]] = []
    add = lambda s, t: notes.append((s, t))
    plats = ", ".join(f"{r.platform} ({r['items']})" for _, r in prof.iterrows())
    add("1. Research context",
        f"Online discourse about {company.name} ({company.domain}) was collected on {date.today()}: "
        f"{len(df)} items across {df['platform'].nunique()} platforms - {plats}. Date range "
        f"{_d(df['date'].min())} to {_d(df['date'].max())}.")
    big = prof.iloc[0]
    add("2. Community landscape",
        f"Most material comes from {big['platform']} ({big['community_type']}), "
        f"{big['items'] / len(df):.0%} of the corpus. Different community types have different norms "
        f"(complaint venues vs. enthusiast forums vs. press), so volume is not representativeness.")
    if len(prof) > 1:
        ps = prof.set_index("platform")["avg_sentiment"].dropna()
        if len(ps) > 1:
            hi, lo = ps.idxmax(), ps.idxmin()
            spread = ps.max() - ps.min()
            add("3. Cross-platform divergence",
                f"Sentiment is highest on {hi} ({ps[hi]:+.2f}) and lowest on {lo} ({ps[lo]:+.2f}); spread {spread:.2f}. "
                + ("This is a meaningful gap - ask what each community's purpose does to what gets posted."
                   if spread > 0.25 else "Platforms are broadly aligned in tone."))
    if not themes.empty:
        t3 = themes.head(3)
        add("4. Dominant discourses", "; ".join(
            f"'{r.theme}' ({r.mentions} mentions, sentiment {r.avg_sentiment:+.2f})" for r in t3.itertuples()))
        worst = themes[themes["mentions"] >= 3].sort_values("avg_sentiment")
        if not worst.empty:
            w = worst.iloc[0]
            add("5. Pain point to investigate", f"'{w['theme']}' carries the most negative tone ({w['avg_sentiment']:+.2f}, n={w['mentions']}).")
    if not emo.empty and emo["mentions"].sum() > 0:
        e = emo.iloc[0]
        add("6. Emotional register", f"Most frequent emotion cue: {e['emotion']} ({e['share_overall']:.0%} of items).")
    flagged = (df["authenticity_risk"] > 0).mean()
    add("7. Authenticity & data quality",
        f"{flagged:.0%} of items carry at least one heuristic flag (duplicates, very short, shouting, burst days). "
        f"Review the Authenticity sheet before quoting anything.")
    bad = [f"{r.source}: {r.note}" for r in results if r.status in ("skipped", "error", "no_data")]
    if bad:
        add("8. Coverage gaps", "Sources without data - " + " | ".join(bad))
    add("9. Limitations",
        "Only public, self-selected content; platform sampling bias; API caps (e.g. Google returns 5 reviews); "
        "VADER sentiment is English-only; keyword codebook is deductive and misses sarcasm. Treat this as a "
        "structured first pass - interpretive coding by the researcher is still required.")
    add("10. Prompts for your interpretive analysis",
        "Who speaks and who is silent? What identity work do reviewers do ('as a long-time customer...')? "
        "Which community norms shape complaints? Where do company replies change the conversation? "
        "What do users say that the company's own website never does?")
    return pd.DataFrame(notes, columns=["section", "note"])
