#!/usr/bin/env python3
"""Cross-reference integrity audit for a skills repo. READ-ONLY.

Usage: python3 crossref_audit.py [repo_dir]   (default: /home/<user>/agent-skills)

Checks (each prints PASS/FAIL with file:line evidence):
 1. every references/|scripts/|templates/ path mention in every .md resolves
    against the file's dir, its skill dir, and the repo root
 2. every related_skills frontmatter entry resolves (in-repo skill or allowed
    bundled skill) -- scans at ANY indentation (also nested under metadata:)
 3. every SKILL.md frontmatter name == folder name, description present
 4. deleted skill names never used as loadable references (historical
    provenance wording like "absorbed from X" is OK)
 5. no duplicate relative paths across skills (e.g. two skills each with
    references/<name>.md)
 6. README category lists/counts and the "N skills, M files" claim match the
    tree (compare on-disk count; git-tracked count differs when the working
    tree has uncommitted changes)

False-positive guards built in (all verified against a real 64-skill repo):
  - URLs: check "http" in the 60 chars BEFORE the match, not "://" -- the
    "//" can be captured inside the token, so "://" straddles the boundary
  - token starting with / or \\ (absolute), ~-prefixed home paths (also when
    pre ends with bare "~"), ${ENV_VAR} expansion, Windows drive (C:\) paths,
    hidden-dir first segments (.hermes/...)
  - noun phrases that are not paths: "scripts/backends", "scripts/references"
  - SKILL_DIR/ placeholder prefix resolves to the skill's own dir
  - cross-skill references need the REPO ROOT as a resolution base
    ("career/resume-engineering/references/<name>.md"); a naive regex only
    captures "references/<name>.md" and false-flags these

Tuning: edit BUNDLED_NOT_IN_REPO / DELETED / PHRASE_TOKENS below for the repo
being audited (bundled = skills legitimately referenced but NOT shipped in
this repo; deleted = names that must never appear as loadable references).
"""
import re, sys, glob, subprocess
from pathlib import Path
from collections import defaultdict

REPO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/<user>/agent-skills")

# --- task/repo-specific allowlists (edit per audit) --------------------------
# Skills legitimately referenced from this repo but not shipped in it
# (resolved by name in the live environment). Keep updated per repo.
BUNDLED_NOT_IN_REPO = {
    "powerpoint","docx","arxiv","humanizer","design-md","popular-web-designs","pdf",
    "xlsx","obsidian","notion","google-workspace","himalaya","openhue","songsee",
    "gif-search","computer-use","claude-code","codex","opencode","open-design-related",
    "manim-video","p5js","comfyui","touchdesigner-mcp","baoyu-infographic","ascii-art",
    "excalidraw","sketch","pretext","architecture-diagram","llama-cpp","serving-llms-vllm",
    "huggingface-hub","evaluating-llms-harness","weights-and-biases","blogwatcher",
    "polymarket","airtable","maps","nano-pdf",
}
# Skill names deleted from the repo; usage that is NOT clearly historical
# provenance ("absorbed from X", "merged into this umbrella", "supersedes")
# is flagged. Ambiguous names like "plan" only match in skill-reference
# contexts (skill_view("plan"), `plan` backticks, related_skills entries).
DELETED = [
    "resume-editing","plan","search-api-selection","sec-edgar-xbrl-fundamentals",
    "mcp-fleet-optimization","hermes-release-update","career-promotion-coaching",
    "enterprise-it-strategy-documents","paid-research-participation","grill-me",
    "portfolio-stock-selection","portfolio-swap-testing","portfolio-selection-stability",
    "portfolio-differentiation-tests","portfolio-optimization","portfolio-risk-testing",
    "portfolio-construction","ml-paper-writing",
]
PROVENANCE_WORDS = ["absorbed","merged into","umbrella","restructure","former",
                    "supersedes","originally compiled","historical","was integrated",
                    "consolidation","consolidated","integrated into"]
# verified noun phrases that look like paths but are not (check each against
# the corpus before adding)
PHRASE_TOKENS = {"scripts/backends", "scripts/references"}

def walk_md():
    for p in sorted(REPO.rglob("*.md")):
        if ".git" in p.parts: continue
        yield p

def find_skill_dir(p: Path):
    for anc in [p.parent, *p.parents]:
        if anc == REPO: break
        if (anc / "SKILL.md").exists() and anc.parent != REPO:
            return anc
    return None

md_files = list(walk_md())
skill_dirs = [p.parent for p in REPO.glob("*/*/SKILL.md")]
skills = {d.name: d for d in skill_dirs}
REPO_SKILL_NAMES = set(skills)
ALLOWED = REPO_SKILL_NAMES | BUNDLED_NOT_IN_REPO

results = defaultdict(list)
def add(check, status, msg):
    results[check].append((status, msg))

# ================= CHECK 1: references/scripts/templates path targets =========
# Multi-segment prefix capture ((?:[A-Za-z0-9_.-]+[/\\])*) is REQUIRED for
# cross-skill refs like career/resume-engineering/references/<name>.md; a
# single-segment prefix only captures "references/<name>.md" -> false FAIL.
TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_.\-])((?:\.{0,2}[\\/])*(?:[A-Za-z0-9_.\-]+[\\/])*(?:references|scripts|templates)[\\/][^\s`\"'<>()\[\]{},;]+)"
)
def clean_token(t):
    t = t.strip()
    t = re.sub(r"[\"']\s*$", "", t)
    t = re.sub(r"[.,;:!?)]+$", "", t)
    t = re.sub(r"[#?].*$", "", t)
    return t

def resolve(token, base_dirs, sdir=None):
    c = token.replace("\\", "/")
    if c.startswith("SKILL_DIR/") and sdir is not None:
        rp = sdir / c[len("SKILL_DIR/"):]
        return rp if rp.exists() else None
    for base in base_dirs:
        rp = base / c
        if "*" in c or "?" in c:
            if glob.glob(str(rp)): return rp
        elif rp.exists():
            return rp
    return None

def skip_context(pre, tok):
    """Return reason string if token is not a skill-relative path, else None."""
    if "http" in pre: return "part of URL"          # "://" can straddle the match
    if tok.startswith(("/", "\\")): return "absolute path"
    if re.search(r"~[\\/]?[^\s]*$", pre): return "home-dir path (~)"
    if re.search(r"\$\{|\$[A-Za-z_]", pre): return "env-var path"
    if re.search(r"[A-Za-z]:[\\/]\s*$", pre): return "windows drive path"
    if re.search(r"(?:^|[ \t({\[])[\\/][^\s]*$", pre): return "absolute /path"
    seg = tok.replace("\\", "/").split("/")[0]
    if seg.startswith(".") and seg not in (".", ".."): return "hidden-dir path"
    return None

check1 = []
for p in md_files:
    sdir = find_skill_dir(p)
    base_dirs = [p.parent]
    if sdir: base_dirs.append(sdir)
    base_dirs.append(REPO)
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:
        add(1, "WARN", f"{p}: unreadable ({e})"); continue
    seen = set()
    for i, line in enumerate(lines, 1):
        for m in TOKEN_RE.finditer(line):
            raw = m.group(1)
            if raw.endswith("/") or raw.endswith("\\"): continue
            tok = clean_token(raw)
            if not tok: continue
            key = (i, tok)
            if key in seen: continue
            seen.add(key)
            pre = line[max(0, m.start()-60):m.start()]
            reason = skip_context(pre, tok)
            if reason:
                if tok in PHRASE_TOKENS:
                    add(1, "INFO", f"{p}:{i}: {tok!r} skipped as noun phrase (not a path)")
                continue
            if tok in PHRASE_TOKENS:
                add(1, "INFO", f"{p}:{i}: {tok!r} skipped as noun phrase (not a path)")
                continue
            if resolve(tok, base_dirs, sdir) is None:
                check1.append((p, i, tok, pre[-30:]))

if check1:
    for p, i, tok, pre in check1:
        add(1, "FAIL", f"{p}:{i}: target missing for {tok!r}  (ctx: {pre!r})")
else:
    add(1, "PASS", "all references/scripts/templates path targets resolve")

# ================= CHECK 2: related_skills frontmatter (any indentation) ======
# yaml.safe_load().get("related_skills") MISSES entries nested under
# "metadata: hermes:" -- scan the raw frontmatter lines at any indent instead.
def get_related_skills(p):
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None, {}
    if not re.match(r"^\uFEFF?---\s*$", text, re.M): return None, {}
    parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.M)
    if len(parts) < 3: return None, {}
    fm_text = parts[1]
    entries, collecting = [], False
    lineno = {}
    for n, line in enumerate(fm_text.splitlines(), 1):
        m = re.match(r"^\s*related_skills\s*:\s*(.*)$", line)
        if m:
            val = m.group(1).strip()
            if val:
                for x in [e.strip().strip("\"'") for e in val.strip("[]").split(",") if e.strip()]:
                    entries.append(x); lineno.setdefault(x, n)
            collecting = True
            continue
        if collecting:
            bm = re.match(r"^\s*-\s+(.+?)\s*$", line)
            if bm:
                e = bm.group(1).strip().strip("\"'")
                entries.append(e); lineno.setdefault(e, n)
            elif re.match(r"^\s*[A-Za-z_][\w]*\s*:", line) or not line.strip():
                collecting = False
    return (None if entries == [] and not re.search(r"related_skills", fm_text) else entries), lineno

check2 = []
checked2 = 0
for name, d in sorted(skills.items()):
    p = d / "SKILL.md"
    entries, lineno = get_related_skills(p)
    if entries is None: continue
    checked2 += 1
    for e in entries:
        if e and e not in ALLOWED:
            check2.append((p, lineno.get(e, "?"), e))

if check2:
    for p, ln, e in sorted(set(check2), key=lambda x: (str(x[0]), x[1])):
        add(2, "FAIL", f"{p}:{ln}: related_skills entry {e!r} is neither an in-repo skill nor an allowed bundled skill")
else:
    add(2, "PASS", f"all related_skills entries resolve ({checked2} skills have related_skills)")

# ================= CHECK 3: frontmatter name/description ======================
import yaml
def parse_frontmatter(p):
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.M)
    if len(parts) < 3: return None
    try:
        return yaml.safe_load(parts[1])
    except Exception:
        return None

check3 = []
for name, d in sorted(skills.items()):
    p = d / "SKILL.md"
    fm = parse_frontmatter(p)
    if fm is None:
        add(3, "WARN", f"{p}: frontmatter unparsable"); continue
    if fm.get("name") != name:
        check3.append((p, f"frontmatter name {fm.get('name')!r} != folder name {name!r}"))
    if not fm.get("description") or not str(fm.get("description")).strip():
        check3.append((p, "frontmatter description missing/empty"))
if check3:
    for p, msg in check3:
        add(3, "FAIL", f"{p}: {msg}")
else:
    add(3, "PASS", f"all {len(skills)} SKILL.md frontmatter name==folder and description present")

# ================= CHECK 4: deleted skill names ================================
DEL_RE = re.compile(r"(?<![A-Za-z0-9_-])(" + "|".join(re.escape(n) for n in DELETED if n != "plan") + r")(?![A-Za-z0-9_-])")
PLAN_RE = re.compile(r"(?<![A-Za-z0-9_-])plan(?![A-Za-z0-9_-])")
def provenance_in_window(lines, i):
    # Provenance wording often lives in the SECTION HEADER ("## Absorbed skills
    # (Aug 9 2026 consolidation): The following ... were merged into this
    # umbrella") while the flagged line is the bullet list below it -- look
    # back ~5 lines, not just at the current line.
    for j in range(max(0, i-5), i+1):
        low = lines[j].lower()
        if any(w in low for w in PROVENANCE_WORDS):
            return True
    return False

check4_flagged, check4_prov = [], []
for p in md_files:
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        continue
    for i, line in enumerate(lines, 1):
        for m in DEL_RE.finditer(line):
            name = m.group(1)
            if provenance_in_window(lines, i-1):
                check4_prov.append((p, i, name))
            else:
                check4_flagged.append((p, i, name, line.strip()[:150]))
        # "plan" is too common a word: only count explicit skill-reference
        # contexts (skill_view("plan"), `plan`, "the plan skill", related_skills)
        if PLAN_RE.search(line) and re.search(
                r"`plan`|skill_view\(\s*[\"']plan|related_skills[^\n]*\bplan\b|\bplan\b\s+skill|skill\s+named\s+plan|skills?:\s*\S*\bplan\b", line):
            if provenance_in_window(lines, i-1):
                check4_prov.append((p, i, "plan"))
            else:
                check4_flagged.append((p, i, "plan", line.strip()[:150]))

if check4_flagged:
    for p, i, name, snippet in sorted(set(check4_flagged), key=lambda x: (str(x[0]), x[1])):
        add(4, "FAIL", f"{p}:{i}: deleted skill name {name!r} used (not historical provenance): {snippet}")
else:
    add(4, "PASS", "no non-provenance usage of deleted skill names")
for p, i, name in sorted(set(check4_prov), key=lambda x: (str(x[0]), x[1])):
    add(4, "NOTE", f"{p}:{i}: {name!r} mention treated as historical provenance (OK)")

# ================= CHECK 5: duplicate relative paths across skills ============
relmap = defaultdict(list)
for name, d in sorted(skills.items()):
    for f in sorted(d.rglob("*")):
        if f.is_file() and f.name != "SKILL.md":
            relmap[str(f.relative_to(d)).replace("\\", "/")].append(name)
dup = {r: ns for r, ns in relmap.items() if len(ns) > 1}
if dup:
    for r, ns in sorted(dup.items()):
        add(5, "FAIL", f"duplicate relative path {r!r} in skills: {', '.join(ns)}")
else:
    add(5, "PASS", "no duplicate relative paths across skills (excluding SKILL.md)")

# ================= CHECK 6: README category lists and counts ==================
readme = (REPO / "README.md").read_text(encoding="utf-8", errors="replace")
cat_re = re.compile(r"^###\s+([\w-]+)\s+\((\d+)\)\s*$", re.M)
readme_cats = {}
for m in cat_re.finditer(readme):
    cat, cnt = m.group(1), int(m.group(2))
    rest = readme[m.end():]
    nxt = re.search(r"^###\s", rest, re.M)
    block = rest[:nxt.start()] if nxt else rest
    names = [x.strip() for x in re.split(r"[,\n]", block)
             if x.strip() and re.match(r"^[a-z0-9][a-z0-9-]*$", x.strip())]
    readme_cats[cat] = (cnt, names)

actual_cats = defaultdict(list)
for name, d in sorted(skills.items()):
    actual_cats[d.parent.name].append(name)

check6 = []
for cat in sorted(set(readme_cats) | set(actual_cats)):
    if cat not in readme_cats:
        check6.append(f"README missing category section for {cat!r} (tree has {len(actual_cats[cat])})")
        continue
    cnt, names = readme_cats[cat]
    act = sorted(actual_cats.get(cat, []))
    if cnt != len(act):
        check6.append(f"README says {cat} ({cnt}) but tree has {len(act)}")
    if sorted(names) != act:
        if sorted(set(names) - set(act)): check6.append(f"README lists {cat}: not in tree: {sorted(set(names)-set(act))}")
        if sorted(set(act) - set(names)): check6.append(f"tree has {cat}: not in README: {sorted(set(act)-set(names))}")
total_actual = len(skills)
total_readme = sum(c for c, _ in readme_cats.values())
if total_readme != total_actual:
    check6.append(f"README category counts sum to {total_readme}, tree has {total_actual}")
if len(readme_cats) != len(actual_cats):
    check6.append(f"README lists {len(readme_cats)} categories, tree has {len(actual_cats)}")
n_files = sum(1 for f in REPO.rglob("*") if f.is_file() and ".git" not in f.parts)
n_tracked = len(subprocess.check_output(["git", "-C", str(REPO), "ls-files"]).split())
m_claim = re.search(r"(\d+)\s+skills,\s*(\d+)\s+files", readme)
if m_claim:
    cs, fs = int(m_claim.group(1)), int(m_claim.group(2))
    if cs != total_actual: check6.append(f"README claims {cs} skills, actual {total_actual}")
    if fs != n_files: check6.append(f"README claims {fs} files, actual {n_files} on disk ({n_tracked} git-tracked)")
add(6, "INFO", f"on-disk files {n_files}, git-tracked {n_tracked}; README claims {m_claim.group(2) if m_claim else '?'}")

if check6:
    for msg in check6:
        add(6, "FAIL", f"README.md: {msg}")
else:
    add(6, "PASS", "README category lists, counts, and totals match the tree")

# ================= OUTPUT =====================================================
print("=" * 78)
print(f"AUDIT: {REPO}  |  {len(skills)} skills, {len(md_files)} md files, {len(readme_cats)} README categories")
print("=" * 78)
fails = 0
for c in [1, 2, 3, 4, 5, 6]:
    items = results[c]
    n_fail = sum(1 for s, _ in items if s == "FAIL")
    fails += n_fail
    status = "PASS" if n_fail == 0 else "FAIL"
    print(f"\nCHECK {c}: {status}  ({len(items)} findings, {n_fail} FAIL)")
    for s, msg in items:
        print(f"  [{s}] {msg}")
print("\n" + "=" * 78)
print(f"TOTAL: {'ALL CHECKS PASS' if fails == 0 else str(fails) + ' FAILING FINDING(S)'}")
print("=" * 78)
