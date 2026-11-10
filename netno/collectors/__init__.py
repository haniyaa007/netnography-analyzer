from .base import Collector
from .browser_sites import SITES, BrowserSiteCollector, interactive_login
from .crunchbase import CrunchbaseCollector
from .google_places import GooglePlacesCollector
from .open_web import HackerNewsCollector, NewsCollector, YouTubeCollector
from .reddit import RedditCollector
from .trustpilot import TrustpilotCollector


def build_collectors(headed: bool = False) -> list[Collector]:
    cols: list[Collector] = [
        RedditCollector(headed), GooglePlacesCollector(headed), TrustpilotCollector(headed),
        CrunchbaseCollector(headed), HackerNewsCollector(headed), YouTubeCollector(headed),
        NewsCollector(headed),
    ]
    cols += [BrowserSiteCollector(k, headed) for k in SITES]
    return cols


__all__ = ["build_collectors", "SITES", "interactive_login", "Collector"]
