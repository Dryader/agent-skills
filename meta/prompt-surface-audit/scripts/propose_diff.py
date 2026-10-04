#!/usr/bin/env python3
"""Build a reviewable unified diff without touching the originals.

Usage:  python3 propose_diff.py <edits.json> [out.diff]

edits.json:
{
  "surface_root": "C:/Users/[user]/.hermes/skills",
  "edits": {"rel/path/SKILL.md": [["old text", "new text"], ...]},
  "delete": ["rel/other/SKILL.md"]
}

Every old string must match EXACTLY ONCE in its file; otherwise that hunk is
skipped and reported. That assertion is the evidence check for the audit
report: a quoted line that is not byte-exact is a report bug.

before/ and after/ trees plus the diff land next to the output path. Nothing is
written back into the surface. Verify with:

  cd <surface_root> && patch -p1 --dry-run < <out.diff>
"""
import difflib
import json
import os
import shutil
import sys


def normalize(text, crlf):
    return text.replace("\n", "\r\n") if crlf else text


def apply_edits(src, pairs, before_dir, after_dir, rel, problems):
    os.makedirs(os.path.dirname(os.path.join(before_dir, rel)), exist_ok=True)
    shutil.copy2(src, os.path.join(before_dir, rel))
    raw = open(src, encoding="utf-8", errors="replace").read()
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    for i, pair in enumerate(pairs):
        old, new = pair[0], pair[1]
        n = text.count(old)
        if n != 1:
            problems.append(f"{rel} hunk {i + 1}: matched {n} times, SKIPPED (first 90 chars: {old[:90]!r})")
            continue
        text = text.replace(old, new, 1)
    after = normalize(text, crlf)
    os.makedirs(os.path.dirname(os.path.join(after_dir, rel)), exist_ok=True)
    with open(os.path.join(after_dir, rel), "w", encoding="utf-8", newline="") as fh:
        fh.write(after)
    return "".join(difflib.unified_diff(
        open(os.path.join(before_dir, rel), encoding="utf-8").read().splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{rel}", tofile=f"b/{rel}", n=2))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    root = os.path.expanduser(spec["surface_root"])
    out = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "proposed.diff")
    base = os.path.join(os.path.dirname(out), "diff-work")
    before_dir, after_dir = os.path.join(base, "before"), os.path.join(base, "after")
    shutil.rmtree(base, ignore_errors=True)

    chunks, problems, hunks = [], [], 0
    for rel, pairs in spec.get("edits", {}).items():
        src = os.path.join(root, rel)
        if not os.path.exists(src):
            problems.append(f"{rel}: missing")
            continue
        hunks += len(pairs)
        chunks.append(apply_edits(src, pairs, before_dir, after_dir, rel, problems))

    for rel in spec.get("delete", []):
        src = os.path.join(root, rel)
        if not os.path.exists(src):
            problems.append(f"{rel}: missing")
            continue
        body = open(src, encoding="utf-8", errors="replace").read()
        chunks.insert(0, f"# NOTE: whole-file deletion proposed ({rel})\n" + "".join(
            difflib.unified_diff(body.splitlines(keepends=True), [], fromfile=f"a/{rel}", tofile="/dev/null", n=2)))

    header = ("# Proposed diff - prompt surface audit\n"
              f"# surface_root: {root}\n"
              f"# apply:  cd {root} && patch -p1 --dry-run < {out}   (then drop --dry-run)\n"
              "# Nothing here has been applied. Take hunks selectively.\n\n")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(header + "\n".join(chunks))

    print(f"files: {len(spec.get('edits', {})) + len(spec.get('delete', []))}  hunks offered: {hunks}")
    for p in problems:
        print("  PROBLEM:", p)
    print(f"diff -> {out}")
    print(f"verify: cd {root} && patch -p1 --dry-run < {out}")


if __name__ == "__main__":
    main()
