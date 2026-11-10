import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

SESSIONS_DIR = ROOT / ".sessions"   # browser profiles (cookies). Git-ignored. Never share.
OUTPUT_DIR = ROOT / "outputs"
SESSIONS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

USER_AGENT = os.getenv("HTTP_USER_AGENT") or (
    "Mozilla/5.0 (compatible; NetnographyAnalyzer/0.1; academic-research)"
)
