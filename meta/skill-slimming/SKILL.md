---
name: skill-slimming
description: Use when a SKILL.md carries data. Slim it to references/.
tags: [meta, skills, context, maintenance]
---


# Skill Slimming (Context Diet)

## When to use
- A SKILL.md body has grown large AND much of it is data, not procedure. Size is a soft tripwire, not a law: live bodies here run median 8.8 KB, p90 24.5 KB, so 20 KB (~5k tokens) only says "look closer". The binding test is per section — is this a lookup table or a catalog? A 12 KB body of rules is fine; a 12 KB body of tables is not.
- User asks to reduce context weight of the skill library
- A skill has accumulated dated correction logs, research findings, or lookup tables

## The rule
- **Payoff is tokens x uses, so measure uses before extracting.** The size lint ranks bodies by bytes; the
  payoff ranks them by `body_tokens * use_count`. Half the high-data-share bodies in this library had 0
  uses, where extraction saves exactly nothing, while the biggest accumulated costs were 0%-data bodies of
  rule bullets (consumer-product-comparison 36 KB x 62 uses, 39 bold-lead bullets averaging 665 chars) that
  must stay in context. Extract only where both bars clear: a genuine lookup table AND real use count.
- **Body = procedure**: steps, thresholds, decision rules, binding verdicts, severity tiers, pitfalls/scar tissue, output formats, current standards. Must be in context while executing.
- **the Reference appendix = data**: pattern catalogs, phrase lists, dated logs, lookup tables, benchmarks, verified research findings, verbatim templates, command dumps. Loaded on demand via skill_view(file_path).
- A slimmed body keeps each moved section's original header + a one-line pointer, so structure stays readable.

## Safety checks (in order)
1. **Bundled-skill check**: `find ~/.hermes/hermes-agent/skills -name SKILL.md` lists the skills that ship with Hermes (58 in this install). NEVER slim bundled skills — updates overwrite them anyway. A bundled skill may be user-customized (cmp vs source); still don't touch it. Also skip hub-installed skills (`hermes skills list` flags them); updates can overwrite those too.
2. **Persistence**: references live inside the skill's own dir (~/.hermes/skills/<cat>/<skill>/the Reference appendix) on real disk (this box: /dev/sdd root, not tmpfs — survives reboot). Backups go to ~/skill-slim-backup/ on the same disk. Never put the working copies in /tmp or $HERMES_HOME/cache.
3. **Backup every skill dir** (tar.gz) before editing; the scripts do this automatically.

## Process
1. **Measure**: print per-section byte sizes for candidate skills (split on `^#{1,2} ` headers). Target biggest bodies first; the top-10 bodies are usually 50% of the weight.
2. **Decide** which sections move — start/end markers are line prefixes matched with str.startswith, so they must be unique in the file (script enforces exactly-once).
3. **Write the spec JSON** (see templates/spec.example.json).
4. **Run** `python3 scripts/slim.py <spec.json>` — backs up, extracts, writes the Reference appendix, replaces body sections with header+pointer. Idempotent: skips skills whose body already contains the `context diet` marker.
5. **Verify** `python3 scripts/verify.py <spec.json>` — full-section containment vs backup, frontmatter parse, header+pointer presence.
6. **Spot-check** with skill_view(name) that the skill loads and linked_files lists the new references.

## Spec format
```json
[
  {"skill": "category/name",
   "sections": [
     {"start": "## Header prefix", "end": "## Next header prefix", "ref": "file.md"},
     {"start": "## Last section", "end": null, "ref": "file.md"}
   ]}
]
```
- start/end are line prefixes (str.startswith); end null = runs to EOF
- sections sharing a ref filename concatenate into one the Reference appendix<ref> file
- the section's header line stays in the body; content moves

## Splitting an oversized reference (the >15 KB trap)
- **Rule**: one reference file = one topic a reader can name from its title. Size is only a tripwire, and the number is a convention, not a natural break — measured over the vendor pack (106 reference files): sizes decay smoothly, median 8.2 KB, p75 18.4 KB, p90 29.9 KB, max 65 KB, so ~15 KB sits near p70 and flags about a third of files. What makes that the right place is the *topical unit*: median section 0.9 KB, p90 3.6 KB, so a 15 KB file typically holds 4-17 topics, which is why it reads as a dump instead of a topic. Set the number to the budget you are willing to pay per load (~15 KB is ~3.7k tokens); set the *rule* to topicality.
- **Machine**: `python3 scripts/split_ref.py <file-or-dir> [--cap 15000] [--dry-run]`. Parses headings at the shallowest level below H1 (auto-detected, fence-aware), groups sections greedily to the cap, re-splits an oversized single section at the next heading level (H4, then H5), writes parts to `<stem>/NN-<slug>.md`, replaces the original with an index, orphan-checks every line over 30 chars, exits 1 on a lost line or a part still over cap.
- **Verified**: unity-cli's eight oversized command references (304 KB) became 31 parts, largest 14,663 bytes, zero lines lost, and the index files (0.6-3.9 KB) kept the original names so the skill's own pointers needed no edit.
- **One-section files are not splittable: leave them.** A 17.7 KB reference that is a single H2 (one topical unit, no H3s) "splits" into a 17.5 KB part plus a stub and still exits 1 — that is the tool correctly refusing, not a failure to fix. Check `grep -c '^#' <ref>` before spending a run on it.
- **Split parts share basenames across skills** (`<stem>/01-overview.md` exists in every split skill), so a duplicate-reference-basename lint fires on the whole library right after a split wave. Compare basenames only for files directly under the Reference appendix; part dirs and `absorbed/` archives repeat names by design (fixed in `scripts/lint.py`).
- **Leave a body alone unless a *section* is a lookup table.** Score data share per section, not per line: bullet-heavy bodies read as "data" but are usually rules that must be in context (unity-cli 28% tables, physics-3d-collision 36%, neither had a movable blob). Only catalogs move, e.g. tilemap-ruletile-createfromsegment's "Common Tile Patterns".
- **Heading counts lie**: `#` comments inside fenced code blocks look like headings. A 65 KB file reported "1 section" for exactly this reason. Parse fences or the section list is nonsense.

## Pitfalls (learned 2026-08-31, verified on 9 skills / 42 sections)
- **Emoji in headers**: `## ⚠️ CRITICAL...` — end markers must include the emoji or the match silently fails. In Python literals use `\u26a0\ufe0f`.
- **Global error list**: one skill's failure skips the rest silently. Track errors per skill; only that skill is skipped.
- **Idempotency marker**: check for the pointer text `context diet` to detect already-slimmed skills. Do NOT use start-prefix presence — headers stay in the body after slimming, so they're still present.
- **Verification false positives**: line-level "moved line still in body" checks fire on common tokens (`---`, `import json, os`, `}`) that exist in both moved and kept sections. The truth test is FULL SECTION containment: the entire moved section text must appear in its ref file.
- **Byte accounting**: exact-reconstruction diffs fail on pointer formatting (blank lines around the pointer line). Don't gate on byte math; gate on containment + frontmatter + pointer presence.
- **Pointer format** (keep the header above it): `> Data moved to the Reference appendix<ref> (<date> context diet). Load on demand: skill_view(name='<skill>', file_path='the Reference appendix<ref>').`
- **Ref file header**: first line notes extraction date + source skill, so provenance survives.
- **Curator**: only auto-archives `created_by: "agent"` skills; slimming user skills doesn't conflict.

## Pitfalls discovered 2026-09-16 (second pass, 6 skills / 11 sections)
- **Big single references are the real trap, not the bodies**: one pointer to a 45-98 KB reference costs the same as a fat body, and the agent has no way to know beforehand. Cap references at ~15 KB and split by topic; keep a one-line index in the body so a partial need costs a partial load (portfolio-analysis/the Reference appendixabsorption of a 100 KB legacy body into the Reference appendixabsorbed/` is the pattern for archive material).
- **verify.py false positives**: it can report `section NOT contained` on a perfectly clean move (whitespace/edge diff around the ref's synthetic header). Do not treat that as data loss — run the orphan check instead: every original section line >30 chars must appear in the ref file. 0 missing = safe.
- **The idempotency marker blocks re-slimming**: a body containing `context diet` anywhere makes slim.py skip the *whole skill*, including sections that were never moved. Move those manually: tar the dir, write the Reference appendix<ref>` with the standard synthetic header + the section text, replace the section with its header + the standard pointer line, then orphan-check.
- **Line-initial header detection inside code fences**: `# ...` comments in fenced Python are not sections, but an H2 search sees them; verify the section list against the body before writing a spec.

## Pitfalls discovered 2026-10-02 (third pass, lint correctness)
See `Reference: lint-correctness`: the skip rule must key on source (bundled + hub), not on
`created_by`; mirror the loader's `EXCLUDED_SKILL_DIRS`; folded the Reference appendixtopics/` packs are
reported apart and never gate the exit code.

## Reference files
- scripts/split_ref.py — split an oversized reference (>15 KB) into topical parts plus a pointer index; recursive by heading level, orphan-checks content
- scripts/lint.py — size lint: bodies over cap, oversized references, unconditional read-pointers, duplicate reference basenames across skills (skips bundled/hub skills by source; folded upstream packs reported apart; exits 1 only on actionable findings)
- scripts/slim.py — the extraction engine (backup, move, pointer)
- scripts/verify.py — the verifier (containment vs backup, frontmatter, pointers)
- templates/spec.example.json — spec format with sample entries

## Reference: lint-correctness

# Lint correctness — what the size lint must skip, and why

Extracted 2026-10-02 from skill-slimming/SKILL.md (third pass). Lessons from making `scripts/lint.py`
trustworthy; each one was a real false-negative or false-positive observed on this library.

- **Never key the lint's skip rule on the usage log's `created_by`.** Skills written straight into
  `skills/` (via write_file rather than skill_manage) have no `created_by`, so a rule that flags only
  `created_by == "agent"` silently skips the agent's own skills — that is how a 10.7 KB body
  (`serena`) and a 64.8 KB reference (a 64.8 KB reference in another skill) went
  unreported while the report still looked clean. Skip by *source* instead: bundled names (walk the
  Hermes source tree, `skills/` and `optional-skills/`) plus hub names (`.hub/lock.json` →
  `installed`), and audit everything else.
- **Mirror the loader's exclusions or the report fills with phantom findings.** Walk with `os.walk`
  and prune `EXCLUDED_SKILL_DIRS` from `agent/skill_utils.py` (`.archive`, `.hub`, `.venv`, `.git`,
  `node_modules`, ...) plus every dot-directory, and stop descending once a directory holds a
  `SKILL.md` (its subdirs are support dirs, never skills). A naive `glob('**/SKILL.md')` walk counts
  archived skills and every topic inside a folded pack: on this library that turned 24 bodies into 59
  and 2 oversized references into 69.
- **Folded upstream packs are not findings.** Files under `references/topics/` are upstream content
  kept verbatim and refreshed by the pack's own sync script (the pack's own sync script, in the
  umbrella). Report them in their own bucket and keep them out of the exit code, or the lint can
  never pass again: 41 topic files over the reference cap is the steady state, not a defect.
- **Cross-check the count against the loader.** `token_audit.py` and `lint.py` must agree with
  `iter_skill_index_files(Path(skills_dir), "SKILL.md")` from the installed Hermes package; that
  loader prunes support dirs and `EXCLUDED_SKILL_DIRS`, and it is the number that decides per-turn
  cost. Any disagreement is a bug in the audit, not a change in the library.
