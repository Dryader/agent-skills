#!/usr/bin/env python3
"""Validation gate for this repository.

Implements every check in AGENTS.md as one runnable command that exits non-zero
on failure, so CI can gate on it. Stdlib only, no dependencies.

    python3 scripts/validate_skills.py

Checks:
  1. frontmatter dialect   name == folder, description present, forbidden keys absent
  2. dangling paths        every scripts/... reference resolves inside its skill root
  3. PII battery           no keys, hex blobs, phone-length digits, real user paths, identities
  4. counts                README.md and SKILLS.md match the tree
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
FORBIDDEN_KEYS = ("author:", "version:", "license:", "platforms:", "metadata:")
SCANNED_EXT = (".md", ".py", ".ps1", ".sh", ".kql")
PII_PATTERNS = (
    (r"BEGIN (?:RSA|OPENSSH|EC|PGP) PRIVATE KEY", "private key", re.I),
    (r"\b[A-Fa-f0-9]{32,}\b", "hex blob (possible key or hash)", re.I),
    (r"\b[1-9]\d{9,10}\b", "10-11 digit number (possible phone or account id)", re.I),
    (r"C:\\Users\\(?!<|Public|Default)[A-Za-z]", "real Windows user path", re.I),
    (r"/home/(?!<)[a-z]+", "real POSIX home path", 0),  # paths are lowercase; /HOME/ENV is a label
    (r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b", "email address", re.I),
)
# vendor example domains and GitHub noreply addresses are not personal data
ALLOWED_EMAIL_DOMAINS = ("contoso.com", "example.com", "example.org", "fabrikam.com",
                         "users.noreply.github.com")
# placeholder local parts, per the repo's placeholder convention
PLACEHOLDER_LOCALS = {"yourname", "your-name", "your_name", "name", "user", "username",
                      "email", "someone", "example", "me", "handle"}
# Identity terms (real names, employers, institutions) deliberately stay OUT of this
# public repo. Export them locally, or set PII_TERMS as a CI secret, comma-separated:
#   PII_TERMS="surname,employer,other-employer" python3 scripts/validate_skills.py
# bundled platform skills that related_skills may legitimately point at
PLATFORM_SKILLS = {
    "powerpoint", "docx", "xlsx", "pdf", "arxiv", "test-driven-development",
    "requesting-code-review", "systematic-debugging", "verification-before-completion",
    "brainstorming", "writing-plans", "executing-plans", "subagent-driven-development",
}

errors: list[str] = []
warnings: list[str] = []


def walk_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def skill_dirs() -> list[str]:
    return sorted(
        d for d, _, fs in os.walk(ROOT)
        if "SKILL.md" in fs and ".git" not in d.split(os.sep)
    )


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def skill_root_of(path: str) -> str | None:
    d = os.path.dirname(path)
    while d and d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, "SKILL.md")):
            return d
        d = os.path.dirname(d)
    return None


def check_frontmatter():
    for d in skill_dirs():
        p = os.path.join(d, "SKILL.md")
        text = open(p, encoding="utf-8").read()
        name = os.path.basename(d)
        if not text.startswith("---\n"):
            errors.append(f"{rel(p)}: does not open with a --- frontmatter block")
            continue
        fm = re.search(r"^---\n(.*?)\n---", text, re.S)
        if not fm:
            errors.append(f"{rel(p)}: unterminated frontmatter block")
            continue
        body = fm.group(1)
        if not re.search(rf"^name:\s*{re.escape(name)}\s*$", body, re.M):
            errors.append(f"{rel(p)}: name: does not match folder ({name})")
        desc = re.search(r"^description:\s*(.+)$", body, re.M)
        if not desc:
            errors.append(f"{rel(p)}: no description:")
        elif len(desc.group(1)) > 200:
            warnings.append(f"{rel(p)}: description is {len(desc.group(1))} chars (>200)")
        for key in FORBIDDEN_KEYS:
            if re.search(rf"^{re.escape(key)}", body, re.M):
                errors.append(f"{rel(p)}: forbidden frontmatter key {key}")
        rs = re.search(r"^related_skills:\s*\[(.*?)\]", body, re.M)
        if rs:
            known = {os.path.basename(d) for d in skill_dirs()} | PLATFORM_SKILLS
            for item in (s.strip().strip("'\"") for s in rs.group(1).split(",")):
                if item and item not in known:
                    warnings.append(f"{rel(p)}: related_skills -> {item} (not in repo or platform list)")


def check_dangling_paths():
    ref = re.compile(r"(references|scripts|templates)/[A-Za-z0-9_.\-]+\.(?:md|py|ps1|sh|kql)")
    for path in walk_files():
        if not path.endswith(SCANNED_EXT):
            continue
        sroot = skill_root_of(path)
        if sroot is None:
            continue
        for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
            if re.search(r"(~/|C:\\|/mnt/)", line):
                continue  # live-environment paths are documentation, not repo refs
            for m in ref.finditer(line):
                target = os.path.normpath(os.path.join(sroot, m.group(0)))
                if not os.path.exists(target):
                    errors.append(f"{rel(path)}:{i}: dangling reference {m.group(0)}")


def check_pii():
    extra = [t.strip() for t in os.environ.get("PII_TERMS", "").split(",") if t.strip()]
    for path in walk_files():
        if not path.endswith(SCANNED_EXT):
            continue
        for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
            for pat, label, flags in PII_PATTERNS:
                m = re.search(pat, line, flags)
                if not m:
                    continue
                if label == "email address":
                    addr = m.group(0).lower()
                    if addr.endswith(ALLOWED_EMAIL_DOMAINS) or addr.split("@")[0] in PLACEHOLDER_LOCALS:
                        continue
                errors.append(f"{rel(path)}:{i}: {label} -> {m.group(0)[:40]}")
            for term in extra:
                if re.search(re.escape(term), line, re.I):
                    errors.append(f"{rel(path)}:{i}: identity term -> {term}")


def check_counts():
    skills = skill_dirs()
    files = [p for p in walk_files()]
    cats: dict[str, int] = {}
    for d in skills:
        cats[rel(d).split("/")[0]] = cats.get(rel(d).split("/")[0], 0) + 1

    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    m = re.search(r"(\d+)\s+skills,\s+(\d+)\s+files,\s+(\d+)\s+categories", readme)
    if not m:
        warnings.append("README.md: no 'N skills, M files, K categories' line found")
    else:
        if int(m.group(1)) != len(skills):
            errors.append(f"README.md says {m.group(1)} skills, tree has {len(skills)}")
        if int(m.group(2)) != len(files):
            errors.append(f"README.md says {m.group(2)} files, tree has {len(files)}")
        if int(m.group(3)) != len(cats):
            errors.append(f"README.md says {m.group(3)} categories, tree has {len(cats)}")

    skills_md = open(os.path.join(ROOT, "SKILLS.md"), encoding="utf-8").read()
    listed = 0
    for m in re.finditer(r"^##\s+([a-z\-]+)\s+\((\d+)\)", skills_md, re.M):
        cat, n = m.group(1), int(m.group(2))
        listed += n
        if cats.get(cat) != n:
            errors.append(f"SKILLS.md says {cat} has {n}, tree has {cats.get(cat, 0)}")
    if listed != len(skills):
        errors.append(f"SKILLS.md registry totals {listed}, tree has {len(skills)}")
    for d in skills:
        if os.path.basename(d) not in skills_md:
            warnings.append(f"{rel(d)}: not listed in SKILLS.md")
    return len(skills), len(files), len(cats)


def main() -> int:
    check_frontmatter()
    check_dangling_paths()
    check_pii()
    n_skills, n_files, n_cats = check_counts()

    print(f"skills: {n_skills}   files: {n_files}   categories: {n_cats}")
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"FAIL  {e}")
    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"all checks passed ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
