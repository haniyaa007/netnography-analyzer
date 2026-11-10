#!/usr/bin/env python3
"""Netnography Analyzer CLI.

  python main.py run                       # prompts for company name + website
  python main.py run --name Acme --website https://acme.com
  python main.py login linkedin            # one-time browser login (you type credentials)
  python main.py sources                   # list sources + whether they are configured
"""
import argparse
import logging
from datetime import date
from pathlib import Path

from netno.collectors import SITES, build_collectors, interactive_login
from netno.config import OUTPUT_DIR, SESSIONS_DIR
from netno.models import Company
from netno.pipeline import run_pipeline


def _set(v: str | None) -> set[str]:
    return {x.strip() for x in v.split(",") if x.strip()} if v else set()


def cmd_run(a):
    name = a.name or input("Company name: ").strip()
    site = a.website or input("Company website (e.g. https://acme.com): ").strip()
    company = Company(name, site)
    out = Path(a.out) if a.out else OUTPUT_DIR / f"{company.slug}_netnography_{date.today()}.xlsx"
    run_pipeline(company, out, only=_set(a.only), skip=_set(a.skip), max_items=a.max_items,
                 headed=a.headed, csv_path=a.import_csv, anonymize=not a.keep_authors)


def cmd_login(a):
    if a.site not in SITES:
        raise SystemExit(f"Unknown site '{a.site}'. Choose from: {', '.join(SITES)}")
    interactive_login(a.site)


def cmd_sources(_):
    print(f"{'source':<16}{'status'}")
    for c in build_collectors():
        miss = c.missing_config()
        if miss:
            st = f"needs env: {', '.join(miss)}"
        elif c.name in SITES and SITES[c.name].get("needs_login"):
            ok = (SESSIONS_DIR / c.name).exists() and any((SESSIONS_DIR / c.name).glob('*'))
            st = "logged in" if ok else f"needs login: python main.py login {c.name}"
        else:
            st = "ready"
        print(f"{c.name:<16}{st}")


def main():
    ap = argparse.ArgumentParser(description="Netnography Analyzer")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="collect + analyse + write Excel")
    r.add_argument("--name"), r.add_argument("--website")
    r.add_argument("--only", help="comma list of sources, e.g. reddit,trustpilot")
    r.add_argument("--skip", help="comma list of sources to skip")
    r.add_argument("--max-items", type=int, default=200, help="per-source cap (default 200)")
    r.add_argument("--headed", action="store_true", help="show browser windows (CAPTCHA / debugging)")
    r.add_argument("--import-csv", help="CSV of reviews exported elsewhere (columns: text,platform,rating,date,author,url)")
    r.add_argument("--keep-authors", action="store_true", help="do NOT pseudonymise author names")
    r.add_argument("--out", help="output .xlsx path")
    r.set_defaults(fn=cmd_run)

    l = sub.add_parser("login", help="log into a site once in a real browser window")
    l.add_argument("site")
    l.set_defaults(fn=cmd_login)

    s = sub.add_parser("sources", help="show configured sources")
    s.set_defaults(fn=cmd_sources)

    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.WARNING)
    a.fn(a)


if __name__ == "__main__":
    main()
