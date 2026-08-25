---
name: agent-tool-evaluation
description: "Use when the user asks if a tool or system is worth adding."
tags: [tooling, evaluation, mcp, memory, skills, adoption, cost-per-use]
triggers:
  - deciding whether to add a tool or MCP server
  - is this tool worth adding
  - tool or MCP evaluation

---

# Agent Tool Evaluation

When the user asks "would X help us?", "is X worth adding?", "what about X?" — treat it as an evaluation task with a VERDICT, not a research report. The user is cost-per-use disciplined, verification-first, privacy-first, and artifact-centric. They expect: verify current state, measure the actual need, name the real harms, a verdict with concrete triggers for when it flips, and restraint as the default. Most surveyed tools get declined — that is the correct outcome of the method, not a failure. The user rewards honest "no"s backed by measurements.

## The Method (in order)

1. VERIFY CURRENT STATE — never answer from training memory. Tools drift (Context7, Serena, Hindsight all changed materially in 2025-2026). Use Exa MCP / web first. Also verify assumptions about the user's OWN stack: deepseek-v4-flash-0731 is frontier-class (AA Intelligence Index 50, GDPval-AA v2 Elo 1559, Aug 2026) — "flash" ≠ weak. Never frame the user's model as weak without checking; the user WILL correct you.
   CHECK COMMUNITY SENTIMENT, not just READMEs — after repo metadata + README (GitHub API: stars/license/pushed_at/archived), search what independent people say: Exa advanced search with excludeDomains = github.com + the project's own site/blog/docs, plus parallel_search as second opinion. Look for critical reviews, HN/Reddit threads, filed issues, security advisories. Seller pages and SEO content mills don't count; watch for name collisions (unrelated products with the same name pollute results — semantica collides with a language course and a Jina plugin). Large persisted results: scripts/extract_persisted_mcp_results.py.

2. GROUND IN SESSION WORK, NOT THE DAY JOB — user correction (Aug 2026): "use my sessions for context". Tool fit is judged against what sessions actually do (portfolio research/backtests, skills, memory workflows), NOT the user's [employer] role — unless the work lens is explicitly requested. Run session_search (browse + targeted queries) before judging fit.

3. MAP TO THE MEASURED WORKFLOW — the pain-inventory gates:
   - Gate 1 — pain inventory: can the user name 3 concrete recent failures the current stack caused? If not, STOP. Re-check in months.
   - Gate 2 — shape the pain: keyword-shaped (session_search covers it), semantic (a provider helps), procedure-shaped (a SKILL problem — memory systems make drift worse, not better), verification-shaped (scripts + sources, not memory).
   - Gate 3 — if passed: 30-day trial with a contamination audit (planted known-fact checks + trap questions; count recall wins vs confidently-fabricated answers).
   - Gate 4 — correction test: can garbage be fixed permanently, or does it resurface?
   - Gate 5 — keep/drop: ≥1 prevented re-explanation/week that session_search provably couldn't catch, AND contamination rare + correctable. Drop if either fails.

4. RUN THE CORPUS AUDIT for memory/recall questions — scripts/session_corpus_audit.py (counts, span, source mix, FTS phrase scans for cross-session recall needs and re-explanation complaints). Measured baseline (Aug 2026): a corpus spanning months of sessions, recall-need phrases in a small fraction of them, user is artifact-centric (decisions leave the conversation → skills/repos). Memory systems consistently fail the gates on this corpus. When the audit says no, the data IS the answer.

5. NAME THE REAL HARMS, SIZED:
   - Perpetual context/token tax — every session, used or not (small at deepseek prices, never zero).
   - Duplicate-tool pollution — the biggest quality risk: never wire a server that duplicates native tools (read_file/search/shell/terminal); use single-project / trimmed contexts. This is the filesystem-MCP and full-context-Serena trap.
   - Ops surface — processes, indexing, config artifacts (.serena/project.yml etc.), startup failures.
   - Work-style influence — semantic shortcuts quietly replacing careful reading; small but real for verification-first users.
   Every harm is bounded and reversible; the honest counterweight is the harm of NOT having it (setup delay when the trigger fires). Give the user the wiring that minimizes harm, then let them decide — no persuasion after the verdict.

6. VERDICT + TRIGGERS — never leave "no" as a dead end: name exactly what flips it ("add it the day you clone a big unfamiliar repo", "revisit when you log 3 session_search failures", "if you ever use Figma, Framelink is the add"). The trigger IS the answer to "so when would we need it?".

## Verified landscape (Aug 2026) — Aug 20 2026 additions: mattpocock/skills, OpenViking, semantica (session-work fit)

- Memory systems: Hindsight (benchmark leader, independently reproduced by Virginia Tech + Washington Post, fact/belief separation with confidence + provenance, already installed as a Hermes memory plugin — the pick if ever triggered); cognee (embedded graph, the document-corpus pick); Zep/Graphiti (temporal — but you operate a graph DB, and it measured 7% on MAB FactConsolidation: temporal-KG complexity does not help conflict resolution); mem0 v3 (append-only; gave up write-time conflict resolution); Letta (a full agent RUNTIME — replaces Hermes, not an add-on; disqualifier is architectural, not quality).
- Memory contamination is real and measured: HaluMem (<50% correct update rates across systems), ConsistencyGate (write-time gates cut contamination 20-62% but consistency ≠ correctness), MAB FactConsolidation (7-18% for the best systems). Retrieval surfaces memories as facts — that's the danger.
- Hermes memory: 7 provider plugins installed but inactive BY DESIGN (`hermes memory status` lists them; `hermes memory setup` enables one). Default-off reasons: keys/cost, privacy, third-party dependency, provider choice, and the bounded-curated memory file preserving prefix caching. Enabling is a consent decision, not a default — even "local" providers still need an LLM key and extraction behavior changes every session.
- Discovery directories: AgentRank (ranked by GitHub signals, has type=skill), A2ASearch (MCP + agents + skills + CLI — the only unified index), MCP.Directory (servers + skills), MCP Find, Glama/Smithery (MCP-only). Hermes ships its own skills hub: `hermes skills search <q>` (14 sources incl. skills.sh, anthropic, openai, clawhub; trust ratings), `hermes skills install <id>`. The hub is thin on enterprise-IT niches (KQL/Intune/PowerShell = zero results) — the user's domains are already better served by self-authored skills.
- Design MCPs: nearly all are Figma/Penpot/component-library connectors; the user's design layer is Open Design (already wired 2-way, bundled skills, previews — beats every free design MCP). The filesystem MCP duplicates native tools; only for file-less clients.
- Serena (LSP-backed symbol-level code MCP, best in class): trigger = large unfamiliar repos / OSS contributions (e.g. borrowing a repo like openbb-tmx); wire single-project context, never the full toolset.
- Context7: the one ADD approved (Aug 2026) — docs-drift fix for KQL/Intune/Python work. Remote mcp.context7.com/mcp, two tools (resolve-library-id → query-docs), free key optional (1,000 calls/mo). Tools register at session start.
- The live profile carries additional workflow skills (test-driven-development, systematic-debugging, requesting-code-review, spike, simplify-code) installed from the platform. verification-before-completion added Aug 2026.

## Wiring an approved tool (Hermes specifics)

- MCP server: `hermes mcp add <name> --url <remote-url>` or `--command/--args` (stdio). PITFALL: the "Enable all tools?" prompt cancels on piped stdin (no TTY). Workaround: write the config directly with `hermes config set mcp_servers.<name>.<key> <value>` (url, connect_timeout, timeout) — the patch/write_file tools REFUSE ~/.hermes/config.yaml as security-sensitive, and `hermes config set` is the official path anyway. Remote servers need only url + optional timeouts (match the exa/firecrawl entry shape). Stdio servers may need `enabled: true`; Windows GUI binaries need a cmd.exe bridge launcher (see the Open Design od_mcp.cmd launcher pattern). Verify with `hermes mcp list` + `hermes mcp test <name>`. New tools register at the NEXT session start.
- Hub skills: `hermes skills install <id>` also cancels on piped stdin — pipe `printf 'y\n' |`. CHECK FOR STUBS: skills.sh entry points can be 7-line stubs referencing a companion skill (grill-me → /grilling) — install both, or the stub is dead weight. Hub-installed skills are user-owned (protected) — do not patch them.
- Only original work ships in this repo. When adapting an external skill, keep the body faithful and add environment-specific rows (e.g. "Scripts (Hermes)" patterns referencing real past bugs like the FCF sign bug).
- Always verify installs: read the installed SKILL.md and skills_list before declaring done — verification-before-completion applies to its own installs.

## Pitfalls

- Recommending a tool by its marketing shape ("one server, hundreds of X") instead of its measured use — the user's pattern is to like the SHAPE and then ask the right question; the answer still comes from the audit.
- Assuming the user's stack needs what other users' stacks need: artifact-centric workflows make memory systems redundant; document the measured baseline instead of asserting it.
- Delivering a research dump without a verdict — the user asks "is it worth it", not "what is it". Verdict first, landscape second.
- Forgetting the trigger half of a "no": a decline without a flip-condition is a dead end, and the user will ask the follow-up anyway.
- Evaluating against the user's day job instead of the sessions they run (user correction, Aug 2026): fit is judged against session work — portfolio research, backtests, skills, memory workflows — unless the work lens is explicitly requested. The first pass on mattpocock/skills, OpenViking, and semantica leaned on the [employer] role; the user redirected with "use my sessions for context", and session_search grounded the real verdict. Ground first, judge second.
