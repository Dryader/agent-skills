---
name: skill-pack-import
description: Use when installing, optimizing or applying a skill pack.
---


# Importing external skill packs into Hermes

Goal: make a third-party skill collection (GitHub skill repos, Claude Code/Codex/Grok plugins) load on demand in Hermes without ever pulling its file contents through the conversation (a 2 MB pack is hundreds of thousands of tokens of context).

## Triage first: a catalog review is a verdict task, not an install task

When the ask is "anything in this pack worth having, now or later?", the deliverable is a per-skill verdict. Select before you copy: most catalogs lose on inspection, and copying forty skills to find that out is the expensive mistake. Recipe with runnable commands: `Reference: catalog-triage`.

1. **Inventory metadata only.** Aggregate per-skill byte sizes and file counts from the repo tree, then read frontmatter heads (name + description) of every SKILL.md in one Python pass. Bodies of at most the two or three finalists get read, and only the head of those.
2. **Prior-art check against the local library — run this BEFORE judging anything attractive.**
   - Grep the registered skills AND `~/.hermes/skills/.archive/` for the skill name and for the capability class ("threat model", "xlsx", "playwright"). A populated `.archive/` means the user already evaluated and culled that category: "add X" is often "restore X and repair what pointed at it".
   - Grep current `SKILL.md` files for `related_skills:` entries and body instructions naming skills that `hermes skills list` does not return. A cull leaves dangling pointers (live deck skills still instructing "for .pptx output use the `powerpoint` skill" after that skill was archived), and the upstream catalog's newer copy is the cheapest repair. Registration ground truth is `hermes skills list`, never the directory listing.
   - To claim a capability is NEW, prove it by absence: grep the whole registered library for the class term, quote the zero-hit result, and say which existing skill is the nearest miss.
3. **Upstream health.** Read the repo README and `pushed_at` first. Catalogs get deprecated in favour of a successor repo: still usable as a frozen content library for reference-heavy skills, but its *harness plumbing* skills (skill-creator, skill-installer, plugin scaffolding) are obsolete by definition — skip anything whose function the running harness already owns.
4. **License per skill.** Catalogs mix licenses. Read each skill's own `LICENSE.txt`: permissive (Apache-2.0, MIT) can be adapted into the user's public skills repo with attribution; proprietary source-available stays local. Check before recommending, not before installing.
5. **Hub before clone.** `hermes skills search <name>` returns the source label (Anthropic, official, skills.sh, clawhub) and the exact install id, so a handful of picks installs one command each. Clone only for a bulk pack or as a refresh source.
6. **Dependency reality check.** For any pick whose value sits in its bundled scripts, check the runtime on both interpreters and state what needs installing. A skill whose script cannot run is a skill you have not evaluated.
7. **Answer shape.** Table of `skill | size | verdict | why`, then a grouped "no, and why" list that accounts for EVERY entry in the catalog, then a named trigger per maybe, ranked by usefulness to this user rather than by novelty. The user reads an unaccounted entry as a gap in the review.

## Procedure

1. **Clone to a persistent source dir** (the clone stays as the update source; for a catalog review, settle the picks first, since cloning is not part of triage):
   `git clone --depth 1 <url> C:/Users/<user>/<repo-name>`
   Immediately verify the target exists where intended (see pitfalls).
2. **Inventory with metadata only**: names + byte sizes, never bodies — `find skills -name SKILL.md -printf '%s\t%h\n'`, `du -sh`, `find ... | wc -l`. Platform packaging (.claude-plugin/, .codex-plugin/, .agents/, .github/) is irrelevant to Hermes; content lives in `skills/<name>/SKILL.md` plus sibling dirs.
3. **Check name collisions** against the registry: intersect the pack's skill dir names with names in `hermes skills list` output.
4. **Copy whole skill directories on disk** into a lowercase category dir:
   `mkdir -p ~/.hermes/skills/<category> && cd <clone>/skills && for d in */; do cp -r "$d" ~/.hermes/skills/<category>/; done`
   Copy the entire dir, never SKILL.md alone — bodies reference the Reference appendix, `resources/`, `scripts/` siblings by relative path.
5. **Validate frontmatter with metadata-only extraction**: an awk loop printing `dir | name | description length` per SKILL.md — name must equal dir name, description must be non-empty. Claude Code-style frontmatter (name + description only) is Hermes-compatible unchanged; multi-line folded scalars (`>`, `>-`) are valid YAML, not corruption.
6. **Verify registration via the CLI registry, not the filesystem**: `hermes skills list` must show each skill under the new category as enabled. The session skill index rebuilds per session, so the pack surfaces next session; the CLI list is the immediate ground truth.
7. **Report**: install path, counts, verification output, and the always-on index cost of the pack's descriptions (long descriptions run roughly 1k tokens/session per ~30 skills) if the user has not already approved that overhead.

## Refresh after upstream updates

`git pull` in the source clone, diff each pack skill dir against the installed copy, re-copy changed dirs, and remove installed dirs upstream deleted (renames otherwise leave stale duplicates that shadow the new names).

After any refresh, re-run the dangling-pointer greps from Triage: an upstream rename or deletion leaves `related_skills:` entries and body instructions pointing at skills that no longer resolve.

## After the import: optimizing a vendor pack

Installing is half the job. Vendor skills are written for a marketplace listing, not for a per-turn
context budget. Measured on the Unity-Technologies pack (34 skills), in this order:

1. **Trim every description to the library convention (~60 chars, trigger first).** Description
   lines are paid every turn. That pack shipped 7,849 chars of description (~1,962 tokens/turn);
   trimmed to 1,923 chars (~480). Rewrite as `Use when <trigger>.` / `Use for <job>.`, keep the
   trigger inside the first 57 chars, then re-parse the frontmatter to prove the new line landed:
   vendor descriptions are often block scalars (`>`, `|`, `|-`) or carry trailing keyword lists,
   and a naive regex silently leaves the original text in place (8 of 34 failed the first pass).
2. **Hunt for a stale fork of the same pack BEFORE adding anything.** A past session may have
   merged the pack into one skill's the Reference appendix (here: 190 files, 1.9 MB, an older revision —
   its `unity-cli.md` was 32 KB where upstream is 50 KB). Two copies of the same guidance at
   different revisions is worse than duplication, because nothing says which is canonical.
   Collapse the fork into a router: environment facts and your own notes stay, a topic map points
   at the installed skills by name, and the fork is tarred to `~/skill-slim-backup/` and moved
   **outside the skills tree** — a copy left in `.archive/` keeps its basename in name resolution
   and makes `skill_view('<name>')` fail as ambiguous for every skill it shadows.
3. **Split references over ~15 KB** — see skill-slimming for the cap rule and the split script that ships with `skill-slimming`.
4. **Do not gut the bodies.** Score data share per *section*, not per line: vendor bodies are
   usually procedure (unity-cli 28% table lines, physics-3d-collision 36%) and moving rules the
   agent needs in context is a downgrade. Only lookup tables and catalogs move.
5. **Account for the pack's own noise**: `CHANGELOG.md` and `SECURITY.md` ride along, and a skill
   CHANGELOG can be 48 KB. Inert (never loaded) — leave or delete, but do not count it as a
   reference when reporting sizes.
6. **Refresh caveat**: every trim and split is local, and `git pull` + re-copy overwrites it.
   Record the rule where the next session will look, and re-apply after a refresh.

## Applying a pack: auditing a project against its skills

An imported pack only pays for its index cost when it changes what you do. The procedure that works:

1. **Load by categorized path** (`skill_view('<category>/<name>')`): a bare name fails with
   `Ambiguous skill name` whenever an archived or reference copy shares it, and the error blames
   `external_dirs`, which sends you looking in the wrong place.
2. **Read for the pack's checkable rules**, not its prose: conventions tables, "NEVER use" lists,
   required prerequisites, and the mechanism the pack says to use (a generated config rather than a
   hand-edited one). Each becomes a test.
3. **Run the static checks first.** Grep the project for every forbidden pattern, and for use of the
   deprecated namespace or hand-rolled mechanism the pack warns against. Cheap, and it finds real
   deviations; report a zero-finding result as evidence rather than skipping the step.
4. **Then the tool-driven check** for what static reading cannot see (a live editor, an analyzer, a
   build). If the tool needs a prerequisite the project lacks — analyzer rules, a package — give the
   exact enabling command and let the owner decide: installing into a graded or shipped project is
   their call, and a blocked check is a finding, not a failure.
5. **Sort the results into applied / judged-and-left / blocked, with a reason for each judged item.**
   A pack rule can lose to the project's own structure (code lives under `Scripts/`, not beside the
   UI assets) or to a change that costs an import round-trip for no functional gain. Say which and
   why; silently complying and silently skipping are both wrong.
6. **Verify each fix on the project's own acceptance path before committing**, and commit one
   purpose per changeset. A pack rule applied and unverified is a regression with a citation.
7. **Record the outcome where the project's next session will look** — which skills were consulted,
   what changed, what was judged, what is blocked. The vendor copies stay untouched, so a refresh
   cannot lose the local decisions.

## Pitfalls

- Pass native paths (`C:/Users/...`) to native Windows tools. In the MSYS shell, `git clone <url> /c/Users/...` is NOT path-translated: the repo silently lands in `C:\c\Users\...`. Check clone destinations with `ls` before building on them.
- Never read pack file contents into context during an import — that defeats the purpose. Metadata (names, byte sizes, frontmatter heads) is all the agent needs; file-to-file `cp` performs the install.
- Do not use skill_manage for bulk imports: its create/write_file ops carry full file content through the context window, and its support-file path allowlist may not match arbitrary repo layouts. skill_manage is for small authored skills; disk copies are for packs.
- Do not infer surfacing from directory existence: some on-disk categories under ~/.hermes/skills (plugin-installed, DESCRIPTION.md-marked dirs like apple/ or gaming/) never appear in the session skill index. Registration proof is `hermes skills list`, which is registry-backed and immediate.
- Estimate the per-session index cost before bulk-registering a pack: the session prompt shows truncated descriptions of every enabled skill, so a 31-skill pack is a permanent, always-on overhead the user should approve first.
- Fetch pack metadata in one pass rather than a shell loop: a single Python script that reads the API tree, aggregates per-skill bytes, then fetches each SKILL.md and prints `name | description | body size` returns the whole inventory in one call and tolerates odd paths. A bash `while read` + `curl -o` loop hands you a partial result you then have to re-derive.
- Frontmatter shapes vary across packs, so never report a parse miss as "no description": Claude-style is `name` + `description`, descriptions also appear as folded scalars (`>`, `|-`) or nested under `metadata:`, and some files carry none at all. Print the raw frontmatter block when the parse comes up short and read it.
- **Check for an official installer before hand-folding a pack.** A CLI-installed pack may ship one (`twg doctor` flags a missing canonical install and names `twg skills install --yes`, which lands in `~/.agents/skills`), and the released artifact can differ from the public repo mirror in both directions (the twg release ships `twg-artifacts`, omits `twg-bench-lite`). Prefer the local canonical install as the sync source.

## Reference: catalog-triage

# Catalog triage: sizing a skill pack without reading its bodies

Read-only inventory of a third-party skills repo that follows `skills/<name>/SKILL.md`.
Use it to answer "is any of this worth having?" before deciding what to copy.

## 1. Per-skill size and file count

```bash
curl -sL "https://api.github.com/repos/<owner>/<repo>/git/trees/main?recursive=1" -o tree.json
python - <<'EOF'
import json, collections
d = json.load(open('tree.json'))
# Repos nest one level (skills/<name>) or two (skills/.curated/<name>).
agg, cnt = collections.Counter(), collections.Counter()
for e in d.get('tree', []):
    p = e['path']
    if p.startswith('skills/') and e['type'] == 'blob':
        parts = p.split('/')
        key = '/'.join(parts[1:3]) if parts[1].startswith('.') else parts[1]
        agg[key] += e.get('size', 0); cnt[key] += 1
for k, v in sorted(agg.items()):
    print(f"{k:36s} {v/1024:8.1f} KB  files={cnt[k]}")
EOF
```

Read the shape before reading any content: a multi-megabyte folder is usually bundled fonts
or ISO schema files, and a 400 KB folder is usually a per-language reference corpus. Both are
cheap at rest, because only the description sits in the session prompt; the corpus loads only
when the skill fires.

## 2. Frontmatter sweep, one pass, no bodies

```python
import json, re, urllib.request
d = json.load(open('tree.json'))
paths = sorted(e['path'] for e in d['tree'] if e['path'].endswith('SKILL.md'))
for p in paths:
    t = urllib.request.urlopen('https://raw.githubusercontent.com/<owner>/<repo>/main/' + p,
                               timeout=20).read().decode('utf-8', 'replace')
    m = re.match(r'---\n(.*?)\n---', t, re.S)
    fm = m.group(1) if m else ''
    desc = re.search(r'description:\s*(.*?)(?=\n[a-zA-Z_-]+:|\Z)', fm, re.S)
    print('###', p, '| body', len(t), 'chars')
    print('   ', ' '.join((desc.group(1) if desc else '').split())[:300])
    if not desc or len(desc.group(1).strip()) < 20:
        print('    RAW:', repr(fm[:400]))
```

The RAW line matters: descriptions appear as folded scalars (`>`, `|-`), inside a nested
`metadata:` block, or not at all, so a short or empty parse means "look by hand", not
"no description".

## 3. Local prior-art and dangling-pointer greps

These decide the recommendation, and they are local, so run them before judging attractiveness.

```bash
# already tried and culled? a populated archive says yes
ls ~/.hermes/skills/.archive/ | grep -iE '<skill-name>|<capability-class>'
# pointers left behind by a cull
ls ~/.hermes/skills/*/ | head -50                       # what is actually registered
hermes skills list | grep -iE '<skill-name>|<capability-class>'
grep -rln "<skill-name>" ~/.hermes/skills --include=SKILL.md | grep -v '/.archive/'
# prove a capability is absent from the registered library
for k in "<capability term>"; do grep -rli "$k" ~/.hermes/skills --include=SKILL.md | grep -v '/.archive/'; done
```

`hermes skills list` is registration ground truth. A directory under `~/.hermes/skills` that the
registry does not list (archive entries, plugin-installed categories, DESCRIPTION.md-marked dirs)
is invisible to the session skill index even though it exists on disk.

## 4. Per-skill license spot check

```bash
curl -sL "https://raw.githubusercontent.com/<owner>/<repo>/main/skills/<path>/LICENSE.txt" | head -5
```

`Apache License` / MIT reusables can be adapted into a public skills repo with attribution;
a proprietary or source-available header means local use only. Some catalogs reuse the same
license file for every skill, others vary per skill (brand-partner skills often carry the
partner's own MIT), so check the specific skill you are recommending, not the repo root.
