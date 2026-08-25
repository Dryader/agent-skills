---
name: financial-data-apis
description: Select, compare, and use financial market data APIs for portfolio analysis, screening, and backtesting. Covers free and paid tiers, pitfalls, TSX/international coverage gaps, and the optimal free stack.
triggers:
  - "stock market API"
  - "financial data API"
  - "fundamentals API"
  - "market data provider"
  - "stock screener API"
  - "historical price data"
  - "yfinance alternative"
tags: [finance, data, apis, edgar, koyfin]
---

# Financial Data APIs for Portfolio Analysis

## The Optimal Free Stack (as of 2026)

For personal portfolio analysis (checking ~40 stocks occasionally), you do NOT need paid APIs. The free stack covers everything:

| Need | Provider | Cost | Notes |
|------|----------|------|-------|
| US Fundamentals | SEC EDGAR XBRL | Free | Authoritative filings, no key (see EDGAR section); Finnhub convenient fallback |
| Screening | Business Quant API | Free | 1,000+ metrics, AND/OR logic, SEC-sourced |
| Bulk Prices | yfinance | Free | Batch download, TSX support |
| Fresh Prices | Tiingo | Free | Rate limited (~100 req/hr), US only |
| Analyst Estimates | Finnhub | Free | Consensus, price targets, earnings surprises |
| Insider/ESG | Finnhub | Free | Congressional trading, insider transactions |

### SEC EDGAR XBRL — authoritative US fundamentals (free, no key)

For US filers' actual financial statements, EDGAR XBRL beats every aggregator: no API key
(descriptive User-Agent header only), every tagged fact from 10-K/10-Q, us-gaap + ifrs-full.
- Endpoints: company_tickers.json (ticker->CIK), companyfacts/CIK##########.json
- Extraction is TRICKY: fy labels unreliable, 10-Q restatements file after 10-K, per-company
  tag churn (debt tags, capex, cash, revenue), stale
  discontinued tags, YTD-only cash flow breaking TTM.
- Full recipe + per-company tag maps: see the EDGAR section above (verified Aug 2026:
  extraction matched several filers' 10-Qs line-for-line)
- Working pipeline lives in the live environment (fetch+cache script + ratio engine; cache on disk).
- Best free stack for US statements: EDGAR (authoritative) > Finnhub free (convenient,
  sign conventions differ) > yfinance (last resort).

## API Comparison Matrix

### Free Tier Champions

**Finnhub** (finnhub.io) — BEST overall free tier
- 60 calls/min (86,400/day), no daily cap
- Fundamentals: US only on free tier; Global on $3,500/mo All-In-One
- TSX: $49.99/mo add-on (EOD only, no fundamentals)
- Includes: financial statements, estimates, ESG, insider data, congressional trading, technical indicators
- Built by ex-Bloomberg/Google engineers, VC-funded
- Pitfall: Free tier is US-only for fundamentals and prices

**Business Quant API** (businessquant.com) — BEST free screener
- 1,000+ fundamental metrics, unlimited AND/OR conditions
- Financial statements parsed from SEC filings (10-K, 10-Q)
- Analyst estimates, insider transactions, institutional ownership
- Segment financials, peer comparison
- Pro plan: $19/mo (60% off) for CSV/XLSX export
- Pitfall: US stocks only

**yfinance** — BEST free bulk data
- Batch download works (yf.download with list of tickers)
- .info gives PE, FwdPE, ROE, debt, growth, sector, rating
- Covers TSX (.TO suffix), international exchanges
- Pitfall: Unofficial scraper, can break anytime. Slow for per-ticker fundamentals (one call at a time). Rate limits unpredictable.
- Pitfall: Duplicate columns when mapping tickers (e.g., 'L' -> 'L.TO' creates duplicates if 'L.TO' already exists). Fix: `returns = returns.loc[:, ~returns.columns.duplicated(keep='first')]`

**Tiingo** (tiingo.com) — Fresh price data
- Free tier: ~100 requests/hour
- US stocks only, no TSX, no TNX
- Pitfall: Rate limits hit fast when bulk fetching 200+ tickers. Use yfinance for bulk, Tiingo for fresh spot checks.

### Paid Options (ranked by value)

**EODHD** (eodhd.com) — Best paid value if you need it
- EOD Historical: £19.99/mo ($25 USD) — prices only, 100K calls/day
- Fundamentals: £59.99/mo ($75 USD) — full fundamentals + bulk endpoint
- ALL-IN-ONE: £99.99/mo ($125 USD) — everything + intraday
- Has MCP server, screener API, 60+ exchanges, 150K+ tickers
- 50% student discount available
- Includes TSX in EOD plan

**Alpha Vantage** — Transparent pricing
- Free: 25 calls/day (too limited for real use)
- Premium: $49.99/mo (75 calls/min) to $249.99/mo (1,200 calls/min)
- Pitfall: Free tier reduced from 500 to 25 calls/day. Not worth paying when Finnhub is free.

**Polygon.io** (now Massive.com) — Overkill for personal use
- Free: 5 calls/min, EOD only (useless)
- Starter: $29/mo — delayed data, 5Y history
- Advanced: $199/mo — real-time data
- Pitfall: No fundamentals in lower tiers. Primarily for real-time trading apps. No TSX.

### FMP (Financial Modeling Prep) — ALIVE on /stable/ endpoints

**Critical:** v3/v4 endpoints return 403 "Legacy Endpoint" for signups after August 2025. BUT the new `/stable/` endpoint format works with existing API keys.

- Base URL: `https://financialmodelingprep.com/stable/` (NOT `/api/v3/` or `/api/v4/`)
- Free tier (Basic): 250 calls/day
- Auth: `?apikey=YOUR_KEY` query param only. Header auth (`apikey: KEY`) returns 401.
- **Working free endpoints (all tickers):** `profile`, `quote`, `search-symbol`, `search-name`, `stock-price-change`, `market-capitalization`, `earnings-calendar`, `earnings`, `dividends`, `splits`, `analyst-estimates`, `price-target-consensus`, `fmp-articles`, `senate-latest`
- **Working free endpoints (demo tickers only — AAPL, NVDA, etc.):** `key-metrics`, `ratios`, `financial-growth`, `discounted-cash-flow`, `income-statement`, `balance-sheet-statement`, `cash-flow-statement`, `grades`
- **402 restricted (need paid plan):** `stock-list`, `company-screener`, `senate-trades`, `house-trades`, `income-statement-bulk`
- Starter ($22/mo): 300 calls/min, 5Y history, US coverage, all fundamentals unlocked
- Premium ($59/mo): 750 calls/min, 30Y history, UK + Canada coverage

**Marketstack** — Rate limited
- Free tier: 100 requests/month (basically useless)
- Paid starts at $9.99/mo for intraday

**TradingView** — No public data API
- Only offers: Charting Library (embeddable widget), Pine Script (runs on their platform), Broker API (for brokers)
- No REST API for pulling raw data. Use their platform for charts, use Finnhub/yfinance for data.

## TSX / International Coverage

This is the biggest gap in cheap APIs. Most free/cheap APIs are US-only.

| API | TSX Coverage | Cost |
|-----|-------------|------|
| yfinance | Yes (.TO suffix) | Free |
| Finnhub | $49.99/mo add-on (EOD only) | Paid |
| EODHD | Included in EOD plan | £19.99/mo |
| Tiingo | No | — |
| Business Quant | No | — |
| Polygon | No | — |

**Recommendation:** Use yfinance for TSX stocks. It works, it's free, and unless you hold many Canadian names you don't need a paid TSX-specific API.

**Koyfin screen exports contain bare Canadian tickers (CORRECTED Aug 7 2026 — the earlier
"US-exchange-only" claim was WRONG):** TSX/TSXV names appear with NO suffix (TNZ, L, POW,
GWO, AFM...) and region "United States and Canada". A `.TO` grep proves nothing — probe the
Name column instead. Failure modes when feeding exports to an API layer: (a) TSX-only names
fail a blind `.US` fetch and vanish silently (26 TSX + 3 TSXV names were missing from the
941-ticker universe this way); (b) worse, bare `L` resolves to Loews (L.US) instead of
Loblaw — a silent wrong-ticker with real price data. Fix (in build_cache.py): collision maps
(L→L.TO, POW→POW.TO; AFM/LMN/MKO→.V per CSV Name; BRKA→BRK-A.US; RCIB/TECKB/CHEUN→dash
format) + `.US`→`.TO`→`.V` retry chain + dedupe against cached .TO holdings.

**Hypothetical-universe test (reusable):** to answer "would ticker X rank?", fetch
`TICKER.TO` from EODHD, append it to the cached prices dict,
and re-run the composite rank_window — never claim a name "wouldn't qualify" without running
this. Verified example (Aug 7 2026): one held TSX name ranked 25th percentile (high 3Y return
but 49% vol and deep MaxDD sink the composite); another ranked in the bottom 8% (negative 1Y
return, high vol) — neither top-20 in any window, so no candidate would emerge from a TSX
supplement today.

## Pitfalls & Gotchas

1. **yfinance duplicate columns**: When mapping tickers (e.g., POW -> POW.TO), if the CSV already has POW.TO, you get duplicates. Always dedupe: `df = df.loc[:, ~df.columns.duplicated(keep='first')]`

2. **Tiingo rate limits**: Bulk fetching 200+ tickers hits the hourly limit fast. Use yfinance for bulk, Tiingo for spot checks.

3. **FMP v3/v4 dead, /stable/ works**: v3/v4 endpoints return 403. Use `/stable/` endpoint format instead. Free tier limited to demo tickers for fundamental endpoints (402 for others). Profile and quote work for all tickers.

4. **Finnhub free = US only**: Fundamentals, prices, estimates are all US-only on the free tier. TSX requires paid add-on.

5. **yfinance timezone issues**: Tiingo returns tz-aware dates, yfinance returns tz-naive. When combining, localize: `s.index = s.index.tz_localize(None)`

6. **Koyfin CSV exports**: Fundamental fields are mostly "N/A for download" — Koyfin restricts bulk export. The CSVs contain ticker, name, and the specific screen's filter columns (e.g., Beta, ROE, D/E for that screen), but NOT full fundamentals. You CANNOT get PE, FCF, margins, etc. from Koyfin CSVs. Use yfinance `.info()` or Finnhub for fundamental enrichment after extracting tickers. Workflow: parse tickers from CSV → download prices → enrich fundamentals separately.

7. **Survivorship bias in backtests**: Recent high-flyers (SNDK +1307%, NBIS +305%) look great in backtests but are lottery tickets. Filter candidates by minimum history (5Y+) and quality gate (Sharpe > 0.3).

8. **Marketstack per-symbol counting**: Each symbol in a batch request counts as 1 API call toward monthly quota. 100 symbols × 3 pages = 300 API calls per batch. BURNED 40,000 calls in one session by re-downloading. Only use for daily updates on a few tickers, never bulk.

9. **EODHD bulk efficiency**: 1 API call per ticker, NO pagination, NO per-symbol counting. 400 tickers = 400 calls (vs Marketstack 1,200). Best paid option for bulk historical data.

10. **EODHD TSX support**: DOES have TSX stocks. Use ticker WITHOUT `.US` suffix (e.g., `POW.TO` not `POW.TO.US`). Rule: if ticker contains `.`, don't append `.US`.

11. **EODHD stale data for Canadian stocks**: Some Canadian stocks have US OTC listings on EODHD that stop updating (e.g., CSU only had data to Feb 2022 while CSU.TO on TSX has current data). Always check `last_date > 2025-01-01` after downloading. If stale, delete the cache file and retry with yfinance using `.TO` suffix. In July 2026, this recovered 17 tickers including a name that was a top-5 composite candidate.

12. **Canadian ticker recovery workflow**: After EODHD batch download, collect all failures + stale tickers. Retry each with yfinance `.TO` suffix:
```python
import yfinance as yf
for t in failed:
    yt = yf.Ticker(t + '.TO')
    hist = yt.history(start='2016-01-01', auto_adjust=True)
    if len(hist) > 200:
        s = hist['Close']
        s.index = s.index.tz_localize(None)
        s.to_frame().to_csv(os.path.join(CACHE_DIR, t + '.TO.csv'))
```

12b. **Koyfin screen CSVs contain bare Canadian tickers (Aug 2026):** TSX-only names appear in screen exports with NO suffix (TNZ = Tenaz, L = Loblaw, GWO = Great-West) and region "United States and Canada". Never conclude a screen is US-only by grepping for ".TO". Two failure modes when feeding these to an API layer: (a) TSX-only names fail a blind `.US` fetch and get silently dropped (26+ names were missing from the 941-ticker universe this way); (b) worse, bare `L` resolves to Loews (L.US) instead of Loblaw — a silent wrong-ticker with real price data. Fix pattern: explicit collision map (L→L.TO, POW→POW.TO) + `.TO` retry when `.US` returns <200 obs. EODHD class-shares need dash format: RCI-B.TO, TECK-B.TO, CHE-UN.TO.

12c. **The <200-row retry heuristic is NOT enough — dead-US twins pass silently (Aug 8 2026):** 33 bare Canadian tickers resolved to dead US securities with ≥200 rows of stale data each. The stale series passes the row-count check, so no .TO retry fires; the phantom gets cached, the window-length filter excludes it from 1Y/3Y/5Y rankings, and the REAL company is silently missing from the universe. The "DPM delisted Oct 2021" conclusion from July 2026 was this bug misread as a market event (DPM Metals is still listed). **Fix:** staleness guard — treat any .US series whose last date is >120 days older than the build date as a phantom and force the .TO→.V retry chain; plus a post-build sweep for series with old last-dates (every hit is a phantom or a genuine delisting — resolve via EODHD probe + CSV Name column before concluding anything). The verification method is the staleness guard + post-build sweep described here.

12d. **Price-based checks can't catch live-data phantoms — run the name-sweep (Aug 8 2026):** the staleness/row-count guards catch phantoms with dead or short data only. Current-data phantoms — bare ticker resolving to a DIFFERENT live security (a Canadian bank name resolving to a NYSE insurer, a TSX name resolving to a US ETF whose price coincided with the small-cap's, and dozens more) — pass every price test. The ONLY complete detector: compare the resolved security's NAME against the screen CSV's Name column via an independent source (yfinance longName). 51 phantoms total found this way (33 stale + 18 live). Mandatory workflow: after every EODHD cache build, run the name-sweep (the name-sweep methodology and script live in the live environment); add mismatches to PHANTOM_MAP in the cache builder; rebuild; re-sweep until clean. BNS-type dual-listings (NYSE common of the same company) are correct as bare keys — price-level + FX consistency is the tiebreaker there.

12e. **Never declare a ticker dead until you've tried dash formats (Aug 8 2026):** the 8 "unresolvable" screen tickers from Aug 7 were ALL live companies with EODHD dash-format symbols: AGFB→AGF-B.TO (AGF Mgmt), CCLB→CCL-B.TO (CCL Industries), GIBA→GIB-A.TO (CGI), ACOX→ACO-X.TO (ATCO), HPSA→HPS-A.TO (Hammond Power), LASA→LAS-A.TO (Lassonde), FCRUN→FCR-UN.TO (First Capital REIT), BFB→BF-B.US (Brown-Forman). EODHD rejects the dot form (AGF.B.TO 404s) but resolves the dash form. Koyfin's bare notation for class/multi-class shares: strip to letters + suffix map (X→-X, .B→-B, .UN→-UN, .A→-A). Probe order for any bare ticker that fails: `.US` → `.TO` → `.V` → **dash forms** (`T-TO`, `T-UN.TO`, `T-A.TO`, `T-B.TO`, `T-X.TO`, `T-B.US`) → then declare dead. CGI recovery alone added a top-tier TSX name to the universe; ATCO (ACO-X.TO) is now the #1-ranked composite candidate.

12f. **EODHD call budget (Aug 8 2026):** paid plans default to 100,000 calls/day (free = 20/day) — a 20k-call day is 20% of cap, not a ceiling hit. Bulk `eod-bulk-last-day` is per-DATE (100 calls/day/exchange) — WORSE than per-ticker for history builds; per-ticker is the right primitive. The big lever is the **Search API** (`/api/search/{query}` = 1 call): returns canonical symbol + company name + Type (Common Stock/ETF/Fund) + ISIN — replaces the 11-probe resolution dance AND doubles as the name-sweep/ETF check (same vendor as prices, so it verifies the price source's own mapping; keep yfinance/Exa for flagged names only). Use `exchange-symbol-list` (1 call/exchange) to pre-intersect before any universe expansion. Free bulk alternative: Stooq `q/d/l/` per-ticker CSVs + `stooq.com/db/h/` ZIP snapshots (12,000+ securities; API key via CAPTCHA since 2026; TSXV spotty) — fine as a bulk layer, EODHD search stays the verification layer.

12g. **Koyfin blocked-column extraction via logged-in browser + CDP (Aug 8 2026):** Koyfin CSVs never include Capital IQ-derived columns ("N/A for download" — display-only vendor license), but the browser renders them. Workflow: launch Playwright chromium VISIBLY on the WSL display (`DISPLAY=:0 chrome --user-data-dir=/tmp/koyfin_profile --force-renderer-accessibility --remote-debugging-port=9222 --remote-allow-origins=*`), user logs in once (session persists in the profile), then drive via CDP (`~/portfolio_audit/extract_all_screens.py`, helper `cdp.py`). The app's own pipeline: POST `/api/v1/screener/query/` (filters + `pageSize:2000`) returns matching kid IDs -> POST `/api/v3p/data/keys` returns FULL values (ticker, name, sector, industry, last price, market cap, ALL custom columns incl. FFO coverage, ROE, D/E, estimate revisions) in one ~330KB JSON — capture via `Network.getResponseBody` on the app's own request (no auth replication needed; the app's x-tab-id rotates but the app's own request carries it). Result: 5 screens extracted Aug 8 (Quality 221, Growth Momentum 136, Pure ER 172, OpEx 388, Revision+Quality 400) to `~/koyfin_browser_screens/*.csv` — every blocked column, with dates. Screen C anatomy from this: median FFO coverage 11.0x (low-debt tilt, NOT a real-asset tilt — sectors well spread), elite 5Y-Sharpe names 6/10 Industrials + 2 Energy. Raw fetch replays 403 without the current x-tab-id; DOM scraping works but is slow (virtualized rows); the Network-capture route is the efficient one. RE-LAUNCH (profile is now PERSISTENT — Aug 22 2026, fixed the /tmp wipe flaw): `DISPLAY=:0 ~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome --user-data-dir=~/portfolio_audit/browser_profile --force-renderer-accessibility --remote-debugging-port=9222 --remote-allow-origins=* --no-first-run --no-default-browser-check` — visible window, user logs into Koyfin once per profile (login now survives reboots), then `python3 extract_all_screens.py`. If Koyfin re-logs-out, the script's click_screen returns 'not found' — re-login in the window and re-run.

12h. **portfolio-api-workflow (Aug 9 2026)** — the holdings-list data workflow (financial data API workflow for holdings-list portfolio analysis; EODHD + yfinance patterns).

12i. **Recovering a Koyfin screen's filter spec when it's missing (Aug 22 2026 — user-corrected workflow):** if a screen's exact filters are needed and the saved screen is gone from the account, the recovery hierarchy is: (1) SESSION HISTORY FIRST — screen-build sessions list the exact filters with values (July 25 session specced the new 8 screens; June 5 specced the June batch); do NOT burn turns clicking through the browser when the user says the screen isn't in the app — the user is right, deleted screens stay deleted (Low Beta + High Return was dropped July 25 for Trend Quality, gone by Aug 22). (2) The export's column headers ARE the filter list — each header is a filter the screen uses (Beta (1Y), Tot. Return %/CAGR (5Y), ROE (LTM), P/E (NTM)). (3) Membership data reveals hard bounds: the max member value = the upper-bound filter, the min member = the lower-bound filter (recovered from the 287-member Low Beta export: Beta ≤ 0.80 exactly, 5Y CAGR ≥ 10% exactly). (4) Unknown thresholds (ROE/P/E here) can be RECONSTRUCTED by iteration: rebuild the screen with the known bounds + guesses, export, compare membership against the saved CSV (the fingerprint), tune until it matches — typically 2-3 cycles. Also: before ever claiming a data path is impossible ("no export-free way to get X from Koyfin"), check session history for tooling already built — the CDP network-capture extraction (12g) had solved exactly that problem on Aug 8 and a future session must not re-declare it impossible.

12j. **EODHD tier probing + ADR detection (Aug 23 2026):**
- Probe semantics: HTTP 200 = works on plan; 403 Forbidden = plan-blocked; 404 = wrong path/ticker (NOT a plan verdict); 422 = accessible but bad params (retry with correct params — e.g. calendar/dividends needs a filter array). Distinguish before concluding "plan doesn't cover it".
- Verified on the user's EOD-tier key: eod (prices), div, splits, exchange-symbol-list, search all 200. Blocked 403: fundamentals, quote, calendar/ipos, calendar/earnings, calendar/splits, historical-market-cap, technical, macro-indicator, economic-events, congressional-trades. UST/rates/news/sentiment paths 404 (wrong path or not on plan — check the MCP tool's actual path before trusting the 404). Note: fundamentals returns 403 Forbidden, not empty {} (supersedes the older "empty {}" note).
- exchange-symbol-list's Country field = LISTING country ("USA" for every NYSE name incl. TSM/TM/BABA) — useless for issuer country. Issuer country = ISIN prefix: non-US prefix = direct foreign listing; US prefix + "ADR"/"ADS" in Name or a vetted known-ADR list = ADR; CA = Canadian. The search endpoint also returns listing country only.
- Substring traps when detecting ADRs by name: 'ADS' matches Broadstone/Gladstone, 'ADR' matches Broadridge/Cadre — false positives; known-ADR lists go stale (BMY = Bristol-Myers is a US company, not an ADR). Verify flagged names individually before trusting a list.
- Scale: NYSE/Nasdaq host ~450-500 sponsored ADRs (Deutsche Bank 2023: 445 of 1,273 sponsored DR programs); the long tail and many giants (Nestle, LVMH, Roche, Samsung, Tencent, Nintendo, post-2008 bank delistees) are OTC-only. Siemens delisted NYSE May 2014 → SIEGY OTC. TFSA-eligibility follows the EXCHANGE listing, not the wrapper.

13. **EODHD VIX/index data**: VIX uses `VIX.INDX` suffix (not `VIX.US` or `^VIX`). Other indices: `SPX.INDX`, `DJI.INDX`. Generic rule: if ticker has no dot AND is not a stock, try `.INDX`.

12. **EODHD endpoint**: Use `/eod/` not `/e/`. Correct format: `https://eodhd.com/api/eod/{ticker}{suffix}?from={start}&period=d&api_token={KEY}&fmt=json`

13. **EODHD fundamentals require paid tier**: The $19.99/mo EOD plan is PRICES ONLY. The `/fundamentals/` endpoint returns empty {} on this tier. Need £59.99/mo ($75 USD) Fundamentals plan for PE, ROE, D/E, etc. Workaround: use yfinance `.info()` for fundamentals (free, no key needed, ~0.3s per ticker).

14. **EODHD key location**: Key file at `/mnt/c/Users/<user>/eod_key.env` (Windows side, contains the raw key). Also at `/mnt/c/Users/<user>/.eod_key`. Read with: `cat /mnt/c/Users/<user>/eod_key.env`. The `~/.eod_key` path (Linux home) does NOT exist — always use the Windows path.

15. **execute_code sandbox lacks data science packages**: The `execute_code` tool runs in a separate sandbox that does NOT have pandas, numpy, scipy, yfinance, or vectorbt installed. For any data analysis work (CSV parsing, price downloads, metric computation), write a `.py` file and run it via `terminal(command='python3 script.py')`. Do NOT use `execute_code` for data science — it will fail with ModuleNotFoundError and waste turns.

10. **Cache strategy**: Cache data to disk to avoid re-downloading. BUT for critical portfolio analysis, the user prefers FRESH data over cached — stale caches hide survivorship bias and miss recent delistings. When the user asks for a fresh analysis, delete the cache and re-download. Use EODHD for bulk (1 call/ticker, no pagination) — 900 tickers takes ~30 seconds with 8 threads. For quick spot-checks, cached is fine.

11. **EODHD API format**: `https://eodhd.com/api/eod/{ticker}.US?api_token={KEY}&from=2016-01-01&to=2026-07-12&period=d&fmt=json` — returns `adjusted_close` (split/dividend adjusted). Key at `/mnt/c/Users/<user>/.eod_key`.

12. **QuantStats vs manual calculation discrepancies (July 2026):** When computing Sharpe and Sortino, quantstats uses different formulas than typical manual implementations. Sharpe: quantstats uses `mean(daily_returns) / std(daily_returns) * sqrt(252)` (arithmetic mean), NOT `CAGR / vol` (geometric mean). Difference: ~5-10% understatement with geometric. Sortino: quantstats uses `sqrt(mean(min(r, 0)^2))` for downside deviation (includes zero-return days), NOT `std(negative_returns)`. Difference: ~10-15% understatement with the wrong formula. **Fix:** Always use `qs.stats.sharpe(ret, rf=0.0)` and `qs.stats.sortino(ret, rf=0.0)` instead of manual formulas. Verify by checking SPY 10Y Sharpe should be ~0.88. Default rf in quantstats is 0.0 (not 0.02).

13. **QuantStats column selection for EODHD data:** When loading EODHD CSVs for quantstats analysis, the `adjusted_close` column must be selected explicitly. The CSV columns are: `open, high, low, close, adjusted_close, volume`. Use `df['adjusted_close']` not `df.columns[0]` (which is `open`). Verify by checking NVDA's 5Y return — should be ~+25,000% (split-adjusted), not -61% (raw open). This bug affected 3 analysis scripts in July 2026 before being caught during self-audit.

14. **BIL returns bug — CRITICAL (July 2026):** When using BIL as a cash proxy in timing model backtests, you MUST use `bil.pct_change().dropna()` for returns, NOT the raw BIL price. BIL prices are $77-92 (dollar values), while BIL daily returns are ~0.0001 (percentage). Using raw prices as "returns" produces astronomically large compounded values and inf Sharpe ratios. This bug was found in the timing-model backtest and validation scripts (live environment). The fix is always:
```python
bil = load_cached('BIL')
bil_ret = bil.pct_change().dropna()  # NOT bil directly
```
Verify: BIL annual return should be ~2-4%, not 8000%+.

15. **Column selection pattern for EODHD CSVs:** Always use this pattern — never trust `df.columns[0]`:
```python
if 'adjusted_close' in df.columns:
    col = 'adjusted_close'
else:
    col = df.columns[0]  # fallback for non-EODHD data
```

16. **VIX data: use VIX.INDX from EODHD, NOT ^VIX from Yahoo (July 2026).** Yahoo's ^VIX data is unreliable (missing dates, stale values). EODHD's VIX.INDX has current data. Always verify VIX values are reasonable (typically 12-35 range). If VIX shows 0 or 100+, the data source is wrong.

17. **Correlation is portfolio-specific, not absolute (July 2026).** One candidate ETF had 0.258 corr to the holdings list but 0.489 corr to the correlation-aware portfolio; a managed-futures fund had 0.12 corr to SPY but 0.37 corr to the portfolio. Always measure correlation to YOUR specific portfolio holdings, not to a benchmark. The same ETF can be a good diversifier for one portfolio and a bad one for another.

18. **Timing model signals: compare PRICE to SMA of PRICE (July 2026).** The 200 SMA must be computed on adjusted_close prices, not returns. `spy_adj_close > spy_adj_close.rolling(200).mean()`. NOT `spy_returns > spy_returns.rolling(200).mean()`.

19. **MCP Exa debugging (July 2026):** Exa MCP server is Streamable HTTP at `https://mcp.exa.ai/mcp`. When MCP calls time out:

    **a) Check server reachability:** `curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "https://mcp.exa.ai/mcp"` — 405 = server up.
    
    **b) Test JSON-RPC handshake:**
    ```bash
    curl -s -X POST \
      -H "Content-Type: application/json" \
      -H "Accept: application/json, text/event-stream" \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
      "https://mcp.exa.ai/mcp?tools=web_search_exa,web_fetch_exa,web_search_advanced_exa"
    ```
    Returns server info (exa-search-server v3.2.1). The `Accept: application/json, text/event-stream` header is REQUIRED — without it, server returns "Not Acceptable."
    
    **c) Most common failure: missing `x-api-key` auth header.** Hermes MCP config MUST include headers with x-api-key. Use `hermes config set mcp_servers.exa.headers.x-api-key "KEY"` — can't edit config.yaml directly due to security restrictions. Key stored in `~/.hermes/.env` as `EXA_API_KEY`.
    
    **d) `web_search_advanced_exa` may timeout while `web_search_exa` works** — advanced search with domain filters is slower at 120s timeout. Fall back to basic search for quick queries.

1. Download Koyfin screen CSVs (free web UI)
2. Parse tickers from CSVs, count cross-screen appearances
3. Filter: in 2+ screens, in returns data, enough history (3Y+)
4. Enrich with Finnhub (fundamentals, estimates, recommendations)
5. Enrich with yfinance (PE, ROE, debt, growth, sector)
6. **Recover stale Canadian tickers:** EODHD sometimes has stale US OTC listings for Canadian stocks (e.g., CSU only had data to Feb 2022). Always check last date. If stale, delete cache and retry with yfinance using `.TO` suffix. In July 2026, this recovered 17 tickers including a top-5 composite candidate.
7. Run scoring formula: `Score = 5Y_Sharpe * 1.0 + 12M_return * 0.5 - AvgCor * 2.0`
8. Test swaps exhaustively (every candidate vs every holdings-list stock)
9. Validate with walk-forward backtest (2Y train, 1Y test)

## References

The sections above carry the distilled recipes for this skill's domain.

