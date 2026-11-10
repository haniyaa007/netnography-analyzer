"""Single place that launches the browser, so you can choose WHICH browser via .env:

  BROWSER_CHANNEL=chrome        # default: your installed Google Chrome (no download needed)
  BROWSER_CHANNEL=msedge        # installed Microsoft Edge
  BROWSER_CHANNEL=chromium      # Playwright's bundled Chromium (needs `playwright install chromium`)
  BROWSER_EXECUTABLE=/path/to/any/chromium-based/browser   # overrides the channel (Brave, Arc, Chromium...)
"""
from __future__ import annotations

import os
from pathlib import Path


def launch(p, profile_dir: Path, headless: bool = True, viewport: dict | None = {"width": 1366, "height": 900}):
    opts = dict(headless=headless, viewport=viewport)
    exe = os.getenv("BROWSER_EXECUTABLE")
    channel = (os.getenv("BROWSER_CHANNEL") or "chrome").lower()
    if exe:
        opts["executable_path"] = exe
    elif channel != "chromium":
        opts["channel"] = channel
    try:
        return p.chromium.launch_persistent_context(str(profile_dir), **opts)
    except Exception as e:
        raise RuntimeError(
            f"Could not launch browser ({exe or channel}). Install Google Chrome, or set BROWSER_CHANNEL=msedge, "
            f"or BROWSER_EXECUTABLE=/path/to/browser in .env. Original error: {e}") from e
