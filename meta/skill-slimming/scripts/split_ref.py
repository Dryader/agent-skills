#!/usr/bin/env python3
"""Split an oversized reference into topical parts, leaving a pointer index behind.

Usage:
  python3 split_ref.py <file.md | directory> [--cap 15000] [--dry-run]

Why: a pointer to a 50-98 KB reference costs the same as a fat body, and the agent has no way
to know beforehand. Cap references at ~15 KB and split by topic, so a partial need costs a
partial load. The original filename becomes a short index that routes to the parts, so every
existing pointer to it keeps working and no SKILL.md needs editing.

How:
  - parses headings at the shallowest level below H1 (auto-detected: H2-structured files are
    common), ignoring '#' lines inside fenced code blocks
  - groups consecutive sections greedily up to --cap
  - a single section still over the cap is re-split at the next heading level (H4, then H5)
  - parts land in <dir>/<stem>/NN-<slug>.md, each with a provenance comment and the original H1
  - the original file is replaced by an index: one line per part, its topic and its size
  - orphan check: every original line over 30 chars must appear in some part

Exit 1 if any part is still over the cap, or any line was lost. Idempotent-ish: re-running on
an already-split index does nothing useful, so restore the original first (or keep the source copy).
"""
import argparse
import datetime
import pathlib
import re
import shutil
import sys


def slug(s, n=44):
    s = re.sub(r"[`*_#]", "", s).strip()
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()[:n].strip("-") or "part"


def parse_sections(text, level):
    """[(heading, lines)] at one heading level; fenced code blocks are not headings."""
    in_fence, cur, out = False, ("__preamble__", []), []
    for line in text.splitlines(True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and re.match(r"^#{1,6} ", line) and (len(line) - len(line.lstrip("#"))) == level:
            out.append(cur)
            cur = (line.rstrip(), [line])
            continue
        cur[1].append(line)
    out.append(cur)
    return out


def first_level(text):
    """Shallowest heading level below H1, fence-aware. A file structured at H2 needs level 2;
    starting at 3 finds no sections and produces a single useless part."""
    in_fence, levels = False, []
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and re.match(r"^#{2,6} ", line):
            levels.append(len(line) - len(line.lstrip("#")))
    return min(levels) if levels else 3


def make_parts(text, cap, level=None):
    if level is None:
        level = first_level(text)
    secs = parse_sections(text, level)
    chunks, cur = [], []
    for head, lines in secs:
        if cur and len("".join(cur[1])) + len("".join(lines)) > cap:
            chunks.append(cur)
            cur = (head, lines)
        elif cur:
            cur = (cur[0], cur[1] + lines)
        else:
            cur = (head, lines)
    if cur:
        chunks.append(cur)
    parts = []
    for head, lines in chunks:
        body = "".join(lines)
        if len(body) > cap and level < 6:
            subs = make_parts(body, cap, level + 1)
            if len(subs) > 1:
                parts.extend(subs)
                continue
        parts.append((head, body))
    return parts


def split_file(path, cap):
    text = path.read_text(encoding="utf-8", errors="replace")
    title = next((l.strip() for l in text.splitlines() if l.startswith("# ")), "# " + path.stem)
    parts = make_parts(text, cap)
    if len(parts) < 2:
        return None
    outdir = path.parent / path.stem
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir()
    date = datetime.date.today().isoformat()
    index = [f"<!-- index for the split reference {path.name}, {date}; parts live in {path.stem}/ -->",
             title, "",
             f"Index only. Split on {date} because it was {len(text):,} bytes, past the ~15 KB reference"
             " cap. Read only the part you need.", ""]
    sizes = []
    for i, (head, body) in enumerate(parts, 1):
        topic = head.lstrip("# ").strip() if head != "__preamble__" else "overview"
        target = outdir / f"{i:02d}-{slug(topic)}.md"
        target.write_text(
            f"<!-- part {i}/{len(parts)} of {path.name}, split {date}, original {len(text):,} bytes -->\n"
            + title + "\n\n" + body.lstrip("\n"), encoding="utf-8", newline="\n")
        sizes.append(target.stat().st_size)
        index.append(f"- `{path.stem}/{target.name}` — {topic} ({target.stat().st_size:,} bytes)")
    index += ["", "## Overview", "".join(parse_sections(text, first_level(text))[0][1]).strip()]
    path.write_text("\n".join(index) + "\n", encoding="utf-8", newline="\n")
    joined = "\n".join(p.read_text(encoding="utf-8") for p in sorted(outdir.iterdir()))
    lost = [l for l in text.splitlines() if len(l.strip()) > 30 and l.strip() not in joined]
    return len(text), len(parts), max(sizes), path.stat().st_size, lost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--cap", type=int, default=15000)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    root = pathlib.Path(a.target)
    skip = {"SKILL.md", "CHANGELOG.md", "SECURITY.md", "README.md", "LICENSE.md"}
    files = sorted(p for p in (root.rglob("*.md") if root.is_dir() else [root])
                   if p.is_file() and p.name not in skip and p.stat().st_size > a.cap)
    if not files:
        print("nothing over the cap")
        return 0
    bad = 0
    print(f"{'file':44} {'was':>9} {'parts':>5} {'max part':>9} {'index':>7} {'lost':>5}")
    for p in files:
        if a.dry_run:
            parts = make_parts(p.read_text(encoding="utf-8", errors="replace"), a.cap)
            sizes = [len(b) for _, b in parts]
            print(f"{str(p)[-44:]:44} {p.stat().st_size:>9,} {len(parts):>5} {max(sizes):>9,} {'-':>7} {'-':>5}")
            continue
        res = split_file(p, a.cap)
        if not res:
            print(f"{str(p)[-44:]:44} {p.stat().st_size:>9,}     1 - unsplittable (one section)")
            bad += 1
            continue
        was, n, mx, idx, lost = res
        print(f"{str(p)[-44:]:44} {was:>9,} {n:>5} {mx:>9,} {idx:>7,} {len(lost):>5}")
        if lost or mx > a.cap:
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
