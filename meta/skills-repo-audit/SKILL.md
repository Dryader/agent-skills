---
name: skills-repo-audit
description: Audit skills repos: overlaps, broken refs, PII, thin skills.
tags: [meta, skills, audit, portfolio, quality, pii]
related_skills: [skill-audit]
---


# Skills Repository Audit (content quality, portfolio readiness)

Class of work: reviewing a whole collection of SKILL.md files (a personal library, a portfolio repo about to go public, or a periodic hygiene pass) for content quality. Delivers: one-line verdict per skill, ranked merge candidates, and a file-level issues list. READ-ONLY — report, never modify the audited repo. Recommend merges and trims, never wholesale deletion.

Use when: preparing a skills repo for publication, after big merge/absorption work, on a schedule, or asked "do these skills overlap / is PII left / which are thin". Complement to `skill-audit` (per-skill semantic correctness); this is repo-level structure/hygiene.

## Workflow

1. INVENTORY. Count and size every skill:
   - `find . -name SKILL.md -not -path './.git/*' | wc -l` — SKILL.md is a FILE; `find -type d -name SKILL.md` finds nothing.
   - Per skill: `for d in $(find . -name SKILL.md -not -path './.git/*' -exec dirname {} \; | sort); do printf "== %s: %s files, %s lines\n" "$d" "$(find "$d" -type f | wc -l)" "$(wc -l < "$d/SKILL.md")"; done`
   - List support files: `find <skill> -type f -not -name SKILL.md | sort`. This alone exposes near-duplicate references (e.g. backtest-toolkit.md + backtest-toolkit-patches.md in one dir) and 96-file reference dirs (oversized knowledge bases that should be split or archived).
   - Cross-check README claims (skill count, file count, install example paths) against the tree — they drift.

2. SCOPE MAP. Extract frontmatter name+description for every skill and print side by side. Handle folded descriptions: `description: >` and `description: |` span multiple lines — regex the whole frontmatter block, not a single line. The one-line map is the fastest overlap detector: two skills whose descriptions name the same tools/firms/domain = merge candidates.

3. READ STRATEGY. Read small SKILL.md files (<~80 lines) fully; large ones: head ~1300-2600 chars + targeted greps for the rest. Batch reads via execute_code but CAP per-file print length — stdout truncates silently; re-run narrower for anything cut.

4. BROKEN-REFERENCE SCAN (script it, then verify by hand). Regex all backticked `*.md|py|sh|ps1|kql|tex|html|json` tokens in each SKILL.md, resolve against the skill dir, flag missing. Worked scanner (this session): iterate files, `re.finditer(r'`?([A-Za-z0-9_./-]+\.(?:md|py|sh|ps1|kql|tex|html|json|txt|bib|bst|sty|pdf|csv))`?', content)`, skip http/git@ prefixes, strip #anchors, check `os.path.exists(dirname+ref)`, also try basename-in-skill-dir. THEN read the context of every flag: ~90% are false positives (example code names like `src/auth.py`, illustrative PDFs, /tmp paths, out-of-repo personal pipelines like `~/portfolio_audit/`). Real breakage classes:
   - path exists in ANOTHER skill's the Reference appendix — relocated/cross-skill reference; report as moved, not missing
   - the Reference appendixabsorbed/<name>/` dirs referenced by an umbrella skill that never shipped — verify absorbed/ contents directly (this session: 1 of 4 shipped)
   - `related_skills` frontmatter naming absorbed/deleted skills
   - absolute install-layout paths (`${HERMES_HOME}/skills/...`) that don't match the repo layout
   - advertised template/asset dirs (a "deck library" listing 10 dirs with 2 shipped)

4b. CROSS-REF INTEGRITY (scripted — 6 checks). Run `python3 scripts/crossref_audit.py <repo>`: (1) every the Reference appendix|scripts/|templates/ path mention in every .md resolves (bases: file dir, skill dir, repo root); (2) every related_skills frontmatter entry resolves (in-repo skill or allowed bundled); (3) frontmatter name==folder + description present; (4) deleted-skill names appear only as historical provenance; (5) duplicate relative paths across skills; (6) README category lists/counts vs tree. The script's false-positive guards are the hard-won part — do NOT re-derive them ad hoc:
   - MULTI-SEGMENT PREFIX: `career/resume-engineering/the Reference appendixfoo.md` — a single-segment regex captures only the Reference appendixfoo.md` and false-flags a valid cross-skill ref. Capture `(?:[A-Za-z0-9_.-]+[/\\])*` before the keyword and resolve from the repo ROOT (this session: 5 of 17 first-pass flags were this).
   - URL GUARD: check for "http" in the text BEFORE the match, not "://" — the `//` lands inside the token, so "://" straddles the match boundary (`https://raw.githubusercontent.com/.../main/scripts/<name>.sh`).
   - ABSOLUTE/HOME/ENV/DRIVE contexts: token starting with `/` or `\`; `~` prefix (pre may end in bare `~` with the `/` inside the token — `python3 ~/.hermes/scripts/x.py`); `${VAR}` expansion (`${HERMES_HOME}/skills/...`); `C:\` drive; hidden-dir first segment (`.hermes/...`).
   - NOUN PHRASES that are not paths: "scripts/references" (README spec intro), "scripts/backends" (pricing prose). Verify each against the corpus, keep in PHRASE_TOKENS.
   - `SKILL_DIR/scripts/<name>.py` placeholder: substitute the skill's own dir.
   - related_skills can be nested under `metadata: hermes:` — `yaml.safe_load(fm).get("related_skills")` returns None and silently skips the check. Scan frontmatter LINES at any indentation (inline `[a, b]` and block `- item` forms). This session: 5 dangling entries (mcporter, test-driven-development x2, requesting-code-review x2) were only visible after this fix.
   - DELETED-NAME scan: provenance wording lives in the SECTION HEADER ("## Absorbed skills (Aug 9 2026 consolidation) ... merged into this umbrella") while the flagged bullet is lines below it — look back ~5 lines, not just the current line. Ambiguous names like "plan" only match in explicit skill-reference contexts (`skill_view("plan")`, `plan` backticks, related_skills entries) — generic English ("power plan", "a plan") is noise.
   - README "N files" claim: compare against the ON-DISK count; the git-tracked count differs when the working tree has uncommitted changes (4 modified + 1 untracked this session) — don't flag the README for that.
   Then hand-verify every FAIL with its context line; the first scripted pass on a real 64-skill repo produced ~50% false positives that the guards above eliminated.

5. PII / SCRUB-CONSISTENCY GREPS.
   - `grep -rn -E "(/home/|/mnt/)" --include="*.md" --include="*.py" --include="*.sh" --include="*.ps1" .`
   - `grep -rn -E "C:\\\\Users"` (same includes)
   - `grep -rn -E "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"` then filter example/contoso/placeholder domains
   - Placeholder drift: `grep -rln "Users/the user" .` — a scrub that replaced the real username with the literal phrase "the user" (inconsistent with <user> elsewhere) is an artifact, not a successful scrub
   - GitHub username / private-repo names in references (`git remote -v` gives the account handle; references naming private repos + their secrets/state structure = leak)
   - Personal finance specifics: concrete holdings tickers with weights, account sizes, bank/card products, TFSA decisions
   - Verbatim user chat quotes (voice-profile files are the usual home)
   - Employer-context residue: sector + fleet size + role + internal-pitch anecdotes survive even when the employer NAME was placeholder-ed
   - EMPLOYER-SCRUB INCONSISTENCY (found Aug 2026): a doc listing MULTIPLE employers can have one scrubbed to `[employer]` and a second left verbatim in the SAME file (resume-template-map.md kept "[previous employer]" while the other employer was [employer]). Verify EVERY employer line in career/resume files, not just the first.
   - Private-repo local-path names: `~/portfolio_signals` style local paths naming a private repo (portfolio-toolkit-scaleup.md) — same leak class as private repo names in URLs; they are on the standard battery for that reason.
   - Dollar portfolio values in finance/ docs ("$30K portfolio", "~$3,054 avg position") — small retail totals are personally identifying; owners usually want them flagged even when tickers are explicitly expected. Flag rather than assume.
   - MACHINE-FINGERPRINT CLASS (Aug 2026): exact hardware spec in config/hardening skills — board model (AORUS ELITE AX V2), BIOS revision strings ("FH BIOS"), exact CPU+GPU SKUs (Ryzen 5 5600 + RX 6800 XT), NVMe controller model (Phison PS5016), installed-app inventories (MSMQ/Parsec/SQLWriter/JDK). The COMPOSITE spec identifies the machine; CPU-FAMILY technical content (Zen 3 MBEC support, benchmark tables citing Ryzen 5800X3D) is transferable platform knowledge and stays. Scrub the SKUs and board/BIOS tokens, keep the family-level facts.
   - CORPUS-STAT CLASS: measured baselines of the owner's own data ("305 sessions / 31,471 messages / ~1% recall") survive in agent-evaluation and memory skills long after the finance numbers are gone — same identifying class, different domain. Genericize: "a multi-month session-corpus audit ... a small fraction".
   - BATTERY SELF-REFERENCE: the repo's own PII-scan command (AGENTS.md grep) must use GENERIC pattern classes — a battery that lists the owner's name/school/employer embeds PII in the repo, and the auditor will flag it as "the only place those strings exist". Generic classes + a note that the personal-term list is maintained outside the repo.
   - Surname-after-scrub pattern: `the user [A-Z][a-z]+` (a scrubbed name immediately followed by a capitalised surname) and `Mr|Ms|Mrs [A-Z][a-z]+`. Filter month names ("the user Aug" is a false positive).
   - Profile-URL class: every `linkedin.com/in/` and `github.com/` hit must be owner-handle, a placeholder ([handle], <owner>/<repo>, $GH_USER, o/r), or a public vendor/known repo; anything else is a flag. Public-figure names inside vendor citations (analyst names) are not PII.
   - KEY-FRAGMENT RECOVERY: when a battery cites "known key fragments" without enumerating them, session_search prior scrub/audit sessions for the fragment list; if unrecoverable, run a superset built from context (prior employer names, surnames seen in old scrub examples).
   - SWEEP MECHANICS: build `FILES=$(find . -type f -not -path './.git/*' -not -name '*.pdf')` and grep $FILES directly — `--include` filters silently skip extensionless files (LICENSE, README, Makefile, .bst/.sty); a filtered first pass MUST be re-run unfiltered.
   - FALSE-POSITIVE FILTERS before reporting: postal-code regex hits hex color codes (#f0f0f0) — drop '#'-prefixed tokens; case-insensitive \bWise\b hits "thesis-wise"; 9-digit runs are often article IDs (CyberArk 000050743), not SINs — require 3-3-3 grouping; long base64-alphabet tokens are usually KQL/DB identifiers (LongTermDebtAndCapitalLeaseObligations...) — require mixed case+digits+entropy >4.5; vendor template phones/emails (AAAI 1-202-360-4062, name@example.org), known Defender ASR GUIDs, DOIs, and paper-hash URLs in vendor .bib are expected noise. Also allowlist: `C:\Users\Public` and other system profiles; vendor example domains (`contoso.com`, `example.com`, `fabrikam.com`); GitHub noreply addresses (`*@users.noreply.github.com`); npm `package@version` specs (`brave-search-mcp-server@2.1.3` matches a naive email regex — require an alphabetic TLD); 13-digit epoch constants (Snowflake `1420070400000`); and any digit run with a leading zero (require a non-zero leading digit for phone-shaped hits, which also clears zero-padded article ids).
   - UNENFORCED-GATE CLASS (report as a finding, not a defect): the repo's AGENTS.md or README documents validation checks as copy-pasted heredocs that only print their results, and no CI runs them — the gate exists on paper, nothing ever fails, and a reader who trusts the documented gate repeats the repo's own unverified claims. Fix shape to recommend: extract the snippets into `scripts/validate_*.py` that exits non-zero, add a workflow to run it on push and pull request, and update the README counts the new files change. Also note whether the identity terms the battery needs are hardcoded in the repo (see BATTERY SELF-REFERENCE above) — they belong in an env var or CI secret.
   - Re-runnable battery with allowlists + filters: `scripts/pii_sweep.py <repo_dir>` (prints PASS/FAIL per class with file:line evidence).

6. STALENESS. `grep -rn -E "20(24|25)" --include="SKILL.md" .` then read context. Prior-year dates are fine when stamped as findings ("verified Aug 2026"); flags are live deadlines in templates, undated "as of" claims, and conflicting instructions (e.g. two planning skills with different plan-file save paths).

7. OVERLAP DETECTION beyond descriptions:
   - identical verbatim blocks in two SKILL.md files (same auth-setup shell block copy-pasted across 3 github skills; same "WHY this matters" examples in 3 enterprise skills) — grep a distinctive shared sentence
   - the same reference filename in two skills' the Reference appendix dirs
   - one skill's body being a doctrine subset of another's (compare line counts + shared firm/tool lists)

## Merge/absorption commit audit (post-restructure)

Use when the repo just went through a restructure commit (skills absorbed into survivors) and the job is verifying merge quality, not re-auditing the whole repo. Read-only.

1. PROVENANCE MAP from git, never from the notes: `git show <merge> --name-status` → rename lines `R<NNN> <old> <new>`. R100 = pure move (content untouched); R0xx = moved WITH modifications = the absorbed bodies; D = deleted. Every '## Absorbed content' note in a survivor must resolve 1:1 to an R0xx/R100 line. Notes naming files that pre-existed in the survivor (`git ls-tree <parent> --name-only <survivor-dir>`) are misattributed — found one: a note claimed an absorbed file that git proved pre-existed (only a 1-line PII scrub changed it).
2. HEADER / PLACEMENT. Absorbed SKILL.md bodies get a dated 'Absorbed from the <skill> skill...' header; plain references that moved alongside don't — that IS the convention, don't flag it. Absorbed notes go AFTER the closing `---` of frontmatter (`grep -n '^---' SKILL.md` — closes at 2nd occurrence; note must be in the tail).
3. DUPLICATES. (a) Same basename in two skills: the deleted copy must be a D line; confirm the surviving blob is the intended one via `git cat-file -s HEAD:<path>` vs `git show <parent>:<deleted-path> | wc -c`. (b) Differently-named near-duplicates (canada-firms.md vs canada-firm-landscape.md) evade basename `uniq -d`: same dir + sizes within ~15% + same entity/tool lists = versions of one doc. Then check which file the survivor SKILL.md body references vs which the absorbed files reference — split pointers mean no canonical file.
4. STALE REFS IN ABSORBED FILES. Relative the Reference appendixx.md` refs inside absorbed files resolve against the NEW skill dir — verify each exists there (moved files usually travel together). Machine-local paths (`~/portfolio_audit/`, `~/.hermes/...`) are intentional data-dir descriptions, NOT broken refs.
5. SURVIVOR-vs-ABSORBED CONTRADICTIONS. Compare the same claim in both: save locations, user-preference rules, procedures. A user preference stated differently in the absorbed file vs the survivor body (found: "visible repo URLs" in SKILL.md vs "name-only hyperlinks, rejected twice" in the absorbed workflow) is a real conflict — report which side carries the explicit user quote.
6. REDUNDANCY. Absorbed SKILL.md bodies often duplicate the survivor's own sections (same WHY-pattern examples, same gotchas, same measured numbers in 3 files). Report with the duplicated section names; the fix is trim-one-side, not delete.
7. EMPTY absorbed/ DIRS. References to the Reference appendixabsorbed/<name>/` that git doesn't track (`git ls-tree -r HEAD | grep absorbed` returns nothing while dirs exist on disk) = content never shipped — git drops empty dirs silently. Verify the dir contents directly, never trust the pointer.
8. SCRUB-CONSISTENCY inside absorbed files. Placeholder convention must be uniform per file: `<user>` in paths but a leftover surname ("the user [surname]") or first name ("Jake's") = name-scrub ran before path-scrub or missed a spot. Report with the exact line; check whether the residue pre-dates the merge (compare parent blob) so the report says introduced-vs-pre-existing.

## Post-cull integrity audit (after culls, trims, and history wipes)

> Data moved to Reference: post-cull-integrity-audit (2026-09-16 context diet). Load on demand: skill_view(name='skills-repo-audit', file_path='Reference: post-cull-integrity-audit').

## Script↔skill consistency audit

Use when every script in a repo must be accounted for by its parent SKILL.md, and every documented invocation must match the script's real interface. Complement to the broken-reference scan (which checks that paths EXIST); this checks that mentions are in the RIGHT skill, name the RIGHT file, and DESCRIBE the right behavior. Read-only. Real session (Aug 2026): 26 skills / 50 files / 19 scripts / single commit c944e41; worked detail in `Reference: script-skill-consistency-2026-08`.

Six checks, each reported PASS/FAIL with file:line evidence, then a ranked FIXES list:

1. ORPHAN / WRONG-NAME. Every script basename must appear in its parent SKILL.md. Build the list from the tree (`find . -path ./.git -prune -o -type f \( -name '*.py' -o -name '*.ps1' -o -name '*.sh' -o -name '*.kql' \) -print`), then grep each basename across ALL .md. `~/`-prefixed and `C:\Users\<user>\`-style mentions are the documented live-env convention — a `~/x.ps1` mention still counts as the parent mention.
2. scripts/X EXISTENCE. Every `scripts/…` token in .md must resolve; grep case-insensitively and whitelist known basenames — anything left is a miss (should be zero). NOTE the bare-name class: files referenced WITHOUT the `scripts/` prefix (`provenance-full.kql` in prose) escape this check — see ghost scripts in check 4.
3. INVOCATION FIDELITY. Diff every described invocation (flags, args, expected outputs, exit codes) against the script's real interface. Extraction: `grep -n -A30 'argparse'` for .py — but some scripts parse `sys.argv` manually with no argparse, so also read the module docstring usage block; `grep -n -A15 'param('` for .ps1 (param blocks can be formatted so grep misses — read the file if unsure); usage comment header for .sh. Real mismatches found: skill prescribes `-InputCsv/-PreviousCsv` but the script defines no `-PreviousCsv` (CmdletBinding rejects unknown params at runtime); skill says "6-row fixture generator" but the script writes 7 rows; skill promises a bucket/flag output the committed script cannot produce.
4. FOLDED REFERENCE SECTIONS vs SCRIPTS. Folded `## Reference: x.md` sections often specify a pipeline (KQL→CSV→PS1) in detail: column contracts, expected outputs, version history. THE BIG TRAP: docs evolve through design generations (weighted composite → two-score → no-score) while the committed script stays frozen at an early generation. Determine which documented generation the committed file actually matches (match params/weights/thresholds in the CODE, not the newest prose). Verify "drift fixed" claims against the ACTUAL files — a reference can claim "PS1 accepts both column names (drift fixed)" while the committed PS1 still checks only the raw name, silently killing every signal. Check numeric consistency INSIDE the reference (same doc says 47 columns and "41 fields"; rf=9 vs rf=10). GHOST SCRIPTS: files named in prose/artifact lists (provenance-full.kql, provenance-governance.kql) that exist nowhere in the repo — either commit them or explicitly mark them live-env-only; repo conventions (AGENTS.md) require every mentioned script to exist.
5. CROSS-SKILL REFERENCES. A script referenced by a DIFFERENT skill than its parent must be referenced by skill name, never by bare basename. Grep every script basename across all skills; flag hits in non-parent skills that don't name the owning skill. The compliant pattern exists in the same repo ("the deep playbook lives in the mde-advanced-hunting skill") — cite it when reporting.
6. SCRIPTS-DIR HYGIENE. Scripts dirs contain code only: no stray .md, no .pyc, no __pycache__. Distinguish git state from working tree: `git ls-files | grep -E 'pyc|__pycache__'` (0 = commit clean — .gitignore usually covers them) vs `find . -name '*.pyc'` (working tree dirty). Report both; severity depends on whether the deliverable is the commit or the tree.

### Execution layer (verify OUTPUT claims by running the real pipeline)

Static diffing settles interface claims; it cannot settle output claims (bucket totals, rf counts, flag sets, decision carry-over). When the SKILL.md states expected outputs AND a generator + runner exist, EXECUTE them end-to-end and compare real output row-by-row (real session Aug 2026: confirmed 7 rows / 47 cols / CCC333 rf=10 Loud / totals 2+2+1+1+1, and PROVED a row-level claim stale that static reading could only argue about — "renamed LOLBin -> RedFlagged" is actually Loud because RENAMED_LOLBIN sets $loud=$true). Method (WSL → Windows PowerShell):
- Patch the committed generator's placeholder OUT before running: `sed 's|/mnt/c/Users/<user>/Downloads|/mnt/c/Users/<user>/AppData/Local/Temp/<auditdir>|'` — unpatched it creates a literal `<user>` directory. Substitute the real user (C:\Users\<user> ↔ /mnt/c/Users/[user]).
- Invoke the script under test with full Windows paths: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\...\x.ps1' -InputCsv ... -PreviousCsv ...` (Windows PowerShell does not understand /mnt/... paths).
- Read results from the OUTPUT CSV, never the console table: `csv.DictReader(open(out, encoding='utf-8-sig'))` — PS 5.1 Export-Csv writes UTF-8 BOM and the console table truncates top rows.
- Cross-check row-level expectations against the GENERATOR'S OWN docstring: SKILL.md and generator docstring are two independent records of one fixture; their disagreement marks the stale one (this round: SKILL.md said RedFlagged, generator said Loud, execution said Loud).
- CLEANUP: keep runs in a disposable temp dir; do NOT bundle `rm -rf` with read-only verification commands — destructive cleanup can be denied mid-run. If denied, stop destructive actions and report the leftover path in the summary (AppData/Local/Temp artifacts are harmless).

### Producer→consumer column cross-check (silent-drift catcher)

Extract both sides programmatically instead of eyeballing: ps1 reads = `re.findall(r'\$row\.([A-Za-z_]\w*)', ps1)` ∪ `columns -contains "X"` checks; producer emits = assignment targets in summarize/project/extend (`X = take_any/make_set/dcount/...`) + `invoke FileProfile(...)` appended columns (GlobalPrevalence/ProfileAvailability/IsCertificateValid/ThreatName). Report consumer reads emitted by NO producer — graceful-degrade columns are expected ($has* guards make absence safe); the FAIL class is the OLD-NAME-ONLY producer (a governance kql still emitting MaxDistinctDays/TotalExecutions while the ps1 reads DistinctDays/ExecutionCount → silently backfilled to 1 / blanked, exactly the drift the docs warn about). Verify "renamed in KQL v2" style claims PER FILE: one file renamed ≠ all files renamed.

### Phrase-grep negative checks (de-confession / holdings / PII-removal passes)

Verify "zero occurrences" claims with exact phrases, then classify every substring hit into benign classes BEFORE reporting: product facts ("Microsoft has not shipped…"), product renames ("(formerly Trusted Signing)"), English substrings ("performers" contains "former"), repo-governance rules (AGENTS.md "restructure"/"culled skill"), feature headings ("Restructure Document Content"). Report exact-phrase zeros AND the benign hits explicitly — never silently filter, never flag. For mechanical sub-checks ("no 3+ ticker lists"): apply the letter of the check AND separately state the substance (found lists were screen-candidate names; "Holdings:" literal and account amounts were zero) — the owner decides which bar counts. Detail from the Aug 2026 round: `Reference: script-claim-coherence-2026-08`.

Root-cause framing: multiple FAILs usually trace to ONE stale script vs evolved docs — name that root cause first in the report. Fixes name BOTH alternatives when intent is ambiguous ("commit the current PS1 OR downgrade the reference sections to the committed design").

## Report (output contract — keep this shape):
   - One-line verdict for EVERY skill (`name: verdict`); verdict vocabulary: STRONG / GOOD / fine vs THIN / DUPLICATE / BROKEN-refs / PII-residue
   - Ranked merge-candidate list with justification and QUOTED overlapping scope lines
   - Issues list with file paths, grouped by class (broken refs / PII / hardcoded paths / stale / inconsistent)
   - Plain text, NO markdown tables

## Pitfalls

- `find -type d -name SKILL.md` returns nothing — SKILL.md is a file; use `-exec dirname {} \;`.
- Naive description extraction misses folded frontmatter (`>` / `|`).
- Unverified broken-ref flags: ~90% are false positives (example code, illustrative names, out-of-repo pipelines). Always grep the context line before reporting.
- related_skills nested under `metadata: hermes:` is invisible to `yaml.get("related_skills")` — scan frontmatter lines at any indent.
- Cross-skill path refs (`career/resume-engineering/the Reference appendixfoo.md`) resolve only from the repo root; naive per-skill resolution false-flags them as missing.
- Deleted-name provenance: "Absorbed/merged into" lives in the section header; flagging only the current line turns valid absorbed-skill lists into false FAILs.
- README file counts: compare to on-disk, not git-tracked — uncommitted changes make the two differ.
- Reporting a cross-skill reference as "missing" when it exists elsewhere misleads the fix — it is a relocation.
- Doubled-prefix path typo (`finance/financial-data-apis/finance/financial-data-apis/the Reference appendixx.md`) reports as missing but is a prefix-dedup fix, never a file-creation fix.
- `grep $'\x00'` cannot work in bash (argv drops the NUL → empty pattern matches every line); byte-scan with python to verify binary-ness.
- Absorbed notes naming live-library-merged skills that never shipped in the repo are coherent if past-tense — "former" is repo-relative, don't flag live-library survivors for it.
- Audit output stays read-only: deliver findings; let the owner merge/trim.

## Related

- `skill-audit` — per-skill semantic correctness (claims vs outcomes vs external evidence). This skill is the repo-level complement: structure, references, PII, overlap. When this audit surfaces concrete fixes in specific skills, follow up with skill-audit-style patches.
- `skill-library-maintenance` — the LIVE library: cost model (index tokens per turn, body x loads) and curator lifecycle (adopt/archive/restore/pin). This skill audits content; that one decides what stays offered.

## Reference: post-cull-integrity-audit

# post cull integrity audit — extracted 2026-09-16 from meta/skills-repo-audit/SKILL.md (context diet). Loaded on demand.

## Post-cull integrity audit (after culls, trims, and history wipes)

Use when the repo went through a CULL (skills removed outright, reference files trimmed, README rewritten) — distinct from merge/absorption. Real session (Aug 2026): 64→39 skills, 406→278 files, 12→10 categories, history wiped to a single commit (37f83a8) for PII. Read-only. Run `python3 scripts/post_cull_audit.py <repo> --culled <names> --trimmed <files> --allowed <bundled> --expect-skills N --expect-files N --expect-single-commit` (lists: comma-separated or `@file`, one per line).

FIRST verify the wipe actually happened: `git log --oneline | wc -l`. With intact history (later session: 8 commits, 39→26 skills), provenance comes from git, never from notes or assumptions: `git show --stat <cull-commit>` lists every deleted file (the definitive trimmed-file list, e.g. plan-mode.md died WITH writing-plans); `comm -23 <(git ls-tree -r --name-only <initial-commit> | grep SKILL.md | sort) <(find . -name SKILL.md -not -path './.git/*' | sort)` gives the culled-skill set. PITFALL: filter by DIRNAME, not filename — reference files named `*-SKILL.md` (deck-guizang-editorial-SKILL.md) end in SKILL.md and inflate the initial count (43 vs 39). Expect two cull waves + a refs-cull commit + a final author-strip commit; each has its own D-list.

Seven checks, then hand-review every flag with its context line:
1. PATH-REF RESOLUTION — every references/|scripts/|templates/ mention in .md/.py/.sh/.ps1 resolves from the SKILL.md root (`../`-prefixed from the file's own dir). Ignore `${VAR}`, `~/`, absolute, URL, and live-env paths — a preceding-char lookbehind class `[A-Za-z0-9_./\\:~$-]` kills them at the regex. Strip trailing dots from captures (sentence-final `foo.md.`).
2. CULLED-NAME SCAN — whole-word boundary `(?<![a-z0-9-])name(?![a-z0-9-])` (IGNORECASE) over all text files. The boundary rule is what stops trimmed `multi-period-testing.md` from false-flagging the survivor `multi-period-testing-framework.md`. Classify each hit: provenance keywords (`former|absorbed|merged|culled|removed|previously|... " was "`) → OK; loadable indicators (`related_skills`, `skill_view(`, "see X skill", backticked name, `../X/` path) → FAIL; else REVIEW. Skip URL tokens (expand to maximal token; contains `://` or bare domain).
3. TRIMMED-FILE SCAN — exact filename AND boundary-stem search for each trimmed file.
4. FRONTMATTER — name==folder, description present, related_skills ⊆ repo names ∪ allowed-bundled. Compare against the SET of skill NAMES, never the list of dir paths (bug hit this session: 5 false failures).
5. HYGIENE — empty dirs; `.usage.json`, `.curator*`, `.DS_Store`, `__pycache__`, `*.pyc`, `node_modules`.
6. README CLAIMS — "N skills"/"N files" strings + every `### category (N)` header's count and skill list vs the tree; category totals must sum to the skill count.
7. GIT STATE — exactly 1 commit (history wiped) + clean tree = the post-wipe publish state.

False-positive classes that WILL appear (review, then exempt WITH evidence — print as `EXEMPT (reviewed) file:line: ref`, never silently filter):
- External marketplace skills sharing a culled name: skills.sh's grill-me/grilling (Matt Pocock) — 7 hits in tool-landscape notes; the culled local copy shared the name. Exempt lines that name the external source (matt pocock / skills.sh / grill-me / hub).
- Live-env install paths: `~/.hermes/hermes-agent/tools/tool_search.py` — a culled name inside an install path is not a skill reference (4 hits). Generically detectable: expand the token around the match, starts with `~/`.
- Prose noun phrases: "automated scripts/backends = terms violation" (API-ToS prose) and `scripts/references` (spec intros) — keep in PHRASE_TOKENS.
- Provenance phrases: "the gh-env.sh helper lived in the former github-auth skill" → OK.
- A history wipe kills the git-based provenance methods of the merge-audit section: with 1 commit there is no `git show <merge> --name-status` — verify absorbed-content provenance from content markers ("Absorbed from the X skill" headers) instead.

### Content-coherence layer (hand checks on absorbed files — after the mechanical scans)

The seven checks verify STRUCTURE; this layer verifies what absorbed content says and where it now lives. Real session: 39-skill repo, 13 absorbed files, 7 redundancy instances, 2 thin-survivor classes.

1. ABSORBED FILES READ COHERENTLY in their new home: (a) every absorbed file carries the "Absorbed from the X skill..." header — coverage can be inconsistent WITHIN one absorption batch (3 of 4 files lacked it); flag the batch, not the file; (b) each absorbed source name should be a CULLED skill — a source that is also a survivor = merged-then-kept; verify intent; (c) internal `references/...` links inside absorbed files resolve against the NEW skill dir (they usually travel together); (d) each absorbed file is listed in the host SKILL.md's References section — an absorbed file absent from References AND fully duplicated by the host body is content-orphaned (side-income-doctrine.md case): no unique value, delete candidate.
2. REDUNDANCY MATRIX among survivors (four classes, all seen in one audit): (a) absorbed file ≈ host SKILL.md section, verbatim examples; (b) absorbed file ≈ PRE-EXISTING reference in the same dir (one QA workflow shipped in 3 copies: SKILL.md section + layout-pitfalls ref + absorbed visual-QA ref); (c) absorbed file ≈ another SURVIVOR's whole body (domain reference vs the deep skill it summarizes — application-control-domain.md vs enterprise-application-control); (d) byte-identical reference in two survivors — `sha256sum` both copies, then check which copy each SKILL.md actually cites; the un-cited copy is dead weight (tool-landscape.md in agent-memory-evaluation while its own SKILL.md points at agent-tool-evaluation's copy). Fix is always trim-one-side, never delete-both.
3. CULLED-CLUSTER CONTENT IN SURVIVORS: after a cluster cull, check survivors for files/sections carrying the culled cluster's content (resume-playbook.md inside python-docx after resume-engineering/resume-editing were culled). The file may be ref-clean (the referenced template map was inlined) yet still contradict the cull's rationale: sections with zero transferable signal (personal "verified work facts", reflection voice rules) are the cull's rejects living on by accident. Recommend stripping the personal sections, keeping the transferable ones (docx template-surgery patterns).
4. THIN-SURVIVOR CLASSES post-cull, each needs a keep / annotate / remove call against the cull's stated rationale: lone category survivors (real methodology — keep, annotate that the cluster was culled); personal side-gig doctrine surviving under a research category (strongest remove candidate — matches "personal admin" cull rationale); student-assignment personal content that is nonetheless self-contained (borderline keep). State the call per-skill in the report.
5. Operational: read_file misdetects files with very long single lines as binary — `file(1)` confirms UTF-8; read via terminal/python instead. Same false-alarm class: verifying binary-ness with `grep $'\x00'` in bash matches EVERY line (argv cannot hold a NUL, so the pattern arrives empty — a clean file "showed" 133 null bytes). Use a python byte-scan for control chars; UTF-8 decode settles it.
6. ABSORBED-SOURCE CLASS: sources named in absorbed notes can be repo-culled skills, live-library skills merged but NEVER in the repo (mcp-fleet-optimization, sec-edgar-xbrl-fundamentals, enterprise-it-strategy-documents, search-api-selection), or pre-repo merges (portfolio-api-workflow + 10 portfolio skills). All are coherent IF the note is past-tense ("during repo restructure") and names NO repo-culled skill. Cross the named list against three things: the git-derived culled set, the initial-commit tree, and the live library (`ls ~/.hermes/skills/...` — properly-merged names are gone there too). "Former" phrasing is repo-relative: do NOT flag it just because the skill still exists in the live library.
7. CROSS-NOTE VERIFICATION: a "lives canonically in <skill>" note (e.g. Debate Pattern → subagent-debate, WHY pattern → presentation-content-patterns) requires BOTH copies to still exist and the canonical target to actually contain the named pattern; pointer-on-one-side-only asymmetry is fine. Also flag same-skill internal duplication (two debate-pattern sections in one SKILL.md) and orphaned one-liners under section headers — merge truncation leaves headers with a stray body line ("## Full-Deck QA" containing only a recommendation that belongs to a later example).
8. NUMBERED-CONSISTENCY for duplicated sections: the same measured numbers across a SKILL.md section + absorbed ref + record ref must agree exactly (67→42 tools, 6,712B→4,264B, 99.6→64.7KB, firecrawl 26→6, brave 8→3 all matched across mcp-server-diagnostics SKILL.md Trimming + context-cost-tuning.md + tool-trimming.md). Agreement = redundancy to report; disagreement = drift to fix. Three copies of one workflow is the signal to name one canonical.
9. DOUBLED-PREFIX PATH TYPOS: automated pointer-fix passes can produce `<category>/<skill>/<category>/<skill>/references/<file>.md` — the resolver reports it missing, but the fix is prefix dedup, NEVER file creation. Detect: `grep -rnE "([a-z0-9-]+/[a-z0-9-]+/)\1" --include="*.md" .`
10. UNRESOLVED SCRUB PLACEHOLDERS: `grep -rnE "\[[a-z][a-z ]*\]"` — classify acceptable redactions ([employer], [Name], template vars like [X]GB) vs substantive-phrase residue ([holdings list] ×9 across 6 finance files, including one garbled pointer "Full analysis: [holdings list] analysis notes in this skill's references"). Report count per token; garbled pointers are fixes, readable-but-artifact is a polish class.

### Snapshot-race reconciliation (audits vs concurrent culls)

Audits dispatched before a cull/trim lands report findings about files that no longer exist. Before acting on ANY finding, check the target file still exists in the tree — a whole class of findings can be moot by report time (happened twice in one project: the Net-Liq dollar-value finding and the resume-playbook recommendation were both culled before their reports landed). Convergence signal for the loop: a round where every finding is either moot (file gone) or fixed on the spot = done; say so explicitly in the summary instead of re-running. Also re-run the mechanical reference check AFTER applying fixes — each fix round creates its own dangling mentions (two stragglers found this way, including an absorbed reference file pointing at a file removed in the same round).

## Reference: script-claim-coherence-2026-08

# Script-claim coherence audit — agent-skills round 2 (Aug 2026)

Second audit round of the portable-app-discovery pipeline claims (round 1:
script-skill-consistency-2026-08.md). Scope: EAC SKILL.md Scoring Model (~L1167)
+ Reference Implementation Artifact (~L1348-1355), MDE SKILL.md fixture
expectations (L130-199) + column-contract table (L144-148), the three committed
kql files, gen_portable_test_csv.py, search_ab.py, de-confession phrase check,
finance holdings check, 47 folded Reference sections. Repo READ-ONLY.

## Verdicts (what the checks found)

- PASS: all enumerated Scoring Model / Reference Implementation claims matched
  ps1 v3.17: no-score header (ps1 L3-6, L36), unweighted RedFlagCount (all
  `$red++` sites are weight-1), bucket precedence Loud > RedFlagged (rf>=2 AND
  not internal) > Internal > New > Installer > Stable (ps1 L474-482), Decision
  carry-over (L62-77, L470-472), Growth KPI (L456-468), params -InputCsv/
  -OutputCsv/-PreviousCsv (L46-48), zero embedded KQL (0 hits for table/
  operator/API tokens), API path lives in MDE run-ah.ps1 (MDE SKILL.md:117).
  Loud list (ps1 L26-28) matches all 14 $loud=$true sites.
- PASS (execution-verified): fixture claims 7 rows / 47 cols / CCC333 rf=10
  T2 B7 C1 Loud / bucket totals 2+2+1+1+1 / Decision=Allow + Quarantine carried.
- FAIL: MDE SKILL.md:189 "renamed LOLBin -> RedFlagged" — actual bucket LOUD
  (RENAMED_LOLBIN sets $loud=$true, ps1 L329). Contradicts the L192 totals
  (2 Loud needs EEE555) and the generator's own docstring (L20-21 "EEE555 rf=2
  Loud"). Row-level claims can be stale even when the totals are right — check
  every row, not just the sums.
- FAIL: provenance-governance.kql L53-54 still emits MaxDistinctDays/
  TotalExecutions; ps1 reads only DistinctDays/ExecutionCount (backfill
  L123-127, output L498-499) → governance CSV silently backfills DistinctDays=1
  and blanks ExecutionCount. "Renamed in KQL v2" (MDE L149-150) holds for
  provenance.kql + provenance-full.kql only. Verify per FILE, not repo-wide.
- WARN: EAC SKILL.md:1181-1184 "Three KQL versions" (A+/A/B) doesn't map to the
  committed trio: Version A claims a cert join provenance.kql lacks; Version B
  "Top 1000 + FileProfile() inline" matches no committed file.
- WARN: ps1 header L23-31 (v3.15/v3.17 changelog) claims DriverLoads/
  DefenderTamperHits come from "KQL ActorBehaviorEvents" — no committed kql
  computes them; $has* guards keep runs safe, but the claim is unbacked.
- WARN: finance bodies contain 3+ ticker lists (portfolio-research-methodology
  :121 — 16-ticker list; screen-validation :15/:24-25/:29/:166/:199/:208) — all
  screen-candidate names, zero holdings/positions/account amounts; "Holdings:"
  literal = 0; one held name (WMB, portfolio-research-methodology:31).
- PASS: de-confession phrases — 10 exact phrases, zero occurrences. Benign
  substring hits classified: "performers" contains "former", "(formerly Trusted
  Signing)" product rename, "Microsoft has not shipped" product fact,
  AGENTS.md "restructure"/"culled skill" governance rules, python-docx
  "Restructure Document Content" feature heading. "PII" only in AGENTS.md's own
  hygiene battery.
- PASS: 47 Reference sections; 164 path-like backticked tokens checked; the only
  unresolved token was an extractor false positive — `mcp_context.py
  <name>` carries a usage suffix; strip trailing usage tokens before resolving.

## Reusable commands (full run in the audit session transcript)

- Fixture run WSL → Windows PowerShell:
  sed 's|/mnt/c/Users/<user>/Downloads|/mnt/c/Users/<user>/AppData/Local/Temp/<auditdir>|' gen_portable_test_csv.py > <auditdir>/gen.py
  python3 <auditdir>/gen.py
  cp portable-app-discovery.ps1 <auditdir>/ && powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\<user>\AppData\Local\Temp\<auditdir>\portable-app-discovery.ps1' -InputCsv ... -OutputCsv ... -PreviousCsv ...
  Read back: csv.DictReader(open(out, encoding='utf-8-sig'))  # PS 5.1 writes UTF-8 BOM
- Column cross-check:
  ps1_reads = set(re.findall(r'\$row\.([A-Za-z_]\w*)', ps1)) | set(re.findall(r'columns -contains "(\w+)"', ps1))
  kql emits: assignment targets in summarize/project/extend + take_any/make_set/
  dcount/countif/iff + `invoke FileProfile(...)` appended columns
  (GlobalPrevalence/ProfileAvailability/IsCertificateValid/ThreatName).
  FAIL class = old-name-only producers (MaxDistinctDays/TotalExecutions).
- Reference-section existence: `^## Reference:\s*(.+?)\s*$` headers; backticked
  `*.md|py|ps1|kql` tokens resolve file-dir → skill-dir → repo-root; strip
  trailing usage tokens (`<name>`) before resolving.

## Pitfalls re-confirmed / new this round

- Console table output truncates top rows — verify from the CSV, not the terminal.
- Generator committed with literal `<user>` placeholder in OUT — patch before running.
- `rm -rf` cleanup bundled with verification got DENIED mid-run; keep destructive
  cleanup separate from read-only verification and report leftover paths in the
  summary (test artifacts in AppData/Local/Temp are harmless).
- The pipeline's own smoke test (generator + ps1) is the cheapest oracle for
  fixture-claim audits: run it, don't re-derive expected outputs by hand.

## Reference: script-skill-consistency-2026-08

# Script↔skill consistency audit — worked session (Aug 2026)

> SUPERSEDED IN PART by `script-claim-coherence-2026-08.md` (round 2, same repo):
> the kql files named "ghost scripts" below are now committed, the committed PS1 is
> now the v3.17 no-score design, and the column-contract drift is fixed except
> provenance-governance.kql (still emits MaxDistinctDays/TotalExecutions). Treat
> this file as the round-1 procedure + evidence pattern; round 2 has current state.

Repo audited: /home/<user>/agent-skills (Dryader/agent-skills portfolio), commit c944e41,
26 skills / 50 files / 19 scripts. READ-ONLY. Result: checks 1-2 PASS, 3-6 FAIL,
all traceable to ONE root cause: the portable-app-discovery pipeline's committed
scripts were frozen at a pre-v3.3 design while both skills' bodies and the test
fixture describe the evolved no-score design.

## The six checks (procedure + evidence pattern)

1. ORPHAN / WRONG-NAME — PASS. All 19 script basenames appear in their parent
   SKILL.md. Live-env mentions (`~/portable-app-discovery.ps1` in
   enterprise-application-control/SKILL.md:1350) count as parent mentions per the
   repo's documented live-env convention.
2. scripts/X EXISTENCE — PASS (zero misses). 28 `scripts/…` mentions, all resolve.
   The bare-name class (`provenance-full.kql`, no `scripts/` prefix) is NOT caught
   here — handle under check 4.
3. INVOCATION FIDELITY — FAIL. Evidence:
   - mde-advanced-hunting/SKILL.md:195 + gen_portable_test_csv.py:10-14 prescribe
     `-InputCsv/-PreviousCsv`; portable-app-discovery.ps1:8-19 defines NO
     `-PreviousCsv` (CmdletBinding → the documented recipe errors at runtime).
   - mde-advanced-hunting/SKILL.md:130 "6-row fixture generator" vs
     gen_portable_test_csv.py:6,153 — 7 rows actually written.
   - gen_portable_test_csv.py:16-22 expects rf/bucket/flag output (v3.15) the
     committed PS1 (portable-app-discovery.ps1:120-128, Tier/CompositeScore only)
     cannot produce.
   - enterprise-application-control/SKILL.md:1350 "two-score pipeline" vs actual
     weighted composite (weights + Tier1/Tier2 thresholds at ps1:13-18).
   Verified-clean pairs (the majority): probe_mcp_endpoint.py usage line == SKILL.md
   claim; mcp_context.py 0/1-arg semantics; extract_pymupdf/marker flag sets;
   Scan-LOLDrivers.ps1 -DataSource Local/-Path + "exit 1 on hash hits" (script
   line 360); repo_freshness.sh positional args; tpm-diagnostics/win-inventory
   run instructions; privacy-status-check "Name = Value" output format; mcp_stdio_probe
   --command/--args/--env/--timeout; check_repo_health owner/repo args;
   session_*_audit [state.db] defaults.
4. FOLDED REFERENCE SECTIONS vs SCRIPTS — FAIL. The design-generation trap:
   - portable-app-discovery.md (mde-advanced-hunting:133-219) describes v3.3
     NO-SCORE (RedFlagCount/buckets/flags). The committed PS1 implements the
     ORIGINAL weighted composite — which eac:1414 explicitly says was REJECTED.
   - "Drift fixed" claims FALSE for committed files: reference says "PS1 v3.18
     accepts both column names" (mde:146-148), but committed ps1:68-69 checks ONLY
     `FileOriginUrl`/`InitiatingProcessFileName_Create` while provenance.kql:48-57
     emits `ExampleOriginUrl`/`ExampleInitiator`/`TopFolderPath`/`MaxDistinctDays`/
     `TotalExecutions` → running the documented pipeline silently zeroes every
     provenance signal (and backfills DistinctDays=1, the exact failure mde:159
     warns about).
   - Internal numeric contradictions in one reference: "47 columns" (mde:184) vs
     "EXACTLY 41 fields" (mde:199); rf=9 (mde:187) vs rf=10 (generator docstring
     :19-20); bucket totals 4 RedFlagged (mde:192) vs 2 Loud+2 RedFlagged
     (generator :17-18).
   - GHOST SCRIPTS: `provenance-full.kql` + `provenance-governance.kql` named in
     artifact lists and the naming convention (eac:1355-1356,1439-1450; mde:137,207)
     but committed nowhere. Either commit or mark live-env-only — AGENTS.md:36
     requires every mentioned script to exist.
   - PASS side: loldrivers-scanning.md (wvs:78-130) matches Scan-LOLDrivers.ps1
     exactly (332 local / 660 live / AsUpIO positive control / extension list) —
     the pattern to emulate: measured claims that match script constants.
5. CROSS-SKILL REFERENCES — FAIL (minor). portable-app-discovery.ps1 (parent:
   enterprise-application-control) is invoked by bare basename in
   mde-advanced-hunting:137,195 without naming the owning skill. Compliant pattern
   exists in the same repo (eac:239 "the deep playbook lives in the mde-advanced-
   hunting skill"). No cross-skill `scripts/` PATH references anywhere.
6. SCRIPTS-DIR HYGIENE — FAIL (working tree only). 11 untracked *.pyc in 8
   scripts/__pycache__/ dirs; gitignored (`.gitignore`: `__pycache__/`, `*.pyc`);
   `git ls-files` = 0 tracked → the commit itself is clean. Distinguish the two
   before reporting severity. No stray .md in any scripts dir.

## Technique notes

- Argparse extraction misses manually-parsed scripts: extract_pymupdf.py and
  extract_marker.py have NO argparse — they parse `sys.argv` inline. The module
  docstring usage block is the authoritative interface for those; diff THAT
  against the SKILL.md claims (all flags matched).
- `grep -n -A15 'param('` can miss PS1 param blocks (formatting varies) — fall
  back to reading the file.
- Exit-code semantics: check the actual `exit N` lines (Scan-LOLDrivers.ps1:360
  `exit 1` only on HASH matches, not name-only matches) — the SKILL.md claim
  "exit 1 on hash hits" is precisely right.
- Fixture-vs-consumer cross-check: the repo's own test fixture (gen_portable_test_csv.py)
  and the PS1 it exercises disagree on interface AND expected output — a repo can
  be internally inconsistent with itself, not just with its docs.
- For the report: PASS/FAIL per check with file:line, then ranked FIXES with both
  alternatives when intent is ambiguous, and the single root cause named first.

## Fixes delivered in the report (ranked)

1. HIGH — reconcile portable-app-discovery.ps1 with documented v3.3+ no-score
   design (commit current PS1 OR downgrade reference sections).
2. HIGH — fix committed KQL↔PS1 column contract (alias/dual-accept the 5 drifted
   column pairs listed above).
3. MEDIUM — commit or mark live-env-only provenance-full.kql / provenance-governance.kql.
4. MEDIUM — mde-advanced-hunting doc fixes: 6→7 rows, 41→47 fields, rf=9→10,
   bucket totals.
5. LOW — cross-skill reference hygiene (name owning skill).
6. LOW — delete gitignored __pycache__ before shipping the tree.
