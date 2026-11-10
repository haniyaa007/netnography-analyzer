# Netnography Analyzer

Type a company name + website → get an Excel workbook with a computational netnography of what
people say about it across review sites, forums, social networks and press.

**Output sheets:** Executive_Summary · Platform_Profile (with charts) · Themes · Theme_x_Platform ·
Emotions · Timeline · Top_Terms · Topics · Quotes · Authenticity · Field_Notes · Company_Profile ·
Source_Log · Raw_Data

## Sources
| Source | How | Needs |
|---|---|---|
| Reddit | official API (PRAW) | client id/secret |
| Google reviews | Places API (New) – max 5 reviews/place | API key |
| Trustpilot | Playwright reading embedded page JSON | nothing (browser) |
| Crunchbase | official API → company context only (no reviews exist there) | paid API key |
| Hacker News, Google News | free public endpoints | nothing |
| YouTube | Data API v3 (video + comments) | API key |
| LinkedIn, Instagram, X, Facebook, Glassdoor | Playwright with **your own manual login** | `python main.py login <site>` |
| G2, Capterra, Yelp, Sitejabber, BBB, Product Hunt | Playwright, JSON-LD + selectors | nothing (login optional) |
| Anything else | export CSV → `--import-csv` | – |

## Setup (VS Code)
```bash
git clone <your repo> && cd netnography-analyzer
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# No browser download needed: uses your installed Google Chrome (see BROWSER_CHANNEL in .env).
# Only if you set BROWSER_CHANNEL=chromium:  python -m playwright install chromium
cp .env.example .env                 # then fill in the keys you have
python main.py sources               # see what is ready
python -m pytest                     # sanity check (no keys needed)
```
In VS Code: Ctrl/Cmd+Shift+P → *Python: Select Interpreter* → `.venv`.
Use Run & Debug (F5) – launch configs are included.

## Use
```bash
python main.py login linkedin        # once per site; you type credentials in the opened browser
python main.py run                   # prompts for name + website
python main.py run --name "Acme" --website https://acme.com --max-items 300
python main.py run --name Acme --website acme.com --only reddit,trustpilot,g2
python main.py run --name Acme --website acme.com --import-csv my_export.csv
python main.py run ... --headed      # watch the browser / solve a CAPTCHA
```
Result: `outputs/<company>_netnography_<date>.xlsx`

## Customising
* **Codebook** (themes + emotions): `netno/analysis/themes.py` – tailor to your industry.
* **Selectors / new sites**: `SITES` dict in `netno/collectors/browser_sites.py`.
  Social markup changes often; if a site returns nothing, inspect the page and update selectors.
* **New API collector**: subclass `Collector`, implement `collect()`, register in `collectors/__init__.py`.

## Privacy, ethics, terms of service – please read
* Your passwords are never read or stored. Only session cookies live in `.sessions/` (git-ignored).
  **Never commit `.sessions/` or `.env`.**
* LinkedIn, Instagram, X, Facebook and Trustpilot terms restrict automated collection; accounts can be
  restricted. Use a dedicated research account, low volume, and prefer official APIs / licensed data
  (SerpApi, Outscraper, vendor exports) for large-scale or commercial work.
* Authors are pseudonymised by default (`--keep-authors` to disable). Follow your ethics board / netnography
  guidelines (e.g. Kozinets) when quoting.
* Sentiment (VADER) is English-only; flags in the Authenticity sheet are prompts for review, not verdicts.
