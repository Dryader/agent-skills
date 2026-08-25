---
name: agent-memory-evaluation
description: "Should an agent get external memory (Hindsight/cognee/Zep)?"
tags: [memory, agents, evaluation, benchmarks, contamination]
triggers:
  - user asks whether an agent should get external memory
  - comparing memory providers (Mem0, Hindsight, Cognee, Zep)
  - should we add memory to this agent

---

# Agent Memory Evaluation

Use when asked whether an agent (or this Hermes install) should adopt an external memory provider — Hindsight, Mem0, Zep/Graphiti, Letta, Cognee, or one of the Hermes memory plugins — or when comparing "agent memory" tools in general.

## The decision is measurable, not vibes

The question "would memory X help us?" has a falsifiable answer: run the pain-inventory gate against the actual session corpus BEFORE evaluating any vendor. A multi-month session-corpus audit (this machine, Aug 2026) found ~1% of sessions contained any cross-session recall need, all satisfied by session_search + skills — verdict: no provider. The audit data decided; no vendor research was needed.

## The five gates

1. **Pain inventory** — list concrete failures from the last 30 days: re-explanations, confidently-wrong context, session_search misses. Fewer than 3 named instances → STOP, re-check in 3 months.
2. **Shape the pain** — "we decided X and forgot" = keyword-shaped (session_search covers it); "I meant the concept, not the words" = semantic-shaped (only this justifies a provider); "methodology drifts" = a SKILL problem, a memory provider makes it worse.
3. **30-day trial with a contamination audit** — plant 5 known-fact checks + 2 trap questions (things sessions never said — does it abstain or fabricate?); count recall wins vs contamination incidents weekly.
4. **Correction test** — when it's wrong, does update/forget stick permanently? If the fix doesn't persist, garbage accumulates and the system becomes a liability regardless of recall quality.
5. **Keep/drop rule** — keep only if BOTH: ≥1 re-explanation per week prevented that session_search provably couldn't handle, AND contamination is rare and permanently correctable. Drop otherwise; remember the token cost of extraction on every session.

## Audit first: scripts/session_memory_audit.py

Runs against `~/.hermes/state.db` (no sqlite3 CLI needed — uses Python stdlib): session/message counts by source, date span, titled-session sample, cross-session recall-phrase scan ("we discussed", "in our previous"...), re-explanation complaint scan ("you forgot", "i told you", "again?"). Read "again?" skeptically — it usually means "run it again", not "you forgot". Subagent-sourced sessions are internal noise; count only cli/acp sources as user-facing.

## Hermes-native path exists before any vendor

`hermes memory status` — plugins installed: honcho, openviking, mem0, hindsight, holographic, retaindb, byterover (+ supermemory requires key). One active at a time; built-in MEMORY.md/USER.md always on. Enable: `hermes memory setup`. Providers are off by default BY DESIGN (billing, privacy, third-party dependency, choice, context-budget) — but several are local-capable, so "local" is not the blocker; the setup step is the consent+config moment. A "local" plugin still needs an LLM key and still costs extraction tokens per session. (OpenViking — one of these plugins — was evaluated for session-work fit Aug 2026: verdict skip, auto-extraction re-enters context without a review gate; sources in the agent-tool-evaluation skill's Verified landscape section.)

## What these tools are actually FOR (conversation-centric vs artifact-centric)

Memory systems exist for users whose conversations ARE the product — the agent's memory of the user is the deliverable, not a side effect of getting work done. Five profiles:

1. **Multi-tenant user profiles (Mem0)** — products where every user needs a persistent evolving profile (support, sales, coaching); the biggest market (AWS ships Mem0 as Agent SDK memory).
2. **Temporal/audit domains (Zep/Graphiti)** — "what did we know as of last Tuesday": compliance, case management, healthcare timelines; a stale fact triggers a wrong action.
3. **Long-running self-managing agents (Letta)** — agents that page their own memory like an OS; adopting Letta means replacing your agent runtime, not adding memory.
4. **Document-corpus knowledge graphs (Cognee)** — entity/provenance over messy corpora (policy PDFs, literature); knowledge management, not chat recall.
5. **Context-window escape hatch (universal)** — LongMemEval: frontier models degrade 30-60% reading full history vs selective retrieval; needed at multi-million-token scale.

Artifact-centric users (decisions → skills/files/repos, verification-first) get ~nothing from this category; git log + skills + session_search already carry their temporal and decision history. When asked "but what is it FOR?", this framing is the answer — it also terminates the "would X help us?" loop by showing which profile (if any) the user matches.

## Pitfalls

- **Vendor benchmark claims are not load-bearing.** LongMemEval/LoCoMo scores are mostly self-reported; the one exception verified: Hindsight's numbers were independently reproduced (Virginia Tech + Washington Post, per its repo). Use benchmarks to confirm "not grossly broken", not to choose.
- **Backbone model gates extraction quality** — Hindsight's own paper: "extraction errors can propagate through the memory graph"; quality depends on the backbone. Leaderboard numbers use Gemini-3/120B. Do NOT assume a budget-priced backbone is weak: deepseek-v4-flash-0731 (the model on this machine) is frontier-class — AA Intelligence Index 50, tied with Gemini 3.6 Flash, 1 pt behind GPT-5.6 Luna, second-best open-weights agentic Elo (GDPval-AA v2 1559), hallucination rate comparable to GPT-5.6 Terra (verify model claims before judging; "flash"-style names lie). A verified-strong backbone strengthens the case for any provider's extraction tier.
- **Contamination is measured, not theoretical**: HaluMem (arXiv 2511.03506) — <50% correct update rates across systems, >50% omission; MemoryAgent Bench FactConsolidation — 7% (Zep/Graphiti) to 18% (Mem0) on single-hop conflict resolution, ≤7% multi-hop; ConsistencyGate (arXiv 2607.22962) — a hallucinated fact "persists as a false premise for every subsequent step", and utility/recency-based admission is structurally blind to it. Retrieval surfaces memories as facts — that's the authoritative-garbage risk.
- **Provider ≠ memory backend**: native Hermes plugins auto-write/auto-recall in the agent loop; a parallel system (cognee, Graphiti) needs you to build and maintain ingestion glue (export sessions → cron → LLM extraction) and recall is opt-in per call. Second source of truth can go stale silently while looking authoritative.
- **A provider's entire value is the conversational-recall slice — nothing else.** It never improves skills (how-to), memory files (curated facts), or repos (work products); those layers stay load-bearing no matter what. Worse: a provider that makes recall effortless becomes a temptation to let decisions live in conversation instead of being written into skills — the exact failure mode frozen methodologies exist to prevent. Discipline: conversation recalls, skills decide, files execute.
- Session_search has zero contamination risk (verbatim transcripts) — the honest trade is keyword-only recall for no fabrication. Verify-first users get less value from memory layers (they re-verify anyway).

## References

- The 2026 provider landscape (Mem0, Zep/Graphiti, Letta, Cognee, Hindsight, basic-memory, second-brain, supermemory): architectures, self-host reality, license/lifecycle traps, and contamination research receipts.
