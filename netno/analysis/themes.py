from __future__ import annotations

import re

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

# Deductive codebook. EDIT THIS to fit your industry - it is the core of the thematic coding.
CODEBOOK: dict[str, list[str]] = {
    "Customer service & support": ["support", "customer service", "helpdesk", "agent", "representative",
                                   "response", "replied", "ticket", "live chat", "call center"],
    "Pricing & value": ["price", "pricing", "expensive", "cheap", "cost", "fees", "fee", "subscription",
                        "value for money", "overpriced", "hidden fees", "worth it"],
    "Refunds, billing & cancellation": ["refund", "refunded", "chargeback", "billing", "invoice", "cancel",
                                        "cancellation", "money back", "double charged", "charged"],
    "Product quality & reliability": ["quality", "broken", "defect", "bug", "bugs", "crash", "crashes",
                                      "reliable", "durable", "faulty", "stopped working", "glitch"],
    "Delivery & logistics": ["delivery", "shipping", "shipped", "arrived", "late", "delay", "delayed",
                             "tracking", "package", "parcel"],
    "Usability & UX": ["easy to use", "interface", "confusing", "intuitive", "navigation", "user friendly",
                       "clunky", "slow", "onboarding"],
    "Trust, scam & fraud": ["scam", "scammed", "fraud", "fake", "stole", "stolen", "rip off", "ripoff",
                            "legit", "untrustworthy", "phishing"],
    "Privacy & security": ["privacy", "security", "breach", "hack", "hacked", "gdpr", "leak", "data leak"],
    "Features & innovation": ["feature", "features", "integration", "integrations", "roadmap", "update",
                              "innovative", "missing feature"],
    "Employer & culture": ["manager", "culture", "salary", "burnout", "layoff", "layoffs", "toxic",
                           "work-life", "hiring", "interview", "employees"],
    "Brand, reputation & advocacy": ["recommend", "recommended", "reputation", "brand", "avoid",
                                     "stay away", "best", "worst", "love", "hate"],
}

EMOTIONS: dict[str, list[str]] = {
    "anger": ["angry", "furious", "outrage", "rude", "ridiculous", "unacceptable", "terrible", "worst",
              "hate", "disgusting", "scam"],
    "frustration": ["frustrating", "frustrated", "annoying", "waste", "useless", "nightmare", "ignored",
                    "waiting", "stuck", "again and again"],
    "disappointment": ["disappointed", "disappointing", "let down", "not as described", "poor", "mediocre",
                       "expected more"],
    "fear / anxiety": ["worried", "scared", "afraid", "risky", "concern", "concerned", "unsafe", "nervous"],
    "joy / delight": ["love", "loved", "amazing", "fantastic", "delighted", "happy", "great", "excellent",
                      "awesome", "perfect"],
    "trust / gratitude": ["trust", "trusted", "reliable", "thank", "thanks", "grateful", "honest",
                          "recommend", "helpful"],
    "surprise": ["surprised", "unexpected", "shocked", "wow", "unbelievable"],
}


def _compile(book: dict[str, list[str]]) -> dict[str, re.Pattern]:
    return {k: re.compile(r"\b(?:" + "|".join(re.escape(w) for w in v) + r")\b", re.I) for k, v in book.items()}


THEME_RE, EMOTION_RE = _compile(CODEBOOK), _compile(EMOTIONS)


def tag(df: pd.DataFrame, patterns: dict[str, re.Pattern]) -> pd.DataFrame:
    return pd.DataFrame({k: df["text"].map(lambda s, p=p: bool(p.search(s))) for k, p in patterns.items()},
                        index=df.index)


def label_column(m: pd.DataFrame) -> pd.Series:
    return m.apply(lambda r: "; ".join(c for c in m.columns if r[c]), axis=1)


def theme_summary(df: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    cols = ["theme", "mentions", "share_of_items", "avg_sentiment", "avg_rating", "top_platform"]
    rows = []
    for t in m.columns:
        sub = df[m[t]]
        if sub.empty:
            continue
        rows.append({"theme": t, "mentions": len(sub), "share_of_items": round(len(sub) / len(df), 3),
                     "avg_sentiment": round(sub["sentiment"].mean(), 3),
                     "avg_rating": round(sub["rating"].mean(), 2) if sub["rating"].notna().any() else None,
                     "top_platform": sub["platform"].value_counts().idxmax()})
    return pd.DataFrame(rows, columns=cols).sort_values("mentions", ascending=False).reset_index(drop=True)


def theme_platform_matrix(df: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for t in m.columns:
        row = {"theme": t}
        for p in sorted(df["platform"].unique()):
            sub = df[m[t] & (df["platform"] == p)]
            row[p] = round(sub["sentiment"].mean(), 3) if len(sub) >= 2 else None
        rows.append(row)
    return pd.DataFrame(rows)


def emotion_summary(df: pd.DataFrame, e: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for emo in e.columns:
        row = {"emotion": emo, "mentions": int(e[emo].sum()), "share_overall": round(e[emo].mean(), 3)}
        for p in sorted(df["platform"].unique()):
            mask = df["platform"] == p
            row[f"share_{p}"] = round(e.loc[mask, emo].mean(), 3) if mask.any() else None
        rows.append(row)
    return pd.DataFrame(rows).sort_values("mentions", ascending=False).reset_index(drop=True)


def top_terms(df: pd.DataFrame, n: int = 25) -> pd.DataFrame:
    rows = []

    def run(texts, label):
        if len(texts) < 3:
            return
        try:
            vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=5000,
                                  min_df=2 if len(texts) >= 20 else 1, max_df=0.9)
            X = vec.fit_transform(texts)
        except ValueError:
            return
        sc = np.asarray(X.sum(axis=0)).ravel()
        terms = vec.get_feature_names_out()
        for i in sc.argsort()[::-1][:n]:
            rows.append({"scope": label, "term": terms[i], "tfidf_score": round(float(sc[i]), 3)})

    run(df["text"].tolist(), "ALL")
    for p, g in df.groupby("platform"):
        run(g["text"].tolist(), p)
    return pd.DataFrame(rows, columns=["scope", "term", "tfidf_score"])


def discover_topics(df: pd.DataFrame) -> pd.DataFrame:
    """Inductive complement to the codebook: unsupervised topic clusters."""
    cols = ["topic", "items", "top_terms", "avg_sentiment", "example"]
    if len(df) < 30:
        return pd.DataFrame(columns=cols)
    k = min(8, max(2, len(df) // 40))
    vec = TfidfVectorizer(stop_words="english", min_df=2, max_df=0.8, max_features=4000)
    try:
        X = vec.fit_transform(df["text"])
    except ValueError:
        return pd.DataFrame(columns=cols)
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    terms, rows = vec.get_feature_names_out(), []
    for i in range(k):
        sub = df.iloc[np.where(km.labels_ == i)[0]]
        top = ", ".join(terms[km.cluster_centers_[i].argsort()[::-1][:8]])
        rows.append({"topic": f"Topic {i + 1}", "items": len(sub), "top_terms": top,
                     "avg_sentiment": round(sub["sentiment"].mean(), 3), "example": sub["text"].iloc[0][:300]})
    return pd.DataFrame(rows, columns=cols).sort_values("items", ascending=False)
