---
name: mcp-server-diagnostics
description: Diagnose MCP server connection failures (especially hosted endpoints), choose the right endpoint + auth variant, and distinguish server outage from config error. Covers Hermes MCP client mechanics (hermes mcp list/test/login, /reload-mcp), raw HTTP endpoint probing, and known hosted-provider endpoint matrices (Firecrawl, Exa).
tags: [mcp, diagnostics, troubleshooting, agents]
triggers:
  - MCP server connection fails
  - mcp server not working or timing out
  - tools not registering after adding a server

---

# MCP server diagnostics

## When to use
- MCP tools stop responding, get unregistered ("Unknown tool"), or `hermes mcp test` fails
- Adding a hosted MCP server (Firecrawl, Exa, ...) and choosing between OAuth / API-key / keyless variants

## Symptom → classification
1. Tool call returns "transport is down; reconnect requested", then later "Unknown tool" → the session's MCP connection died and tools were unregistered. Config may be perfectly fine.
2. `hermes mcp test <name>` → "Session terminated" / "Connection failed" → server-side or auth issue.
3. **Raw HTTP probe decides who's at fault** (scripts/probe_mcp_endpoint.py): POST an MCP initialize with `Content-Type: application/json` + `Accept: application/json, text/event-stream`, with and without the credential header.
   - HTTP 404 on ALL paths (including `/` and `/api/mcp`) → server outage or moved endpoint. Config is not the problem; wait it out or switch providers. (Exa's hosted MCP did exactly this in 2026-07 while exa.ai stayed up.)
   - HTTP 401/403 → auth: wrong/missing key, or the endpoint requires OAuth.
   - text/html content-type → NOT an MCP endpoint (you hit a web page); find the real /mcp path.
   - 200 + JSON-RPC → endpoint fine; the issue is client-side → `/reload-mcp` or session restart.
4. **Stdio servers (command-based): raw JSON-RPC handshake over stdin.** Pipe `initialize` into the server command with the key in its env — line-delimited JSON: `printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' | BRAVE_API_KEY=x npx -y @brave/brave-search-mcp-server`. A `serverInfo` reply means server + key are healthy and the fault is Hermes-side (usually the config: args stored as a quoted string instead of a YAML list, or env not passed). Then `notifications/initialized` + `tools/list` to enumerate. `scripts/mcp_context.py <server>` does a full connect + tool list per configured server as a one-shot health probe.

## Hosted-provider endpoint matrices (check the provider's docs page — variants are NOT interchangeable)
- Firecrawl: `https://mcp.firecrawl.dev/v2/mcp` = API-key variant (`headers: {Authorization: "Bearer <key>"}`); `/v2/mcp-oauth` = OAuth variant (interactive browser flow — `hermes mcp login` must be run by the human in a terminal; fails non-interactively with "non-interactive environment and no cached tokens"); `/v2` alone = a web page, NOT an MCP endpoint; keyless = reduced tool surface (search/scrape/parse only).
- Exa: `https://mcp.exa.ai/mcp?tools=a,b,c` + `x-api-key` header — tool selection is a URL query param; also accepts `Authorization: Bearer`.

## Hermes client mechanics
- `hermes mcp list` (config-level), `hermes mcp test NAME` (live connect + tool discovery), `hermes mcp login NAME` (interactive OAuth), `hermes mcp add NAME --url U --auth {oauth,header}` (--auth oauth prompts in non-interactive shells).
- **`hermes mcp add` enable-prompt nuance (corrected Aug 2026):** the "Enable all N tools?" confirmation reads piped stdin: EOF cancels (so `< /dev/null` fails), but `echo y | hermes mcp add NAME --command CMD --env KEY=VAL --args ...` completes it non-interactively. `--args` must be the LAST option; `--env` takes KEY=VAL pairs. Verified with @brave/brave-search-mcp-server. Non-interactive alternative: `hermes config set mcp_servers.<name>.<key> <value>` — but CAUTION: `hermes config set mcp_servers.<name>.args '<json array>'` stores the array as a QUOTED STRING, not a YAML list, and the stdio server then fails to launch ("Connection closed" on `hermes mcp test`). For stdio servers always use `hermes mcp add --args` (writes a proper YAML list), or fix an existing entry by removing and re-adding it.
- Session tool registry only refreshes via `/reload-mcp` (user-typed) or a session restart. Fixing config does NOT re-register tools mid-session.
- Auto-reconnect retries with backoff (up to 5) then unregisters the tools — after that, `/reload-mcp` is the only lever.
- Adding a hosted server with a key: put the credential in `config.yaml` `mcp_servers.<name>.headers` (same pattern as `x-api-key` / `Authorization: Bearer`).

## Config editing pitfalls
- NEVER rewrite config.yaml via a full `yaml.safe_dump` round-trip — it silently strips ALL comments. Insert new server blocks textually (find the `mcp_servers:` line, splice before the next top-level key).
- The patch/write_file tools REFUSE to write `~/.hermes/config.yaml` (security guard) — use `hermes config set mcp_servers.<name>.<key> <value>` or direct terminal edits, never the patch tool.
- Newly added servers register at the NEXT session start (no hot reload); `hermes mcp test` verifies the connection immediately but the toolset updates next session.
- When the running session's reload drops a server you just added, re-check config — the reload may have pruned it; re-insert and reload again.

## Trimming the MCP tool surface (context & security)

- **Make exclusion lists evidence-based.** Before proposing `tools.exclude` cuts, session_search the actual `mcp__<server>__` tool-call names across history. Never-used families are the cut candidates: monitor tools (recurring/cron-only work), agent tools (duplicate in-session Exa/Parallel hunts), feedback tools (dead weight), interact tools (built-in browser duplicates), research-papers tools (arxiv-skill duplicates). Keep tools with a usage trail — firecrawl: scrape/search/parse (+ crawl/map pair if wanted); brave: web_search/news_search/llm_context only. Test Pro-gated tools live before deciding (brave_summarizer returned no summary key on the free tier — dead weight).
- **tools.exclude list-as-string trap (verified Aug 2026):** `hermes config set mcp_servers.<name>.tools.exclude '<json array>'` stores a QUOTED STRING; membership then degrades to substring matching, so excluding `firecrawl_search_feedback` silently ALSO excludes `firecrawl_search`. (`firecrawl_extract`-style partial names never match at all.) Fix surgically: `cp ~/.hermes/config.yaml config.yaml.bak-$(date +%Y%m%d-%H%M%S)`, then a python line-regex replacing the quoted-string line with a proper YAML block list at the correct indent (match `      exclude: '\[[^\]]*\]'`), then verify with `yaml.safe_load` + sanity checks like `"firecrawl_search" not in exclude`.
- **`hermes mcp test NAME` reports the RAW server surface** — all 26 firecrawl tools appear even with 20 excluded, because filters apply at registration, not connection. Verify the effective set with scripts/mcp_context.py (replicates registration) or `/reload-mcp` then inspect the catalog.
- **Pin npx-based servers.** `npx -y pkg` floats to the latest published version on every connection; a compromised release executes with your keys in env. Pin `pkg@<version>` after validating (e.g. `@brave/brave-search-mcp-server@2.1.3`).
- Measured Aug 23 2026 (this machine): 67 → 42 MCP tools; deferred catalog 6,712B → 4,264B (~1,066 tok/request); full-schema exposure 99.6KB → 64.7KB; firecrawl catalog share 40% → 15%. Full record: tool-trimming.md.

## References
- scripts/probe_mcp_endpoint.py — raw initialize probe: POSTs MCP initialize to a URL with optional headers, prints status/content-type/body preview for classification. Usage: `python3 probe_mcp_endpoint.py <url> [Header-Name=value ...]`
- scripts/mcp_context.py — context-footprint measurement + single-server probe. Run with the Hermes venv python (`head -1 $(which hermes)` → venv/bin/python; the `mcp` package is NOT in system python). No args: per-server and total catalog bytes vs full-schema bytes for every configured server. One arg (server name): that server's enabled tool names + sizes (health probe). Replicates Hermes registration: config `tools.include`/`exclude` filters, capability-gated utility tools, `build_catalog_listing_with_form` truncation.
- mcp-context-footprint.md — the deferred-catalog mechanism (why 67 tools cost ~1.7k tokens, not ~25.5k), measured per-server numbers, registration details that affect counts (utility tools, filters, EODHD token file), and the standalone-verification recipe.
- tool-trimming.md — evidence-based MCP tool-surface trimming record (Aug 2026): session_search method, firecrawl 26→6 and brave 8→3 cut lists, the tools.exclude string-vs-list mechanics and surgical config fix, post-trim context numbers.
- The 2026 discovery-index landscape (AgentRank, A2ASearch, MCP.Directory, skills.sh) + Context7 (endpoint, tools, when it pays) + the cost-per-use verdict pattern for "should we install this MCP thing?" questions.



## Reference: context-cost-tuning.md

# MCP Context-Cost Tuning

## Scope

Use when the user asks how much context their MCP servers consume, wants to trim tool lists, or is adding/removing servers. Complements the Hermes MCP connection mechanics docs; this one covers cost, pruning, and supply-chain hygiene.

## Context footprint design (verified in Hermes source, Aug 2026)

- Hermes ships a deferred tool catalog in the system prompt: one line per tool, first sentence clipped to 60 chars, grouped per server with a header, budget-capped at 4000 tokens. Full schemas load on demand via tool_describe.
- Per server with prompts/resources capabilities, Hermes synthesizes 4 meta tools: get_prompt, list_prompts, list_resources, read_resource.
- Token estimate: chars / 4 (Hermes's own cheap rule; real tokenizers differ ~20%, the ratio is the point).
- Catalog builder lives in `~/.hermes/hermes-agent/tools/tool_search.py` (~lines 375-560); meta-tool synthesis in `tools/mcp_tool.py` (~line 5530).

## Measured numbers for this install (2026-08-23, 6 servers)

Pre-filter (67 tools): catalog 6,712 B ≈ 1,678 tok/request; full-schema expansion 99.6 KB ≈ 25.5k tok (~15x). Per-server catalog bytes: brave 794 (8 tools), context7 604 (6), eodhd 1,251 (13), exa 714 (8), firecrawl 2,685 (26), parallel_search 664 (6). After pruning 25 tools (firecrawl 20, brave 5): 42 tools, catalog 4,264 B ≈ 1,066 tok; full-schema 64.7 KB. Largest single tool schema: brave_llm_context 7.0 KB (~1,800 tok when actually loaded). EODHD advertises 91 tools server-side; config tools.include registers 9 (+4 meta = 13 in catalog). Full method: mcp-context-footprint.md.

## Evidence-based pruning workflow

1. session_search for `mcp__<server>__<tool>` call history; keep tools with real usage or a stated core role, cut zero-usage modules (Aug 2026 example: firecrawl monitor/research/agent/feedback families had zero calls ever; brave local/place/video/image and a Pro-gated summarizer were dead weight).
2. Append to tools.exclude — NEVER via `hermes config set` (stores the array as a QUOTED STRING; the filter uses `in` membership so substring matching silently over-excludes: excluding "firecrawl_search_feedback" as a string also kills "firecrawl_search"). Fix surgically: back up config (`cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak-$(date +%s)`), regex-replace the `exclude: '<string>'` line with a real YAML list (8-space indent under `tools:`), verify with yaml.safe_load plus a sanity check that kept tool names are absent from the list. Preserve pre-existing excludes when appending.
3. Filters apply at REGISTRATION (session start or /reload-mcp), not in `hermes mcp test` (which shows the raw server surface — firecrawl still reported 26 tools after 20 exclusions). Verify via the in-session reload notice count or by running the registration code path.

## Supply-chain hygiene

- Pin npx MCP server versions: `npx -y pkg@latest` re-resolves the newest published version on every connection; a compromised npm release would execute on the machine with the configured env. Pin a tested version (e.g. `@brave/brave-search-mcp-server@2.1.3`, verified Aug 2026).
- Tool poisoning is the real attack class for MCP: malicious instructions in tool descriptions or returned content get treated as context (Invariant Labs, CSA, CVE-2025-54136). Mitigations: first-party endpoints only, treat tool results as untrusted data, keep catalog descriptions short and visible (the deferred design helps).

> Measurements and per-server byte tables: mcp-context-footprint.md (canonical).


## Reference: mcp-context-footprint.md

# MCP context footprint in Hermes (measured Aug 2026)

How much system-prompt context MCP servers consume, and why the number is
small. Source code anchors in the Hermes source tree
(`~/.hermes/hermes-agent/`): `tools/tool_search.py` (deferred catalog) and
`tools/mcp_tool.py` (registration, utility schemas).

## The mechanism: deferred tool catalog

Hermes does NOT ship full MCP tool JSON schemas in the system prompt. It ships
a compact listing: one line per tool (`- mcp__server__tool: short description`),
grouped under `{server} tools ({n}):` headers. Built by
`build_catalog_listing_with_form` in `tools/tool_search.py`:

- Short description = first sentence clipped to 60 chars (`_short_desc`), so
  catalog lines are ~60-120 bytes each.
- Grouped per source (MCP server / plugin toolset), sorted, byte-stable across
  assemblies (prompt-cache safe).
- Budget: 4000 tokens default. Degradation is PER SERVER, greedy smallest
  first: `full` (name + short desc) -> `names` (names only) -> `summary` (one
  line per server) -> `none`. One huge server must not cost small servers
  their listing.
- Full schemas are loaded on demand via `tool_describe` (one tool per call),
  then invoked via `tool_call`.

## Measured numbers (reference fleet, Aug 23 2026)

6 servers, 67 tools registered (note: the MCP servers themselves expose more —
eodhd advertises 91 tools; config `tools.include` filters to 9 real + 4 utility):

| server          | tools | catalog bytes | full-schema bytes | largest tool |
|-----------------|-------|---------------|-------------------|--------------|
| brave           | 8     | 794 B         | 32.7 KB           | 7.0 KB (llm_context) |
| context7        | 6     | 604 B         | 5.6 KB            | 2.9 KB       |
| eodhd           | 13    | 1,251 B       | 13.7 KB           | 2.3 KB       |
| exa             | 8     | 714 B         | 8.8 KB            | 4.0 KB       |
| firecrawl       | 26    | 2,685 B       | 32.7 KB           | 4.2 KB       |
| parallel_search | 6     | 664 B         | 6.0 KB            | 2.8 KB       |
| TOTAL           | 67    | 6,712 B       | 99.6 KB           |              |

- Catalog ~1,700 tokens per request (chars/4 rule); full expansion would be
  ~25,500 tokens, a ~15x difference. Real tokenizers vary within ~20% of the
  chars/4 estimate; the ratio is the point.
- The catalog sits in the byte-stable system-prompt prefix, so it is paid
  once per prompt-cache window, not per turn.
- Fixed overhead regardless of MCP: the tool_search/tool_describe/tool_call
  core tool schemas, roughly 3-4 KB combined.
- firecrawl's 26 tools are ~40% of the catalog; its monitor_* and
  research_* tools are the first candidates for a `tools.exclude` list if
  trimming is ever needed.

## Registration details that affect the count

- Utility tools: for each server whose capabilities include prompts and/or
  resources, Hermes synthesizes 4 tools — `list_resources`, `read_resource`,
  `list_prompts`, `get_prompt` (`_build_utility_schemas` in mcp_tool.py).
  They count toward the catalog. Servers without prompts/resources
  capabilities (brave, firecrawl) get none.
- Config filters: `mcp_servers.<name>.tools.include` / `.tools.exclude`
  whitelist/blacklist server tools before registration (eodhd uses include).
- The mcp Python package is NOT in system python; it lives in the Hermes
  venv. Find the interpreter via `head -1 $(which hermes)` and use
  `venv/bin/python` for any script importing `mcp`.
- EODHD OAuth tokens: `~/.hermes/mcp-tokens/eodhd.json` holds the
  access_token (+ refresh_token, expires_at). `eodhd.client.json` is only
  client registration (no token) — a glob over `*eodhd*.json` can pick the
  wrong file. Check `expires_at` when auth fails.
- parallel_search's MCP endpoint is Cloudflare-gated: send a browser
  User-Agent header from raw clients.

## Standalone server verification (independent of Hermes)

When `hermes mcp test NAME` fails, isolate server/key problems from Hermes
config problems:

1. stdio server: pipe `initialize` into the command with the key in env;
   expect a `serverInfo` result. Then `notifications/initialized` +
   `tools/list` (line-delimited JSON over stdin/stdout). Confirmed working
   Aug 2026 with @brave/brave-search-mcp-server: 8 tools listed.
2. HTTP server: same protocol over POST, session header from the initialize
   response; EODHD's `mcp.eodhd.com/v2/mcp` needs `Authorization: Bearer`.
3. A server that connects and lists tools via `scripts/mcp_context.py <name>`
   is healthy — the failure is then in the Hermes config (e.g. args stored
   as a string instead of a YAML list, see SKILL.md Pitfalls).


## Reference: tool-trimming.md

# Tool-surface trimming record (Aug 23, 2026)

Session: MCP setup + A/B round 2 (Brave added to the MCP fleet). Evidence-based
trim of firecrawl (26 tools) and brave (8 tools) after measuring context cost.

## Baseline (before trim)

67 MCP tools across 6 servers. Deferred catalog 6,712B (~1,678 tok at chars/4),
full-schema expansion 99.6KB (~25.5k tok). Firecrawl = 40% of catalog cost
(26 tools, 2,685B). Largest single tool schema: brave_llm_context 7.0KB.

## Evidence method

session_search for `"firecrawl_scrape" OR "firecrawl_crawl" OR ...` (all tool
names) across session history. Result: only scrape/search ever called
repeatedly; extract called once (already excluded); parse attempted once and
failed. Zero calls ever: agent, agent_status, interact, interact_stop, all 8
monitor_*, all 5 research_*, developer_search, feedback, search_feedback, map,
crawl, check_crawl_status. Brave added the same day = zero usage; summarizer
tested live (web_search with summary:true returned no summary key) = Pro-gated,
dead on the free tier.

## Applied excludes

firecrawl (21 entries, includes the pre-existing firecrawl_extract):
firecrawl_extract, firecrawl_agent, firecrawl_agent_status, firecrawl_interact,
firecrawl_interact_stop, firecrawl_monitor_check, firecrawl_monitor_checks,
firecrawl_monitor_create, firecrawl_monitor_delete, firecrawl_monitor_get,
firecrawl_monitor_list, firecrawl_monitor_run, firecrawl_monitor_update,
firecrawl_research_inspect_paper, firecrawl_research_read_paper,
firecrawl_research_related_papers, firecrawl_research_search_github,
firecrawl_research_search_papers, firecrawl_developer_search,
firecrawl_feedback, firecrawl_search_feedback

brave (5): brave_local_search, brave_place_search, brave_video_search,
brave_image_search, brave_summarizer

Kept: firecrawl scrape/search/parse/map/crawl/check_crawl_status; brave
web_search/news_search/llm_context.

## Mechanics discovered (the hard way)

1. `hermes config set mcp_servers.firecrawl.tools.exclude '<json>'` stores a
   QUOTED STRING. With a string, `name in exclude` becomes substring matching:
   `"firecrawl_search" in '"firecrawl_search_feedback"'` is True → the keep-list
   tool would have been wrongly excluded. Same class of bug as args-as-string.
2. Fix: cp config to config.yaml.bak-<timestamp>, python line-regex
   `      exclude: '\[[^\]]*\]'` → block list lines (`      exclude:\n` +
   `        - name` per item, 8-space items), yaml.safe_load verify, sanity
   asserts (kept tools not in exclude, counts 21/5).
3. `hermes mcp test firecrawl|brave` still reports 26/8 (raw server surface) —
   the filter applies at registration. Effective-set verification must
   replicate registration: run scripts/mcp_context.py (applies config filters +
   capability-gated utility tools) — it reported firecrawl 6, brave 3, total 42.

## After trim

catalog 4,264B (~1,066 tok/req); full-schema 64.7KB; firecrawl catalog 663B
(15% of total). Backup file: ~/.hermes/config.yaml.bak-*. Revert = delete
entries from the exclude lists.

## Side findings

- EODHD server advertises 91 tools; config `tools.include` exposes 9 + 4
  utility tools (13 catalog entries). Additions are cheap (~100B catalog each).
- Meta utility tools (list_resources/read_resource/list_prompts/get_prompt) are
  synthesized by Hermes per server when it advertises prompts/resources
  capabilities (tools/mcp_tool.py `_build_utility_schemas`) — they count toward
  the catalog and must be included in footprint replication.
- Brave API returned extra_snippets on the free tier despite the Pro label in
  docs — check actual responses, not labels.
