from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

import pandas as pd
from rich.console import Console

from .analysis import netnography as nn
from .analysis import themes as th
from .analysis.sentiment import add_sentiment
from .collectors import build_collectors
from .collectors.manual_import import import_csv
from .export.excel import write_workbook
from .models import Company, CollectorResult
from .utils import clean_text

console = Console()


def _anon(a: str) -> str:
    return "user_" + hashlib.sha1(a.encode()).hexdigest()[:8] if a else ""


def to_frame(reviews, anonymize: bool) -> pd.DataFrame:
    df = pd.DataFrame([asdict(r) for r in reviews])
    if df.empty:
        return df
    df["text"] = df["text"].map(clean_text)
    df["title"] = df["title"].map(clean_text)
    df = df[df["text"].str.len() >= 15].copy()
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce").dt.tz_localize(None)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["engagement"] = pd.to_numeric(df["engagement"], errors="coerce").fillna(0).astype(int)
    df["extra"] = df["extra"].map(lambda d: json.dumps(d, ensure_ascii=False, default=str))
    df = df[~(df["platform"] + "|" + df["text"].str.lower().str[:200]).duplicated()]
    if anonymize:
        df["author"] = df["author"].fillna("").map(_anon)
    return df.reset_index(drop=True)


def _readme(company: Company, results: list[CollectorResult]) -> pd.DataFrame:
    rows = [
        ("What this is", f"Computational netnography workbook for {company.name} ({company.domain}), generated {date.today()}."),
        ("Method", "Public online discourse is collected per platform, cleaned, de-duplicated, scored for sentiment (VADER), "
                   "coded against a keyword codebook (netno/analysis/themes.py), screened for authenticity, and summarised."),
        ("Sheets", "Executive_Summary | Platform_Profile | Themes | Theme_x_Platform | Emotions | Timeline | Top_Terms | "
                   "Topics | Quotes | Authenticity | Field_Notes | Company_Profile | Source_Log | Raw_Data"),
        ("Ethics", "Author names are pseudonymised by default. Quote responsibly; do not attempt to re-identify individuals."),
        ("Caveat", "Heuristic first-pass analysis. Sentiment is reliable for English only. Always read raw data before concluding."),
    ]
    return pd.DataFrame(rows, columns=["item", "description"])


def run_pipeline(company: Company, out_path: Path, only: set[str] | None = None, skip: set[str] | None = None,
                 max_items: int = 200, headed: bool = False, csv_path: str | None = None,
                 anonymize: bool = True) -> Path:
    only, skip = only or set(), skip or set()
    results: list[CollectorResult] = []
    for c in build_collectors(headed):
        if (only and c.name not in only) or c.name in skip:
            continue
        console.print(f"[cyan]> {c.name}[/cyan] ...", end=" ")
        res = c.run(company, max_items)
        results.append(res)
        colour = {"ok": "green", "skipped": "yellow", "no_data": "yellow", "error": "red"}[res.status]
        console.print(f"[{colour}]{res.status}[/{colour}] {len(res.reviews)} items {res.note}")
    if csv_path:
        res = import_csv(csv_path)
        results.append(res)
        console.print(f"[green]> manual_import[/green] {len(res.reviews)} items")

    df = to_frame([r for res in results for r in res.reviews], anonymize)
    profile: dict = {"company": company.name, "website": company.website}
    for res in results:
        profile.update(res.profile)
    log_df = pd.DataFrame([{"source": r.source, "status": r.status, "items": len(r.reviews), "note": r.note}
                           for r in results])
    prof_df = pd.DataFrame([{"field": k, "value": v} for k, v in profile.items()])

    if df.empty:
        console.print("[red]No data collected.[/red] Check Source_Log in the workbook / configure keys / log in.")
        return write_workbook(out_path, {"Read_Me": _readme(company, results), "Company_Profile": prof_df,
                                         "Source_Log": log_df})

    console.print(f"[bold]Analysing {len(df)} items...[/bold]")
    df = add_sentiment(df)
    theme_m, emo_m = th.tag(df, th.THEME_RE), th.tag(df, th.EMOTION_RE)
    df["themes"], df["emotions"] = th.label_column(theme_m), th.label_column(emo_m)
    df = nn.flag_authenticity(df)

    themes = th.theme_summary(df, theme_m)
    emo = th.emotion_summary(df, emo_m)
    prof = nn.platform_profile(df)
    raw_cols = ["platform", "content_type", "date", "author", "rating", "sentiment", "sentiment_label",
                "sentiment_blended", "themes", "emotions", "flags", "engagement", "title", "text",
                "source_url", "language", "word_count", "extra"]

    sheets = {
        "Read_Me": _readme(company, results),
        "Executive_Summary": nn.executive_summary(company, df, themes),
        "Platform_Profile": prof,
        "Themes": themes,
        "Theme_x_Platform": th.theme_platform_matrix(df, theme_m),
        "Emotions": emo,
        "Timeline": nn.timeline(df),
        "Top_Terms": th.top_terms(df),
        "Topics": th.discover_topics(df),
        "Quotes": nn.representative_quotes(df),
        "Authenticity": nn.authenticity_table(df),
        "Field_Notes": nn.field_notes(company, df, prof, themes, emo, results),
        "Company_Profile": prof_df,
        "Source_Log": log_df,
        "Raw_Data": df[raw_cols],
    }
    path = write_workbook(out_path, sheets)
    console.print(f"[bold green]Saved:[/bold green] {path}")
    return path
