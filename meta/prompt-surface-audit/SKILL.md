---
name: prompt-surface-audit
description: Audit prompts and skills for dated instruction patterns.
tags: [meta, prompts, skills, quality]
---


# Prompt Surface Audit

Auditing an agent's own prompt surface (system prompt, tool descriptions, SKILL.md files and their references, request-building config) for text written for older models: boosters that now over-trigger, scaffolds an API feature replaced, step scripts for judgment work, fossils nobody owns, and bloat paid on every request.

Catalogue-level questions belong here too, and they come up more often than the text-level ones: where a skill came from (bundled, hub-installed, locally owned, or an upstream removal that left an orphan behind), what the whole catalogue costs as always-injected text, and which entries nothing will ever clean up. Step 2 and Step 2b cover that.

Two deliverables, always: a **report** (location, quoted evidence, pattern, why it is obsolete for the target model, confidence, action) and a **proposed diff**. Propose; apply only when the request itself says to apply.

## Step 0. Fix scope and target model from the environment

- Scope: the files the request names if it names any; otherwise everything in the working directory that reaches a model as text. List what the inventory found before auditing it.
- Target model: the model the request names, else the migration target the repo documents, else the newest model the repo's own config points at. In this install that is `model.default` and `model.provider` in `~/.hermes/config.yaml`, plus any configured reference models.
- State both assumptions at the top of the report and proceed; a corrected assumption beats a blocked audit.
- Confidence follows the target model. A finding whose reason is another vendor's documented behavior is Medium when that vendor is not the target. Defects provable inside the files (two skills disagreeing, a verbatim duplicate, text addressed to the maintainer, a violation of the repo's own authoring standard) are High regardless of model.

## Step 1. Measure before reading

```bash
python3 scripts/scan_prompt_signals.py ~/.hermes/skills <out-dir>
```

It counts every signal line per file, ranks files by booster and prohibition density, and writes `hits.json` plus `per_file.json`. Read only the top offenders, in full, before writing a finding. The signals are described in `Reference: signals-and-keeps`; the regexes in the script are the source of truth.

Numbers that change decisions: the always-injected catalogue cost (every skill's name plus description rides in every request, so sum them rather than guessing), how many of those descriptions exceed the repo's own bar, and the per-file density of boosters and prohibitions. Quote the measured number, not an adjective.

`scripts/skill_inventory.py` prints the whole catalogue accounting in one pass: size, provenance split, per-skill origin-hash match, index chars, over-bar descriptions, orphans, never-loaded skills. Describe the catalogue's cost precisely — it rides the cached prefix, so it is context on every turn plus a full re-send on every cache write (new session, compression, model switch), never a per-turn bill. The bar for a description is the bundled authoring standard: ≤60 chars, one sentence, ends with a period, no marketing words. A measured pass over 190 skills took the block from 30,737 to 13,845 chars (55%) with no capability removed, so lead with that arithmetic rather than "too many skills".

## Step 2. Establish provenance and actionability before proposing anything

- `~/.hermes` is not a git repo, so `git blame` is unavailable. Use the install's own state instead: `~/.hermes/skills/.usage.json` (`created_by`, `use_count`, `patch_count`, `state`), `.hub/lock.json` for hub installs, and file mtimes.
- Gate every proposed edit on ownership. Hash the live directory against the origin hash recorded for it in `~/.hermes/skills/.bundled_manifest` (MD5 over the package's sorted relative paths plus bytes, the same function as `tools/skills_sync.py::_dir_hash`). A bundled skill updates only while that hash still matches; the moment you edit it, sync SKIPS it forever and your text survives every future update. So a local edit to a clean bundled skill is safe from overwrite but freezes that skill from upstream fixes — state the tradeoff and let the user choose, and name `hermes skills list-modified` / `hermes skills diff <name>` / `hermes skills reset <name>` as the way to see or undo it. Hub-installed and third-party skills are not yours to edit at all (the hub owns its install path and `hermes skills update` overwrites). Entries under `~/.hermes/skills/.archive/` are already out of the catalogue, so a finding there is a restore-or-delete decision, not an edit.
- Detect ORPHANS from the manifest, never from vibes. A bundled skill REMOVED upstream keeps its file in the catalogue forever while its manifest row simply disappears — sync never deletes from the user tree, and the local copy can therefore be a version behind the successor that absorbed it. Reconstruct that history from the exact path: `commits?path=skills/<cat>/<skill>/SKILL.md` (added / maintained / deleted) on the repo API, then the merging PR body (`pulls/<n>`) for the reason — consolidation into another skill reads differently from redundant-or-dead. `git/trees/main?recursive=1` lists what ships today (`skills/` is the active bundle, `optional-skills/` ships without loading), which is how you tell a present-day home from a removed one.

## Step 2b. Establish what the lifecycle will and will not clean up

Before recommending deletions, read the ownership split: `hermes curator status` separates curator-managed (`created_by: agent`) from bundled and from unmanaged (no provenance marker, or `created_by: null` — hand-written, installed by URL, or created by a foreground agent).

- The curator never deletes. Archive (`~/.hermes/skills/.archive/`, restorable with `hermes curator restore <name>`) is the maximum.
- It auto-transitions ONLY curator-managed skills. Unmanaged entries are never stale-detected or pruned, so a dead unmanaged pack sits in the catalogue indefinitely: recommend `hermes curator adopt <name>` for the ones worth keeping live, `hermes curator archive <name>` for the rest.
- `hermes curator prune --dry-run` lists what idle-30d would archive. Do not run it blind: that list is dominated by used-but-bursty research and methodology skills, where a long idle gap is a workflow shape, not death. Pin those first (`hermes curator pin <name>`), say which ones you pinned, and only then offer the prune.

## Step 3. Write the findings table

One row per finding: location `file:line`, the exact quoted text, the pattern it matches, one sentence on why it is obsolete for the target model, confidence, and an action of remove / rewrite (give the replacement) / move (say where) / add (under-description) / flag. Order by confidence, highest first. A documented-pattern match always gets a concrete action; keep `flag` for idiom dating that no row documents and for out-of-scope items. Give counts per pattern group at the top of the report.

## Step 4. Build the diff without applying it

`scripts/propose_diff.py <edits.json> [out.diff]` copies each target into a `before/` tree, applies the replacements into `after/`, asserts that every old string matched **exactly once**, and emits a unified diff. The single-match assertion doubles as the evidence check: if a quoted line is not byte-exact the hunk is refused, and that is a report bug, not a diff bug.

Then verify the artifact and report the verification:

```bash
cd ~/.hermes/skills && patch -p1 --dry-run < <out.diff>
```

Report file count, hunk count, dry-run result, and that the originals were untouched. Leave the before/after trees and the raw match JSON in the scratch dir and name them in the reply.

## Deliverables in the shape this user wants

- Report inline in the reply, tables over prose, assumption block first, per-group counts near the top.
- The diff as a file delivered as an artifact, with the apply command on one line. Never apply it unless asked.
- A keep list and an out-of-scope boundary in the report. A clean surface must read as clean, and the boundary stops the inventory being mistaken for complete.
- Flag-only items are still findings: date-stamped evidence trails in research skills, and any pattern whose fix belongs upstream.

## Pitfalls

- Count uppercase boosters case-SENSITIVELY. `\bONLY\b` and friends with `re.IGNORECASE` match ordinary prose ("only", "required") and manufacture a systemic finding: the same surface measured 148 booster lines case-sensitively versus 6,565 insensitively.
- A locally edited bundled skill is never overwritten. Sync skips any package whose bytes no longer match the manifest origin hash, so the edit survives and the skill simply stops receiving upstream fixes. Report the freeze and let the user decide instead of refusing the edit; `hermes skills list-modified` shows the frozen set. Check ownership before writing any hunk so the tradeoff is stated, not guessed.
- Never justify a deletion by length. The harm is a specific dated instruction, not volume, and context only the author has is never cruft.
- Do not flag absolute machine paths in a single-user local skill set. The volatility argument assumes a shared repo; here those paths are load-bearing.
- Do not flag a verification date as rot. A claim stamped with when it was checked is the fix for the volatile-specifics problem, not an instance of it.
- Do not flag reasoned prohibitions, deliverable prompt templates, numeric rules governing the user's own documents, or step order in genuinely fragile operations. Classify each line separately; a legitimate neighbour does not launder a no-provenance one.
- Probe behaviour before calling a cut good, one change at a time, on a scratch copy. A cut that regresses is re-added in its minimal form, never as the verbose original.
- Generate replacements from a script FILE (`write_file`, then run it), not an inline heredoc: through this host's MSYS shell, heredocs lose backslash escapes and the failure range from a parse error to a silently unmatched replacement. Keep the single-match assertion regardless of how the edits were produced.

## Files

- `Reference: signals-and-keeps` — signal table, the keep list, and where this install's prompt surfaces live with how to re-measure their cost.
- `scripts/scan_prompt_signals.py` — signal scanner and ranker.
- `scripts/propose_diff.py` — non-destructive hunk builder and diff emitter.
- `scripts/skill_inventory.py` — catalogue accounting: provenance, origin-hash match, index cost, over-bar descriptions, orphans, never-loaded skills.
- `scripts/set_descriptions.py` — guarded description rewriter (refuses hub-owned and block-scalar entries, backs up originals, re-verifies frontmatter).

## Reference: signals-and-keeps

# Signals, keeps, and this install's surfaces

## Signal table

| Signal | What it looks like | Why it is cruft now |
|---|---|---|
| Booster density | uppercase MUST / NEVER / ALWAYS / CRITICAL / IMPORTANT, especially several per file | markers stop carrying information once everything is critical, and the prompt's register becomes the output's register |
| Hedges on requirements | "try to", "if possible", "ideally", "where possible" attached to something the task actually needs | read literally as permission to under-deliver |
| Trait claims and choreography | "you tend to over-X", "remember to plan", "think step by step", scratchpad/tag incantations | the behaviour is native now; the sentence causes over-planning and over-triggering |
| Scaffolds an API replaced | assistant-turn prefill plus its stop-sequences, regex extraction and retry loop; forced tool choice; sampling-param fossils | structured output and tool steering replaced them, and the surrounding code is cruft too |
| Output clamps | "at most N words", "post an update every third tool call", numeric ceilings | clamps starve reasoning, and a stated operational reason does not convert a number into a keeper: re-express as audience and outcome |
| Step choreography | long numbered scripts for judgment work | the model's own plan usually beats a hand-written script; keep numbered steps only where order is genuinely fragile |
| Prohibition clusters | runs of Do not / Never / Avoid with no stated reason | describing success beats enumerating failure, and a prohibition against a failure that was not coming can anchor toward it. Prohibitions encoding a real business or policy constraint, or carrying their reason, stay |
| Grader vocabulary | "you will be graded", "hidden tests", "the detailed checklist is for benchmarking" | describes the scoring apparatus instead of the requirement |
| Repetition | the same sentence in two sections, "Remember," "Again,", "As stated above" | duplicated rules make the model reconcile wordings and cost tokens |
| Fossils | retired model names, per-version technique claims, "now works differently", "was wrong", "RETIRED", incident and log narration, author TODOs | the reader never saw the previous version, and pinned model names degrade silently at the next release. State the current rule |
| Dated state claims | "as of <year>", "the optimal stack (as of <year>)", dated screen or experiment narration | the rule survives without the date; move dated detail to a reference |
| Trigger enumeration | frontmatter `description:` listing near-synonymous queries, one phrase per missed trigger | descriptions ride in every request; name intent categories instead. Trigger text may carry calibrated urgency, so cut it against a trigger eval, not by eye |
| Duplicate definitions | two skills for one server or one tool, same H1, overlapping bodies, or a one-line alias stub | two catalogue entries and two descriptions for one capability, and divergent copies eventually disagree |

## Keep list (do not flag)

1. Context only the author knows: audience, product, environment facts, the quality bar, the reason behind a constraint. Too-short prompts produce generic output. Cruft is not the same thing as length.
2. Fragile operations keep their exact commands: destructive sequences, auth flows, compliance steps.
3. Reasoned prohibitions and real business or policy constraints stay, ideally with the reason beside them.
4. Tool contract detail, parameter semantics, limits and failure modes stay, and usually grow.
5. Format-pinning examples on genuinely format-sensitive output stay, labelled illustrative.
6. Working redundancy: the same contract stated twice, or a reference copy that is still accurate, is a refactoring preference, not a dated pattern. Propose dedup only when the copies disagree.
7. A one-line role statement is fine. Identity text is a finding only when it substitutes for real context.
8. A single recap of the key constraints at the end is a deliberate pattern; scattered duplication is the anti-pattern.
9. Verification dates, provenance stamps, and evidence trails in research skills are the fix for rot, not rot. Flag them at most as a structural question ("move the wave-by-wave archaeology to a reference").
10. Absolute machine paths in a single-user local skill set are load-bearing. The volatility argument assumes a shared repo.
11. Numeric rules that govern the user's own documents (prose length, bullet counts on a post) and research-design budgets ("attack at most 2 claims") are not output clamps on the agent's own replies.

## This install's prompt surfaces

| Surface | Path | Notes |
|---|---|---|
| Skill bodies | `~/.hermes/skills/**/SKILL.md` | loaded on trigger |
| Skill references | `~/.hermes/skills/**/references/*.md` | loaded on demand, so cheaper than the body |
| Always-injected catalogue | frontmatter `name` + `description` of every skill | rides in every request: sum the two fields, divide by ~4 for tokens |
| Session persona | `~/.hermes/SOUL.md` | keep it short on purpose |
| Request config | `~/.hermes/config.yaml` | check for sampling-param fossils, cache-hostile ordering, guardrail settings, and any rendered token budget |
| Vendored install | `~/AppData/Local/hermes/hermes-agent` | system prompt builder `agent/prompt_builder.py`, tool descriptions under `tools/`. Upstream code with an upgrade path, so report findings there instead of patching |
| Bundled skills | `~/AppData/Local/hermes/hermes-agent/skills/<category>/<skill>` | compare hashes before proposing an edit; identical copies are overwritten on update |

The install's own authoring standard caps a skill description at 60 characters, one sentence, ending in a period, on the grounds that long descriptions bloat the listing and dilute attention. Measure the surface against it and report the count and the wasted characters: that number is model-independent and survives any argument about which model is running.

## Re-measuring the catalogue cost

```bash
python3 - <<'PY'
import os, re
root = os.path.expanduser("~/.hermes/skills")
total = over = 0
for dp, dn, fn in os.walk(root):
    dn[:] = [d for d in dn if d not in (".archive", ".git")]
    if "SKILL.md" not in fn:
        continue
    text = open(os.path.join(dp, "SKILL.md"), encoding="utf-8", errors="replace").read()
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        continue
    fm = m.group(1)
    name = re.search(r"^name:\s*(.+)$", fm, re.M)
    desc = re.search(r"^description:\s*(.*?)\s*$", fm, re.M | re.S)
    n = len(name.group(1).strip()) if name else 0
    d = len(" ".join(desc.group(1).split()).strip().strip('"')) if desc else 0
    total += n + d
    over += max(0, d - 60)
print("catalogue chars:", total, "~tokens:", total // 4)
print("chars over a 60-char description bar:", over)
PY
```
