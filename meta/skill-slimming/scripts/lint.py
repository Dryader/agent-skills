#!/usr/bin/env python3
"""Skill size lint — catch context weight regrowing in a skill library.

Usage: python3 lint.py [skills_dir] [--max-body-kb 10] [--max-ref-kb 15] [--all]

Flags, in the order they cost context:
  1. SKILL.md bodies over the cap (loaded whole whenever the skill triggers)
  2. single reference files over the cap (one pointer = the whole load)
  3. duplicate reference basenames across skills (two payloads, one topic)
  4. line-initial "read/load/open references/X" pointers at a file over the cap
     (an unconditional read instruction defeats the on-demand split)

Skipped by design:
  - bundled skills (in the Hermes source tree) and hub-installed skills: both are
    refreshed from upstream, so slimming them is wasted work. --all includes them.
    Do NOT key this on the usage log's created_by: a skill written straight into
    skills/ has no created_by, and keying on it silently skipped the agent's own
    skills (that is how a 10.7 KB body went unreported).
  - hidden dirs and the loader's EXCLUDED_SKILL_DIRS (.archive, .hub, .venv, ...):
    the loader never indexes them, so they cost nothing per turn.
  - folded upstream topic packs under references/topics/: kept verbatim and refreshed
    by the pack's own sync script, so their size is not actionable. Reported apart,
    and they do not affect the exit code.
"""
import os, re, sys, json

# mirror agent/skill_utils.py: dirs the loader refuses to walk, and the support dirs it
# prunes once a skill root is found
EXCLUDED_DIRS = frozenset({'.nox', '.hub', '.git', '.pytest_cache', '.tox', '.ruff_cache',
                           'node_modules', '.curator_backups', '.locks', '.archive', 'venv',
                           'site-packages', '.mypy_cache', '__pycache__', '.github', '.venv'})
SUPPORT_DIRS = frozenset({'references', 'assets', 'scripts', 'templates'})


def bundled_roots(repo=None):
    """The two directories inside the Hermes source tree that ship skills."""
    repo = repo or os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "hermes-agent")
    return [os.path.abspath(os.path.join(repo, d)) for d in ("skills", "optional-skills")]


def is_bundled(path, roots):
    """True only for a file INSIDE the bundled tree.

    Skip by path, never by name: a local skill can share a bundled skill's name (a local fork of
    `hermes-agent` here is 48.8 KB against the bundled 13.2 KB and is not refreshed from upstream),
    and a name-keyed skip made that fork invisible to this lint.
    """
    p = os.path.abspath(path)
    return any(p == r or p.startswith(r + os.sep) for r in roots)


def hub_names(skills_dir):
    """Skill names installed from the hub (refreshed from their upstream pack)."""
    try:
        lock = json.load(open(os.path.join(skills_dir, ".hub", "lock.json"), encoding="utf-8"))
    except Exception:
        return set()
    inst = lock.get("installed") or {}
    return set(inst) if isinstance(inst, dict) else {i.get("name") for i in inst}


def skill_files(skills_dir):
    """SKILL.md paths the loader would index: hidden/venv/archive and support dirs pruned."""
    out = []
    for root, dirs, files in os.walk(skills_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
        if "SKILL.md" in files:
            out.append(os.path.join(root, "SKILL.md"))
            dirs[:] = []          # a skill root's subdirs are support dirs, never skills
        else:
            dirs[:] = [d for d in dirs if d not in SUPPORT_DIRS]
    return sorted(out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    skills_dir = args[0] if args else os.path.expanduser("~/.hermes/skills")
    max_body = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--max-body-kb")), 10)) * 1024
    max_ref = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--max-ref-kb")), 15)) * 1024
    include_all = "--all" in sys.argv
    roots = bundled_roots()
    hub = hub_names(skills_dir)
    try:
        usage = json.load(open(os.path.join(skills_dir, ".usage.json"), encoding="utf-8"))
    except Exception:
        usage = {}

    def not_ours(path, name):
        return not include_all and (is_bundled(path, roots) or name in hub)

    body_hits, ref_hits, pack_hits, dupes = [], [], [], {}
    for p in skill_files(skills_dir):
        name = os.path.basename(os.path.dirname(p))
        if not_ours(p, name):
            continue
        d = os.path.dirname(p)
        sz = os.path.getsize(p)
        if sz > max_body:
            entry = usage.get(name)
            usage_n = entry.get("use_count") if isinstance(entry, dict) else 0 or 0
            body_hits.append((sz, name, usage_n or 0))
        refs_root = os.path.abspath(os.path.join(d, "references"))
        for root, dirs, files in os.walk(refs_root):
            dirs[:] = [x for x in dirs if x not in EXCLUDED_DIRS]
            for base in files:
                f = os.path.join(root, base)
                rel = os.path.relpath(f, d).replace(os.sep, "/")
                size = os.path.getsize(f)
                if rel.startswith("references/topics/"):
                    # a folded upstream topic pack: kept verbatim, refreshed by its sync script
                    if size > max_ref:
                        pack_hits.append((size, f"{name}/{rel}"))
                    continue
                # nested = a split part dir (references/<stem>/NN-topic.md) or an absorbed archive;
                # those repeat names across skills BY DESIGN, so they never count as duplicates
                nested = os.path.dirname(os.path.abspath(f)) != refs_root
                if size > max_ref:
                    ref_hits.append((size, f"{name}/{rel}"))
                if not nested and size > 5000:
                    dupes.setdefault(base, []).append(name)
        for line in open(p, encoding="utf-8", errors="replace"):
            m = re.match(r"\s*(?:[-*]\s*)?(?:read|load|open)\s.*?references/([\w\-./]+\.md)", line, re.I)
            if m:
                tgt = os.path.join(d, "references", m.group(1))
                if os.path.exists(tgt) and os.path.getsize(tgt) > max_ref:
                    rel = os.path.relpath(tgt, d).replace(os.sep, "/")
                    bucket = pack_hits if rel.startswith("references/topics/") else ref_hits
                    bucket.append((os.path.getsize(tgt), f"{name} -- unconditional read of {m.group(1)}"))

    def dump(title, rows, limit=25):
        print(f"\n{title}: {len(rows)}")
        for sz, label, *rest in sorted(rows, reverse=True)[:limit]:
            extra = f"  (loaded {rest[0]}x)" if rest else ""
            print(f"  {sz/1024:6.1f} KB  {label}{extra}")

    dump("SKILL.md bodies over cap", body_hits)
    dump("reference files over cap / unconditional reads", ref_hits)
    d = [(b, ", ".join(f"{n}" for n in v)) for b, v in dupes.items() if len(set(v)) > 1]
    print(f"\nduplicate reference basenames across skills: {len(d)}")
    for base, owners in sorted(d)[:15]:
        print(f"  {base} -> {owners}")
    if pack_hits:
        dump("folded upstream topic packs over cap (verbatim; refresh, never slim)", pack_hits, limit=5)
    bad = len(body_hits) + len(ref_hits) + len(d)
    print(f"\nlint: {bad} finding(s).")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
