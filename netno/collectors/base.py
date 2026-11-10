from __future__ import annotations

import os
from abc import ABC, abstractmethod

from ..models import Company, CollectorResult
from ..utils import log


class Collector(ABC):
    name: str = "base"
    requires_env: list[str] = []

    def __init__(self, headed: bool = False):
        self.headed = headed  # show the browser window (useful for CAPTCHAs / debugging)

    def missing_config(self) -> list[str]:
        return [k for k in self.requires_env if not os.getenv(k)]

    def run(self, company: Company, max_items: int) -> CollectorResult:
        missing = self.missing_config()
        if missing:
            return CollectorResult(self.name, status="skipped",
                                   note=f"Missing env vars: {', '.join(missing)}")
        try:
            return self.collect(company, max_items)
        except Exception as e:  # one broken source must never kill the whole run
            log.exception("Collector %s failed", self.name)
            return CollectorResult(self.name, status="error", note=f"{type(e).__name__}: {e}")

    @abstractmethod
    def collect(self, company: Company, max_items: int) -> CollectorResult: ...
