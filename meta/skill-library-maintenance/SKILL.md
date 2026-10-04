---
name: skill-library-maintenance
description: Audit skill-library and memory-store cost; archive, pin.
tags: [meta, skills, context, cost, curator, maintenance]
related_skills: [skill-slimming, skills-repo-audit, mcp-fleet-optimization]
---


# Skill Library Maintenance

Class of work: keeping the live library (`~/.hermes/skills`) and the always-injected memory
stores cheap and correct — what stays offered, what gets archived, what gets slimmed, what gets
cut out of the stores, and repairing references after removals. Distinct
from `skills-repo-audit` (read-only content quality of a repo) and `skill-slimming` (moving data out
of one body); this one owns cost accounting and the curator lifecycle.

## When to Use

- The user asks what is wasting tokens or context in the skill library.
- The library needs pruning, or a skill pack was just imported.
- A curator pass needs reviewing before it runs.
- The USER/MEMORY stores are at their cap, or staged records are piling up in
  `~/.hermes/pending/memory/`.
- A skill was removed and other skills may still reference it.

## Cost model — compute both, optimize the larger

1. **Index cost.** The `name: description` line of every active skill is injected into the system
   prompt every turn: `chars / 4` ≈ tokens per turn, forever. A real 181-skill library: 15.5k chars
   ≈ 3.9k tokens/turn, ≈ 3.9M tokens per 1,000 turns.
   **Render the block, do not estimate it from names and descriptions.** The rendered block also
   carries a category header per category, the six-character `    - ` indent and ~1.1k chars of
   boilerplate, so a listing estimate undercounts by ~30% (135-skill library: 10.8k chars estimated
   vs 14.2k chars ≈ 3.6k tokens rendered). Reproduce it exactly as the prompt does:
   `build_skills_system_prompt(skills_dir_override=Path('<skills-dir>'))` in `agent/prompt_builder.py`,
   then `estimate_tokens_rough` from `agent.model_metadata`. Marginal cost ≈ 26 tokens/skill/turn at a
   60-char description, so the index scales linearly with the number of skills offered and the only
   way to cut it is to offer fewer.
2. **Load cost.** The SKILL.md body, paid only when the skill is loaded: `body_tokens × use_count`.
   This is normally the larger number. Same library: eight high-traffic skills had spent ≈5.5M
   tokens while the ENTIRE index costs 3.9M per 1,000 turns.
3. **Fixed overhead is the denominator, and it is where the fat actually is.** Measured on this
   install (request body from `~/.hermes/sessions/request_dump_*.json`, window from
   `context_length_cache.yaml`, live per-category split from `agent/context_breakdown.py`): 25
   built-in tool schemas ≈ 13.2k tokens, deferred MCP catalog ≤4k (its own budget cap), the whole
   skills index 3.6k, ~22.7k fixed before any conversation, against a 262k window. The index is
   therefore ~1.4% of the window and ~16% of the fixed block. When the user asks whether the index is
   too big, answer with that ratio rather than opening another slimming pass: halving it means
   archiving about half the library for ~1.8k tokens/turn, while tool schemas and conversation
   history dwarf it.

4. **The memory stores are always-injected too, and they are not the skills index.**
   `~/.hermes/memories/MEMORY.md` and `USER.md` ride in the same fixed block every turn, capped by
   `memory_char_limit` / `user_char_limit` in `config.yaml` (2,200 / 1,800 chars here ≈ 1,000
   tokens/turn at full). Cut them by the same logic as the index — fewer always-on lines — but by a
   different mechanism: facts move into the skill that governs the task, bulky detail moves into
   `~/.hermes/notes/`, and only calibration with no other home stays. Procedure, including the
   atomic-batch rule that gets past a full store and the staged-record queue:
   `Reference: memory-store-slimming`.

Rank by `body_tokens × uses` FIRST and index chars SECOND. A fat body on a frequently loaded skill
beats any index trim, and it compounds because the skill keeps loading.

Run `scripts/token_audit.py` for all of it in one read-only pass: index tokens/turn, per-skill
`body × uses`, dead skills, slimming candidates, cross-skill duplication.

## Levers, ranked by measured payoff

1. **Slim the top loading bodies into the Reference appendix.** Biggest win, compounds with use. Targets are
   bodies that are >35% tables or fenced code; run the extraction with `skill-slimming` (engine +
   verifier) and keep procedure, thresholds and pitfalls in the body.
2. **Remove dead skills from the index.** A skill with 0 loads over 30+ days costs ~18 tokens/turn
   forever. Each one is ~70 index chars. The lever depends on provenance and the choice is not
   optional: `hermes curator archive <name>` handles local skills (it refuses pinned ones), while
   hub-installed skills are refused outright — `curator: skill 'X' is hub-installed; never archive`
   — and only `hermes skills uninstall <name>` removes them, reversibly with `hermes skills install
   <name>`. Back the directory up before either (Python `tarfile`; see `skill-slimming`), because an
   uninstall takes the files with it. Expect installed packs to dominate the list: of 20 dead
   skills in one pass, 14 were `official`/`skills.sh` and only 4 were archivable.
3. **Collapse a never-firing domain pack into one umbrella plus per-topic references.** Keeps
   the capability offered while cutting e.g. 35 index lines to one. **Only for content you own, and
   only with a refresh mechanism you also write.** An upstream-maintained pack (installed with
   `npx skills add`, a hub tap, or `hermes skills install`) folded by hand drifts: a merged fork of
   the Unity pack sat at 190 reference files with a 32 KB `unity-cli.md` against upstream's 50 KB
   and was archived for it. Fold a vendor pack only when you ship the sync with it — the worked case
   is the `unity` pack's own sync script: it fetches upstream, refreshes only files that still
   match the recorded baseline (`.sync-state.json`), keeps this install's SKILL.md frontmatter, adds
   upstream-new files, and never overwrites a file differing from both upstream and the baseline —
   local edits stay sticky and reported. **No sync script, no fold.** Prefer references over a new
   skill whenever the parent's description already covers the task shape, because a reference is
   lazy (0 cost until read) while a skill's index line is paid every turn (~19 tokens/skill/turn on
   a 175-skill library); but if the trigger wording is genuinely independent, a separate skill is
   correct and folding it makes the content dead.
4. **Descriptions ≤60 chars.** Beyond 60 is free per turn (the loader truncates) but appears in full
   when the skill loads.
5. **Fix circular descriptions — a skill that never fires is worse than a fat one.** A description
   that names the tool instead of the task ("Use when using X") matches only a task that already
   mentions X, so the body never loads and a correct, verified skill contributes nothing. The signal
   is usage contradicting capability: a wired tool with a handful of lifetime calls next to hundreds
   of hand-rolled equivalents for the same job. Rewrite the description to name the task shape
   ("renaming symbols or tracing callers across files"), keep it ≤60 chars, and place the decision
   rule in the skill that governs that class of change too, not only in the tool's own skill.

## Extraction mechanics — two silent failures

Both leave a body that looks slimmed and a reference that is wrong, so check for them explicitly.
(Engine and verifier live in `skill-slimming`; these are the failures the engine does not catch.)

- **Section markers must be headings at the SAME level.** A deeper start paired with a later shallower
  end swallows every section between them into the ref: an `### X` start ended by the file's
  `## References` pulled three whole H2 sections — including the one holding the real content — into a
  file named after the H3. Pick the end as the next heading at the moved unit's own level, then list
  the ref's headings after the move; a ref carrying headers that were not the moved unit's means the
  span was wrong — restore from the backup and redo rather than patching the mess.
- **A bullet-heavy section can still be data.** Bullets are usually rules that must stay in context,
  but they move when they are dated, topic-scoped accumulations: numbering that restarts or runs
  12b/12c/12k, a provider or tool name plus a date in the lead, or one bullet of 10 KB on a single
  topic. Split those by topic (provider quirks vs pipeline/tooling) rather than moving the section
  whole, and keep any cross-cutting rule behind.
- **Back up with Python's `tarfile`, not the shell's `tar`.** The Windows build is bsdtar and rejects
  `--force-local`; MSYS `tar` reads a `C:/...` destination as a remote `host:path` and fails. Verify
  the archive exists before the first write — proceeding after a failed backup is how a removed skill
  ends up with no copy on disk.

## Do not chase (measured non-issues)

- **Cross-skill duplication.** On a real 181-skill library exactly one pair shared more than two
  8-line blocks (14 boilerplate lines). Not a waste class worth auditing every pass.
- **the Reference appendix bulk.** Lazy. Multi-MB reference sets cost nothing until read.
- **Long raw `description:` values.** No per-turn cost — the index truncates to
  `SKILL_PROMPT_DESC_LIMIT = 60` (`agent/skill_utils.py`). Fix them for legibility, not for tokens.
- **Big bodies that are mostly procedure.** Size alone is not waste. A 12k-token body that is 44%
  data is a target; a 5k-token body of pure procedure is not.

## Lifecycle mechanics

- **Archived = absent from the index, NOT from name resolution.** `.archive` is in the loader's
  exclusion list, so an archived skill leaves the index and `skills_list`; the files stay on disk.
  Name lookup still matches basenames under the skills dir, so an archived directory or reference
  file whose name equals a live skill makes `skill_view('<name>')` fail with `Ambiguous skill name`
  — the live skill becomes unloadable and the error blames `external_dirs`. When archiving a copy
  whose name collides (a superseded fork of an installed pack, a reference file named after a
  skill), move it OUT of the skills tree to `~/skill-slim-backup/` rather than into `.archive/`,
  then prove it with one `skill_view('<colliding-name>')` call. Audit the collisions by
  intersecting live `skills/**/SKILL.md` dir names against `.archive/*/SKILL.md` names.
- **Nothing auto-unarchives.** `apply_automatic_transitions` has no archived→active branch, and
  `curator status` "reactivated" only ever means stale→active. An archived skill cannot accrue the
  activity that would revive it, because it is never offered.
- **`restore` does not reset the inactivity clock.** `hermes curator restore <name>` sets the state
  back to active and the next pass re-archives it unless it is used or **pinned**. Restore also lands
  the skill flat at `skills/<name>` (the category path is not reconstructed) and refuses if a hub
  skill owns the name or the skill is bundled (unless `curator.prune_builtins`).
- **`pin` is the protection lever** — exempts a skill from every auto transition regardless of
  provenance. `adopt` writes `created_by: agent`, which is a curator-management flag and not
  authorship proof; it also does not reset the clock, so adopting an idle skill schedules its archive.
- **Never mass-adopt.** Unmanaged skills are already permanently exempt; adopting converts that
  protection into a 30-day fuse. Simulate the pass per skill and show the user the predicted counts
  before running anything.
- **Deletion is a separate path.** Only `hermes curator purge` deletes, it is off by default
  (`curator.archive_ttl_days: 0`), so archives are recoverable indefinitely.
- **The library has a second writer.** `hermes curator` creates and patches skills on its own
  schedule, so a count measured earlier in a session can be wrong later: `hermes curator ledger` lists
  its mutations and `hermes curator rollback <id>` reverses one. Check the ledger when a number moved
  and you did not move it, and mtime-scan the tree to prove your own audit stayed read-only.
- **`environments:` is not a domain switch.** It is an offer-time relevance filter that only
  recognises kanban, docker and s6, and unknown tags fail OPEN — tagging a domain pack with its
  domain name changes nothing. `requires_apps:` fails closed but needs a plugin-declared app;
  `requires_toolsets` is profile-level. For a domain pack the real choices are keep, collapse or
  archive.

## Bundled copies drift silently (the frozen-copy trap)

Every bundled skill is seeded into the profile, and the profile copy is what gets served. The moment
that copy differs from the shipped source by one line, the CLI records it as **user-modified** and
`hermes update` skips it forever: the copy stops tracking upstream and rots in place. Observed: a
citation skill sat two minor versions behind, and a fetch skill kept writing scratch output to `/tmp`,
which native Windows Python cannot read on this box, because the upstream fix never landed.

Audit, then classify — the three outcomes need three different actions:

1. `hermes skills list-modified` gives the flagged set; `hermes skills diff <name>` is the
authoritative test ("matches the stock version" vs a real diff); the shipped source to compare against
is `AppData/Local/hermes/hermes-agent/skills/<category>/<name>/SKILL.md`. Diff line counts rank them:
single-digit diffs are usually artifacts, a version gap shows as tens of lines.
2. **The flag is stored state, not a live diff.** Copying byte-identical stock content over a flagged
copy does NOT clear it — four skills were flagged modified with a zero-line content difference. Clear it
with `hermes skills reset <name>` (`--restore` also takes the stock bytes). Until you reset, the flag
keeps blocking upstream updates even though the file already matches stock.
3. **Upstream is not automatically better — read its cross-references before adopting, and verify the
reference really dangles.** Before calling a pointer broken, check every tier the name can live in: the
active tree, `optional-skills/<category>/<name>` (shipped but not installed), the hub catalog, and the
connector/plugin namespaces. A name missing from the active tree is usually an optional skill or a
connector, not a defect, and asserting otherwise freezes a working skill out of upstream fixes on a
false premise. A keep stands only on a *re-verified* defect (a genuinely renamed or removed target) or on
a local edit that is the better text; the defect goes upstream as a report either way. Re-check the basis
of any keep you inherited before repeating it, and reverse the decision when that basis was wrong.

Then the action is mechanical: **adopt stock** where the local copy is a stale version (back up the dir,
copy the shipped `SKILL.md` and its the Reference appendix over, `hermes skills reset` to clear the flag, then
`hermes skills diff` to prove "matches the stock version"); **reset only** where the bytes already match;
**keep** where the local edit is the correct one. Hub skills are the same question on a different lever:
`hermes skills check` lists installed hub skills with pending updates and `hermes skills update <name>`
applies them. This lever *restores* stock so updates resume — the opposite of slimming a bundled skill,
which is never allowed because updates overwrite it anyway.

## Repair after removals

Dangling names are how a library rots. After any archive/delete pass:

1. `grep -rn "<removed-name>" ~/.hermes/skills --include=SKILL.md`, then fix in this order:
   `related_skills` frontmatter (mechanical, do it first), then instructions that say "load
   `<removed-skill>`", then leave historical prose alone — notes recording past decisions are not
   instructions. A word that matches a removed skill name is not always a reference to it: a
   benchmark corpus or a product named after the tool is prose, and rewriting it corrupts the note.
1b. **Classify the referrer before it protects anything.** A reference from another *dead* skill is
   circular and counts for nothing — only a live (used) skill's reference is a dependency. Then
   split by kind: `related_skills` entries and "consider `<tool>`" alternatives are mechanical to
   repair, so the dead skill still goes; a live skill naming the dead one as the toolchain or
   mechanism for a capability it does not itself provide is a keep. Name the keeps with their
   referrer in the report instead of skipping them silently.
2. Substitute the surviving mechanism, never a new skill: a removed planning skill's row becomes the
   built-in `/plan`; a removed parallel-subagent skill's row becomes `delegate_task`.
3. Check schedulers before archiving: `grep -rl "<name>" ~/.hermes/cron/` for anything a cron job
   may load.
4. Exclude cache and ledger noise (`.hub/index-cache/`, `.curator_ledger.jsonl`) — a bare recursive
   grep across them returns megabytes.

## Pitfalls

- **State the basis of every threshold you write into a skill.** A bare round number ("cap references
  at 15 KB", "slim bodies over 20 KB") reads as a finding and gets audited, and when challenged the
  honest answer is usually that no natural break exists — the measured distribution decays smoothly
  (median 8.2 KB, p75 18.4 KB, p90 29.9 KB) so 15 KB sits near p70 and flags a third of files. Write
  the measurement that fixes the *shape* of the rule (a smooth decay, a bimodal gap, a topical unit
  of ~0.9 KB), and say plainly when the number is a convention chosen for a budget rather than a
  derived boundary. A rule that survives scrutiny is stated as the rule ("one file = one topic"),
  with the number demoted to a tripwire the script can vary.
- **`last_activity_at` does not exist** in `.usage.json`. The keys are `last_used_at`,
  `last_viewed_at`, `last_patched_at`, with `created_at` as the anchor for a never-used skill.
  Reading a missing key silently falls back and inflates every idle count — cross-check a few rows
  against `hermes curator status` before trusting a computed idle table.
- **`use_count: 1` can be an import artifact.** If `last_used_at` equals `created_at` to the
  microsecond, the skill has never actually been loaded; that is the never-used signal, not
  `use_count == 0`.
- **Pass native paths to the audit script.** Bash expands `~` to `/c/Users/...`, which native Python
  resolves against the current drive and silently finds zero files. Use
  `python scripts/token_audit.py C:/Users/<user>/.hermes/skills`.
- **Scope a lint run to what you changed, or it cannot come back clean.** The size lint
  (`skill-slimming`'s `lint.py`) walks the whole library by default and reports the standing
  backlog of over-cap bodies, exiting 1 on findings — a whole-library exit 1 is the library's known
  state, not a regression from your edit, and quoting it as a verification result is wrong. Pass the
  directories you touched as non-flag arguments to restrict the walk, and quote that scoped result; the
  thresholds are `--max-body-kb` (default 10) and `--max-ref-kb` (default 15).
- **Skip unreadable entries instead of aborting the walk.** A hub-install dir raised
  `OSError [WinError 1920]` on `stat()`; the walk must tolerate it.
- **A protected skill still needs reporting.** Bundled, hub, pinned and unmanaged skills cannot be
  edited by an autonomous pass. When the right fix lands on one, name it and recommend
  `hermes curator adopt <name>` (or unpinning) rather than silently skipping.
- **A superseded copy archived in place can be the thing breaking a skill.** If a name suddenly
  resolves ambiguously after a cleanup pass, look in `.archive/` before editing the live skill.
- **Count the index the way the loader does, or a fold inflates your own audit.** The loader prunes
  the Reference appendix, `templates/`, `assets/` and `scripts/` from the index walk, so a SKILL.md nested
  under one is never offered and costs no index line. Any audit that `rglob('SKILL.md')` without that
  prune reports every folded topic as an active skill (34 topics inflated a 135-skill index to 169).
- **Move a skill's own reference files with it.** Folding a skill into a parent's the Reference appendix
  leaves its private notes behind in `.archive/`, and any surviving copy that links them dangles
  (a `ngo-scripting-notes.md` link in the Unity pack pointed into the archive). Walk the moved files'
  outbound links after the fold, not only the parent's.
- **Do not rewrite upstream links to fit the new location.** Topic bodies link a file under their own
  the Reference appendix relative to their own folder; state that resolution rule once in the router body
  instead of editing 34 files, or the sync loses its clean comparison and every future refresh
  fights your edits.
- **Folding does not make the topics' descriptions irrelevant, but it does stop them being paid.**
  Once a topic is a reference, its frontmatter description is never indexed; the sync still preserves
  it (the short descriptions are a local edit) so a later unfold or reinstall keeps the curated text.
- **Never build a patch `old_string` from a displayed tool result when the line carries a credential-shaped
  value.** The output pipeline redacts those, so `Bearer <key>` reaches you as `Bearer ***`, the redaction
  becomes your match text, and the fuzzy matcher writes it into the file and takes neighbouring characters with
  it — a config snippet inside a skill lost its closing backtick and gained a literal `***`. Read the raw bytes
  in Python (`open(path, "rb").read()`) or rewrite the sentence so it carries no placeholder token, then verify
  per line: an odd backtick count (code-fence lines excepted) or a stray `***` means the edit landed wrong. The
  diff the patch returns is where you catch it, before the next session reads the file as authoritative.

## Supporting files

- `scripts/token_audit.py` — the whole audit in one read-only run (index cost, load cost ranking,
  dead skills, slimming candidates, duplication). Pass the skills dir as the only argument.
- `Reference: loader-and-pack-invariants` — indexed-vs-rendered counts, the snapshot-path
  `environments` defect, and the body-hash + known-deviations rules a synced pack must follow.
- `Reference: memory-store-slimming` — cutting `MEMORY.md` / `USER.md`: the atomic-batch rule,
  the staged-record queue in `~/.hermes/pending/memory/`, and the route-before-cut procedure.

## Reference: loader-and-pack-invariants

# Loader and synced-pack invariants

Facts that make a library audit come out wrong if you assume the naive version. Verified on this box;
the counts move as skills are added and as the enabled toolset set changes, so re-measure rather than
quoting a stored number.

## Indexed is not the same as rendered

- `iter_skill_index_files()` counts SKILL.md files on disk. The per-turn block is built by
  `agent.prompt_builder.build_skills_system_prompt()` and *additionally* hides skills whose
  frontmatter conditions fail (platforms, apps, environments, requires_toolsets/tools).
- Never quote the indexed count as the per-turn cost. A forced full scan and the on-disk snapshot
  (`.hermes/.skills_prompt_snapshot.json`) can disagree with each other and with the file count:
  observed 135 indexed, 128 rendered on a forced full scan, 130 through the snapshot.
- The hidden set is not only platform gates: 5 skills were `platforms: [macos]` / `[linux, macos]`
  (correctly hidden on Windows) and one was `environments: [kanban]`, leaking through the snapshot
  path described below. Count the hidden set before claiming "everything is offered".
- Measure the block, not the file list. `token_audit.py` prints both the field sum (name +
  description, no formatting) and the rendered size; the field sum understates by the per-line
  indentation plus the surrounding guidance.

## Upstream defect: the snapshot path drops the `environments` gate

- The snapshot branch of `_build_skills_system_prompt_inner` re-checks only platforms and apps
  (`skill_matches_platform_list(...) and skill_matches_apps(...)`), and `extract_skill_conditions()`
  in `skill_utils.py` never captures `environments` at all. The full-scan branch goes through
  `_parse_skill_file`, which does check it.
- Effect: an `environments:`-gated skill leaks into the block whenever its `requires_toolsets` is
  satisfied (observed: `sdlc-review`, `environments: [kanban]`). One extra entry, not an agent
  correctness risk, but it makes the entry count vary by enabled toolset. Do not patch the installed
  package: an update clobbers it, and the fix belongs upstream.

## The library has a second writer

- `hermes curator` is a background task that creates, patches, prunes and archives skills on its own
  schedule (default every 7 days, prune-only unless the LLM consolidation pass is opted in). A count
  measured at the start of a session can be wrong by the end of it: a curator-created skill appeared
  mid-audit and moved the index by one, with no action from the session.
- `hermes curator ledger` is the mutation log (id, actor, action, skill); `hermes curator rollback <id>`
  reverses a single mutation; `hermes curator status` gives the managed/unmanaged split and the
  last-pass summary. When a number moved and you did not move it, read the ledger before theorising.
- Prove your own audit was read-only before reporting it: list every file under the skills tree whose
  mtime falls inside the audit window and account for each one. Verifiers or probes that wrote into
  the live tree invalidate the audit they were part of.

## A synced pack must compare BODY hashes, not file hashes

- When a pack rewrites a synced file's frontmatter (a short local description over an upstream long
  one), that file can never hash equal to upstream. If the baseline stores the upstream *file* hash
  while the equality test compares *bodies*, the "upstream moved" branch is dead code and an upstream
  body edit is misreported as a local edit, so the refresh silently never happens.
- Rule: for any file whose frontmatter is ours, hash `body_of(text).strip("\n")` for both the compare
  and the baseline write.
- **An allowlist suppresses the signal, so it can hide a broken mechanism.** A pack that reported the
  same N "known local deviations" every run looked healthy while its SKILL.md refresh branch was dead
  code: the allowlist said "expected" about files the sync could no longer update. A clean-looking
  report is not evidence that the mechanism works; probe the mechanism instead (below).
- Deliberate local deviations (a reference tree split locally, for example) belong in a
  `.sync-local-edits.json` allowlist beside the state file, so the check reports them as known and
  still exits 0. An *unlisted* local edit should exit non-zero; a known one must not, or the check
  becomes noise nobody reads.
- Exit codes should cover only actionable drift: upstream moved, a new upstream file, an unknown
  local edit. `gone upstream` and known deviations are informational.

## Prove a sync script still works (fixture probe)

Never test a sync script against the live pack. Copy the skill dir into scratch, then:

1. **Stub the fetch.** Replace the single call site that resolves upstream
   (`up_root, tmp = fetch_upstream(...)` / `base, label = fetch_source(...)`) with a fixture path plus
   a throwaway tmp dir. Match the real return signature or the script exits 2.
2. **Build a fixture pair:** an upstream topic dir with a SKILL.md (upstream frontmatter) and a
   a `references/` file, and the same topic in the pack copy with OUR frontmatter over the same body.
3. **Baseline, then walk every case and assert:** an upstream body edit reports `upstream-moved` (not
   `locally-edited`) and exits 1; `--apply` rewrites the body and keeps our frontmatter; a file listed
   in `.sync-local-edits.json` reports as known-local with exit 0; an unlisted local edit exits 1; a new
   upstream file reports `new` and exits 1, and `--apply` pulls it in; a re-check exits 0.
4. **Hash the live originals** before and after to prove the probe stayed in scratch.

## Reference: memory-store-slimming

# Slimming the USER and MEMORY stores

Two files ride in the system prompt every turn: `~/.hermes/memories/MEMORY.md` (agent notes) and
`~/.hermes/memories/USER.md` (who the user is). Caps live in `~/.hermes/config.yaml` as
`memory_char_limit` (default 2,200) and `user_char_limit` (default 1,800). At 4,000 chars combined
the pair costs roughly 1,000 tokens/turn, and a store with no headroom left stops being able to
absorb new facts — which is why consolidation records start staging instead.

## The rule that makes the rest work

**The cap is checked only on the FINAL result of a batch.** One
`memory(target=..., operations=[...])` call can remove, replace and add together even when the
additions alone would overflow. That is the only way past a store sitting at 98% — issue the adds
first and the batch is refused and nothing lands. So: compose the whole change for a store as ONE
batch, and if it is refused, the fix is to free more room in the same batch, never to split it.

## Procedure

1. **Measure both stores**: chars vs cap, entry count, and per-entry size. Know which store is the
   binding constraint before proposing anything.
2. **Back up first** — `~/.hermes/memories/*.md`, `~/.hermes/pending/memory/*.json`, and
   `~/.hermes/notes/personal-facts.md` into `~/memory-slim-backup/<date>/`.
3. **Drain the staged queue** in `~/.hermes/pending/memory/*.json`. `memory.write_approval` and
   `skills.write_approval` default to false, so records sit there indefinitely; the drain surface is
   `/memory pending`, `/memory approve <id|all>`, `/memory reject <id|all>`, `/memory approval on|off`.
   Approval replays each op against the entry it pinned when staged and refuses if that entry changed
   since; a record containing any op with no pinned entry is refused *whole* because batches are
   atomic, so such a record can never apply and must be rejected. Read every record before deciding:
   staged content is a proposal, not verified fact, and a record can carry a claim the session can
   disprove (a "file not found" note about a file that exists).
4. **Route before cutting.** For each fact ask where it belongs: task-specific detail and pitfalls go
   into the skill that governs that task — grep the skill for the fact FIRST and only then cut it;
   bulky personal, project and coursework detail goes into `~/.hermes/notes/personal-facts.md` with a
   pointer left in the store; always-on calibration (reply shape, medical constraints, machine
   permissions, work context, standing standards) has no other home and stays. A fact that belongs
   nowhere stays too — a store below its cap costs little, and a lost preference costs the user.
5. **Write one atomic batch per store**: replace the entries being rewritten, remove the entries whose
   content moved, add the new facts. Ops are `{action: add|replace|remove, content?, old_text?}`;
   `old_text` only identifies the entry, and for `replace`, `content` is the complete new entry.
6. **Verify after**: re-read both stores, then probe that every fact which left still resolves in its
   new home. A fact that resolves nowhere was deleted, not moved.

## Pitfalls

- **Two staged records editing the same entry must be merged into ONE replace.** Approving the
  second one alone is refused, because the text it pinned no longer exists.
- **Pointers must stay honest.** After moving facts into a skill or into `personal-facts.md`, check
  that the store's pointer line names the right file and that the file's own line is not stale.
- **Do not restate in the store what the environment already injects.** Python version, tool lists
  and other facts carried by the runtime block are paid for twice; keep only the non-obvious part
  (a pip flag, a path convention).
- **A terse follow-up like "can we get these slimmer?" refers to the thread's subject.** When a
  report ends by flagging N items, the user's next "these" is usually the thing the conversation was
  about, not the caveats you just listed — confirm before spending a pass on the wrong object.
