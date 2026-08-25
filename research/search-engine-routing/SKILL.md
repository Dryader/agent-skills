---
name: search-engine-routing
description: "Use for every web search task; route engines automatically."
tags: [search, research, apis, routing]
triggers:
  - choosing a search API
  - search engine comparison
  - A/B testing search providers

---

# Search Engine Routing

Load this for every web search task. Decide the engine mix yourself from the task and query; never ask the user which engine to use or whether to escalate. Over-escalation is nearly free (~$0.01 per extra call); under-escalation is the only real risk, so default to the extra call whenever there is any sign the answer will be acted on.

## Default: Exa (5-6 results)

Routine lookups: general questions, definitions, background reading, current events, casual research.

## Automatic escalation signals (any one -> add a Parallel pass)

Detect these from the query and context yourself, without being told:

- **Proper name + claim or role** ("who is X", "is X really Y", background checks) -> verification pattern.
- **Money:** tickers, tax questions, prices, "should I buy/hold/sell" -> financial decision.
- **Products:** model numbers, device names, "best X", review comparisons -> product research; escalate when the user is choosing rather than browsing.
- **Security or enterprise:** controls, configs, deployments, anything that will be applied to systems -> high stakes.
- **Recency-sensitive content:** "latest/update/new/recent", or fast-moving domains (news, pricing, regulation, software releases) -> after the Exa pass, inspect result dates; escalate if they look old.
- **Claims phrasing:** "is it true that", "did X happen", "someone said" -> claims check.

## Post-pass quality check (always, no user input needed)

After the first Exa pass, escalate if results are thin: one domain family dominating, fewer than 3 distinct authoritative domains, or visibly stale dates. Also escalate when a fact from earlier in the conversation needs corroboration or a source was challenged.

## Disagreement

If Exa and Parallel conflict on a fact, bring in Tavily as the third opinion. Never blend conflicting sources into one answer without flagging the conflict.

## Verification protocol (when escalated)

1. Run the same query on Exa (5 results) and Parallel (5 results).
2. Expect low source overlap. A fact confirmed by both from disjoint sources is independent confirmation; state it as such.
3. On conflict, fetch the pages: Parallel `web_fetch` with an objective for clean excerpts, Exa `web_fetch_exa` for full markdown (YAML frontmatter noise on MS Learn pages).
4. Report agreement/disagreement explicitly.

## Brave (independent-index secondary)

Measured Aug 2026 (6 queries, top-10, harness round 2): own crawler, no Google/Bing in the pipeline. Fastest engine (0.8s), thinnest payload (240 ch/res; extra snippets are Pro-only), free ~$5 credit/mo (~1,000 req). Returns relative age strings, not published dates. Mid independence: 17% overlap with Exa, 12% Parallel, 9% Tavily. Thin snippets can miss facts other engines catch (3/4 answer containment vs 4/4 elsewhere). Use for cheap source diversity or context-constrained loops; never the default, and not a verification replacement for Parallel (Exa + Parallel stays the best diversity pair).

## Never

- Firecrawl search in loops (10 req/min cap, no dates, slow, redundant). Extraction only.
- Tavily as a default (redundant with Exa). Tiebreaker only.
- More than 1-2 Parallel calls per task (~58KB payloads each; they exceed the 50KB tool-output cap and get persisted to /tmp).
- Asking the user which engine to use, or whether to escalate. Make the call.

## Execution gotchas

- Dates: Firecrawl and Tavily return none; Exa and Parallel do. Date-based judgments need Exa or Parallel.
- Exa date params: use `startPublishedDate`/`endPublishedDate`; crawl-date params silently ignored since Apr 2026.
- Exa people/company search: strong, but raw matches carry ~39% false positives in the field; validate with a second source.

## Costs at a glance (all free at typical usage)

Exa $10/mo no-card credits; Parallel anonymous MCP; Tavily 1 credit per basic search (1,000 free/mo); Firecrawl 2 credits per 10 search results (1,000 free/mo); Brave $5/mo credit (~1,000 requests, then $5/1k).

To re-verify this policy: run `scripts/search_ab.py` from this skill against your own queries; method and prior data: see the Exa API docs.

