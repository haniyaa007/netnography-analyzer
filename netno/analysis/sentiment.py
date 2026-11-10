from __future__ import annotations

import pandas as pd
from langdetect import DetectorFactory, detect
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

DetectorFactory.seed = 0
_an = SentimentIntensityAnalyzer()


def _lang(t: str) -> str:
    try:
        return detect(t[:500])
    except Exception:
        return "unknown"


def add_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """VADER compound score (-1..1). VADER is English-only: `sentiment_reliable` marks English rows."""
    df = df.copy()
    df["word_count"] = df["text"].str.split().str.len()
    df["language"] = df["text"].map(_lang)
    df["sentiment_reliable"] = df["language"].eq("en")
    df["sentiment"] = df["text"].map(lambda t: _an.polarity_scores(t)["compound"]).round(3)
    df["sentiment_label"] = pd.cut(df["sentiment"], [-1.01, -0.05, 0.05, 1.01],
                                   labels=["negative", "neutral", "positive"]).astype(str)
    star = (df["rating"] - 3) / 2   # 1..5 stars -> -1..1
    df["sentiment_blended"] = df["sentiment"].where(star.isna(), 0.5 * df["sentiment"] + 0.5 * star).round(3)
    return df
