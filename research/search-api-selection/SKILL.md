---
name: search-api-selection
description: "Choose the search/scrape API for a research task: cost-aware selection across Tavily, Firecrawl, Exa, Brave and web_extract."
---


# Search API Selection

Not all search tools are equal. Pick the cheapest tool that does the job.
Exa is the default for research (semantic search finds academic sources Tavily misses).
Brave is the cheap fallback for quick factual lookups.

## Quick Decision

| Need | Tool | Cost |
|------|------|------|
| Research, academic sources, deep discovery | Exa semantic search | $0.007/query |
| Quick factual lookups, news | Brave Search | $0.005/query |
| Full page content (known URL) | `web_extract` | Free |
| Paywalled/JS-heavy page scraping | Firecrawl scrape | 1 credit |
| Structured JSON extraction | Firecrawl extract | 10-40+ credits |
| Page interaction (clicks/forms) | Firecrawl interact | Varies |

## Cost per query (pay-as-you-go)

- **Brave**: $0.005 — cheapest, own 30B+ page index, keyword-based
- **Exa**: $0.007 — semantic search, content included free with 10 results, best quality for research
- **Tavily**: $0.008 basic / $0.016 advanced — keyword-based, snippets only
- **Firecrawl**: 2 credits per 10 results on search; free tier = 1,000 cr/mo (no rollover), search capped at 10 req/min (Hobby raises to 100/min)

## The Default Research Pattern

```
1. Exa for semantic search discovery (finds academic papers, theses, studies)
2. web_extract for pulling full content from found URLs (free)
3. Brave as cheap fallback if Exa is unavailable
4. Firecrawl ONLY for JS-heavy sites or paywall bypass attempts
```

Never burn Firecrawl credits on tasks that free tools handle.

## Why Exa Wins for Research

Head-to-head testing (June 2026) searching for friendship/psychology research:
- **Exa found**: PubMed studies, university theses, 323K-participant cross-cultural studies, 2025 journal papers
- **Tavily found**: Blog posts, Reddit threads, Psychology Today articles
- Exa's semantic search understands MEANING, not just keywords
- Content is bundled free with search results (no separate scrape step)

## Parallel Search MCP (added Aug 2026)

Free anonymous tier at `https://search.parallel.ai/mcp` (no key, no account, hobby rate limits); an API key in the `Authorization` header raises limits and adds usage analytics. Configured in this profile as `parallel_search` (key pending). This server runs in `basic` mode and exposes only `web_search` + `web_fetch`; an OAuth/enforced-auth variant lives at `https://search.parallel.ai/mcp-oauth` (anonymous → 401).

Deep research, enrichment, FindAll and monitoring are NOT on that server. They are reachable two ways: the Task MCP at `https://task-mcp.parallel.ai/mcp` (API key required; createDeepResearch, createTaskGroup, getStatus, getResultMarkdown) or the `parallel-cli` binary (not installed here). Prefer the MCP server when one is needed — typed calls, no shell quoting.

Measured A/B vs Exa + Firecrawl (6 queries x 10 results, Aug 2026 — full dataset in `Reference: search-engine-ab-aug-2026`):

- Quality: statistical tie with Exa/Firecrawl on answer containment (4-5/5 factual probes in top-3).
- URL overlap with Exa only 5-25% (top-5 sometimes 0%) — engines are COMPLEMENTS, not substitutes. Use Parallel as a second opinion / source-diversity pass on verification hunts.
- MCP output: ~10 results, no count control, ~58KB per call (heavy for agent context vs Exa's compact highlights).
- Latency ~1.5-2.7s steady every call; Exa faster on warm cache (~0.2s).
- Ranking style: sometimes puts third-party explainers above canonical docs (Exa leads with primary sources more often).
- MCP web_search requires `objective` + `search_queries` (keyword-style), not a plain query; `session_id` used for free-tier rate limiting.

## Calling MCP tools in one turn
- **One MCP tool per `tool_call`.** Batching several `mcp__*` searches into a single `tool_call` is refused with "Local tools require one entry per tool_call; mixed and multi-local batches are not supported". Issue them as separate calls in sequence, or, when several searches should run in one shot, use `execute_code` with `hermes_tools.web_search` / `web_extract` (free, batched) and keep the MCP engines for the queries that benefit from semantic search.

## Pitfall: "X vs Y" comparison queries
Queries of the form "A vs B for <task>" return mostly agency, vendor and SEO content, including synthetic pages whose specifics are impossible (citing product versions that do not exist). Treat them as leads, not evidence:
1. Prefer practitioner sources for the verdict: forum and discussion threads, engineering blogs, and the vendors' own docs and pricing pages.
2. Version-check every concrete claim against the vendor before repeating it, and drop pages you cannot verify — say in the reply which sources you discarded and why.
3. Steel-man the losing side with its own query ("why choose <B> for <task>") so the recommendation is balanced; the strongest counter-argument usually shows up in a source that otherwise favours the alternative.

## Tavily: Not Worth Adding (verified Aug 2026)

Our stack (Exa MCP: search/advanced/fetch/agent_run; Firecrawl MCP: all tools except extract; web backend = Exa) covers Tavily's entire surface. No capability gap:

- `include_answer` (one-call cited answer): Exa has /answer endpoint; agent_run does it too
- `topic=finance`: NO ticker_symbol param in current OpenAPI — just a source bias. Exa Agent Connect Financial Datasets (27K tickers: prices, fundamentals, earnings, SEC filings) is the real structured option
- `/extract`: batch scraping 1 credit/5 URLs (cheaper than Firecrawl scrape for bulk) but NO schema support; Firecrawl scrape still does single-page schema extraction via formats:["json"]+jsonOptions
- Keyless mode (`X-Tavily-Access-Mode: keyless` header): free rate-limited search+extract, no account — only useful for scripts outside Hermes
- Risks: acquired by Nebius 2026 (roadmap uncertainty); tavily_research hangs on their MCP (#158); intermittent empty results (#143); 1,000 free credits/mo vs Exa's ~20K free requests

Verdict: skip Tavily.

## Exa MCP Setup

Exa MCP accepts either OAuth (interactive clients) or an `x-api-key` header — our config uses the header. Add to `~/.hermes/config.yaml`:
```yaml
mcp_servers:
  exa:
    connect_timeout: 30
    timeout: 800          # agent_run runs ~750s; the timeout must cover it
    url: "https://mcp.exa.ai/mcp?tools=web_search_exa,web_fetch_exa,agent_run,web_search_advanced_exa"
    headers:
      x-api-key: <EXA_API_KEY>
```
Tools available: `mcp__exa__web_search_exa`, `mcp__exa__web_fetch_exa`, `mcp__exa__web_search_advanced_exa`, `mcp__exa__agent_run` (tool selection is the `tools=` URL param — drop a tool there and it stops being callable)

## Exa Limitations

- **No anti-bot bypass**: Cannot crawl Cloudflare, CAPTCHAs, login walls, JS-heavy SPAs
- **Index-based**: Serves pre-crawled content, not live scrapes. Fresh content may lag hours.
- **Paywalled sites blocked**: Bloomberg, WSJ, FT, NYT — not in index, direct fetch returns SOURCE_NOT_AVAILABLE
- **Use `maxAgeHours: 0`** to force live crawl when freshness matters (costs same)

## Firecrawl MCP Credit Costs

- Search: 2 credits per 10 results; free plan caps at 10 req/min (429s in agent loops — pace ~35s); results carry NO publishedDate
- Scrape: 1 credit/page
- Extract: 10-40+ credits (LLM-powered, very expensive — tested 37 credits for one call)
- Crawl: 1 credit/page (adds up fast on multi-page)

## Pitfall: Blog Archive Pages

`web_extract` on author/archive pages (WordPress, Blogger, Ghost, etc.) often returns ALL posts concatenated into one blob without date separators or post boundaries. This is useless for "summarize the other posts by this author" tasks.

**Fix**: Use Exa `web_search_advanced_exa` with `site:` filter + `startPublishedDate`/`endPublishedDate` to discover individual posts. Exa returns each post as a separate result with full text included — no second fetch needed.

```
mcp__exa__web_search_advanced_exa(
  query="site:example.com",
  startPublishedDate="2026-01-01",
  numResults=20
)
```

This cleanly separates posts, includes dates, and bundles content. Works even when the blog has no sitemap or RSS.

**When to use this pattern**: "summarize all posts from year X", "what else did this author write", "get all articles from this blog" — any task that starts with an archive/author page URL.

## Pitfall: Source Files Come Back Mangled

`web_extract` (and rendered-page extraction generally) strips markup from source files — XML, WiX templates, plist, code — returning bare fragments that look like a successful fetch yet carry nothing usable. When the answer depends on exact syntax or identifiers in a repo file: list the directory via the GitHub contents API (`https://api.github.com/repos/<org>/<repo>/contents/<dir>`, works through web_extract), download the file raw with `curl -sL -o scratch.file https://raw.githubusercontent.com/...`, then read/grep it locally. Full recipe: `software-packaging-research` skill.

## Known Site Limitations

- Reddit: blocked by Firecrawl AND web_extract. Use browser or old.reddit.com JSON.
- Medium: paywalled, returns summary only.
- Facebook: needs auth for group posts.
- Bloomberg/WSJ/FT/NYT: paywalled, blocked from all index-based tools. Need browser + subscription.

See `Reference: search-api-comparison` for full pricing details and sources.

## Reference: search-api-comparison

# Search API Cost & Selection Guide (Updated June 2026)

## Pricing Comparison

### Exa (Pay-as-you-go, no subscription)
- Free: 1,000 requests/month (up to 20,000 on free tier)
- Search: **$7/1,000 requests** = $0.007/query (10 results with content included free)
- Deep Search: $12/1,000 requests
- Deep-Reasoning Search: $15/1,000 requests
- Contents endpoint: $1/1,000 pages
- Summaries: $1/1,000 summaries
- **March 2026 update**: contents for 10 results now bundled free with search
- Source: https://exa.ai/pricing

### Tavily (Credit-based plans)
- Free: 1,000 credits/month
- Pay-as-you-go: $0.008/credit
- Basic search: 1 credit ($0.008)
- Advanced search: 2 credits ($0.016)
- Research (mini): 4-110 credits ($0.032-$0.88)
- Research (pro): 15-250 credits ($0.12-$2.00)
- Plans: Project $30/mo (4K credits), Bootstrap $100/mo (15K), Startup $220/mo (38K)
- Source: https://docs.tavily.com/documentation/api-credits

### Brave Search API
- Free: 2,000 queries/month
- Pay-as-you-go: **$0.005/query** — cheapest option
- 30B+ page independent index, 100M+ page updates/day
- Subsidized by Brave browser business (not primary revenue)
- Source: https://brave.com/search/api/

### Firecrawl (Subscription only, no pay-as-you-go)
- Free: 1,000 credits/month
- Hobby: $16/mo (yearly) — 5,000 credits
- Standard: $83/mo (yearly) — 100,000 credits
- Growth: $333/mo (yearly) — 500,000 credits
- **Credits do NOT roll over** (except annual Scale/Enterprise)
- Search: 2 credits per 10 results
- Scrape: 1 credit per page
- Extract: 10-40+ credits (LLM-powered, tested 37 credits for one call)
- Source: https://www.firecrawl.dev/pricing

## Per-Query Cost (10 results)

| Service | Cost per search | Subscription required? |
|---------|----------------|----------------------|
| Brave | $0.005 | No |
| Exa | $0.007 | No |
| Tavily basic | $0.008 | No |
| Tavily advanced | $0.016 | No |
| Firecrawl | $0.002 | Yes ($16/mo min) |

## Architecture Differences

### Exa — Neural semantic search
- Own index + custom transformer embeddings
- Searches by MEANING, not keywords
- Pre-built index, serves cached content by default
- `maxAgeHours` param for freshness control (0 = always live crawl)
- Cannot bypass Cloudflare, CAPTCHAs, login walls
- No proxy infrastructure

### Brave — Traditional search engine
- Own 30B+ page index with own crawler
- Keyword + ranking based (like Google/Bing)
- Partly powered by Web Discovery Project (opt-in browser user data)
- Privacy-first, no tracking
- Subsidized by browser business

### Tavily — Hybrid aggregator
- Combines own crawler with third-party data
- Keyword-based search
- Returns concise answers with citations
- Stale link problems, JS limitations

### Firecrawl — Live scraping engine
- Scrapes on demand (not pre-built index)
- Handles JS-rendered SPAs, can click/fill forms
- Needs proxy infrastructure for anti-bot bypass
- Most expensive, subscription-only

## Research Quality Comparison (Tested June 2026)

Query: "friends neglecting friendships for romantic relationships psychology research"

**Exa found:**
- Roth & Parker (2001) PubMed study — 53% of girls, 32% of boys report being neglected
- 2025 Personal Relationships journal study — real-time tracking vs retrospective perception
- University of Iowa thesis on "amatonormativity" — cultural bias toward romantic relationships
- Frontiers in Psychology — 323,200 participants, 99 countries study
- Tufts University thesis on friendship undervaluation

**Tavily found:**
- Psychology Today blog post (Dunbar's study)
- Ball State Daily News opinion piece
- Reddit threads
- Refinery29 personal essay

**Conclusion:** Exa's semantic search surfaces academic/peer-reviewed sources. Tavily surfaces blog posts and popular articles. For research tasks, Exa is significantly better.

## Limitations by Tool

| Limitation | Exa | Brave | Tavily | Firecrawl | web_extract |
|-----------|-----|-------|--------|-----------|-------------|
| Cloudflare bypass | No | No | No | Partial | No |
| Paywalled sites | No | No | No | Partial | No |
| JS rendering | No | No | No | Yes | No |
| Live crawling | Yes (maxAgeHours) | No | No | Yes | Yes |
| Reddit | Partial | Yes | Partial | No | No |
| Bloomberg/WSJ | No | No | No | Partial | No |

## Reference: search-engine-ab-aug-2026

# Three-Engine Search A/B — Aug 2026 (Exa vs Parallel vs Firecrawl)

Measured on 6 queries x 10 results per engine, identical intent, same week.
Queries: Canada capital gains 2026 / Hugging Face CTO / WDAC vs AppLocker /
SQLAlchemy async expire_on_commit / IEMs under $200 / Windows 11 KB5101684.

## Answer containment (fact present in top-3 excerpts)

| Query | Parallel | Exa | Firecrawl |
|---|---|---|---|
| capital gains rate (50%) | True | True | True |
| HF CTO (Chaumond) | True | True | True |
| WDAC "servicing criteria" | False (rank 4-5) | True | True |
| expire_on_commit=False | True | True | True |
| KB5101684 builds | True | True | True |

## URL overlap (Jaccard, top-10 | top-5)

| Query | PvE | FvE | FvP |
|---|---|---|---|
| capital gains | 5% / 11% | 18% / 25% | 5% / 11% |
| HF CTO | 25% / 25% | 33% / 11% | 11% / 11% |
| WDAC | 18% / 11% | 33% / 11% | 18% / 11% |
| SQLAlchemy | 11% / 25% | 33% / 25% | 11% / 25% |
| IEMs | 5% / 0% | 18% / 11% | 5% / 0% |
| KB5101684 | 5% / 0% | 18% / 11% | 0% / 0% |

Takeaway: 5-33% overlap everywhere; canonical convergence only on exact-KB
lookups (both engines returned the same support.microsoft.com page as #1).

## Payload & latency (10 results each)

| Engine | chars/result | total (60 res) | lat mean | lat min-max |
|---|---|---|---|---|
| Parallel | 2,264 (p50 929, p90 9,145) | 136KB | 1.9s | 1.5-2.7s |
| Exa | 2,768 (p50 1,891, p90 7,892) | 166KB | 1.3s | 0.9-2.1s (0.2s warm-cached) |
| Firecrawl | 1,016 | 61KB | 4.3s | 0.9-8.1s (cached vs live fetch) |

Token-efficiency myth: Parallel's "3-5x payload" claim was an artifact of
comparing its fixed 10 results vs 5-result Exa calls. At equal counts Exa is
slightly larger. Parallel MCP's real cost: no result-count knob (always ~10,
~58KB/call — trips Hermes tool_output 50KB persisted-output threshold).

## Chrome-led excerpts (excerpt STARTS with nav/membership/YAML junk)

Parallel 6/60, Exa 1/60, Firecrawl n/a (meta-description style). Round-2
"mostly junk" characterization was overstated — noise is real but concentrated
in hub pages / frontmatter, not the average result.

## Metadata

- Exa: publishedDate on most results (3-10/10 by query type).
- Parallel: publish_date 6-9/10, more on people/org pages.
- Firecrawl: NO date field at all (0/60). Disqualifies it for freshness work.

## Firecrawl operational quirks (verified this session)

- Account on FREE plan: 1,000 cr/mo, no rollover, search 10 req/min hard cap
  (429 at 11 req/min). Hobby = 100/min. Check balance:
  `GET https://api.firecrawl.dev/v2/team/credit-usage` (Bearer key) —
  returns remainingCredits / planCredits / billingPeriod.
- v1 REST search rejects MCP-wrapper keys (`sources`, `highlights`) — 400
  "unrecognized_keys". Response `data` is a LIST of results, not `{web: [...]}`.
- Search = 2 credits per 10 results; scrape = 1 credit/page.
- Latency is fetch-bound: cached 0.9s, live crawl 8.1s.

## Parallel MCP schema notes

- `web_search`: required `objective` (natural language) + `search_queries`
  (2-3 keyword queries). Optional `session_id` (32+ hex, reused across calls —
  free-tier rate limiting), `model_name` (analytics only).
- `web_fetch`: urls + optional objective/search_queries for excerpt focus;
  `full_content: true` for whole-page markdown.
- REST: `POST https://api.parallel.ai/v1/search` with `x-api-key` header.
- Raw HTTP clients get Cloudflare 403 (error 1010) without a browser UA;
  Hermes' own MCP client passes fine.

## Verdict

Quality: tie. Use Exa for dense default search (highlights, primary-source
ranking, count control, warm cache). Use Parallel (free, anonymous) when a
hunt needs a genuinely different source set. Use Firecrawl for extraction —
its search mode is its weakest hat (no dates, slow, rate-capped).
