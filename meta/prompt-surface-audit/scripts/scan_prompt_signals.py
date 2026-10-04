#!/usr/bin/env python3
"""Count dated-prompt signals across a prompt surface.

Usage:  python3 scan_prompt_signals.py <surface-root> [out-dir]

Writes hits.json (signal, file, line, text for every match) and per_file.json
(line counts, per-signal counts, numbered-block and table counts) into out-dir
(default: ./audit-data beside this script).

Booster markers are matched CASE-SENSITIVELY on purpose: matching them
case-insensitively picks up ordinary prose ("only", "required") and inflates
the count by more than an order of magnitude.
"""
import json
import os
import re
import sys
from collections import Counter

SIG = {
    "caps":       re.compile(r"\b(MUST|NEVER|ALWAYS|CRITICAL|IMPORTANT|MANDATORY|DO NOT|NON-NEGOTIABLE)\b"),
    "caps_soft":  re.compile(r"\b(Never|Always|Do not|Don't|Avoid)\b"),
    "prohib":     re.compile(r"^\s*[-*\d.]*\s*(Do not|Never|Avoid|Don'?t)\b", re.IGNORECASE),
    "hedge":      re.compile(r"\b(try to|if possible|ideally|where possible|as appropriate)\b", re.IGNORECASE),
    "numbered":   re.compile(r"^\s*\d+[.)]\s+\S"),
    "date":       re.compile(r"20\d\d-\d\d-\d\d|\bas of (20\d\d|[A-Z][a-z]+ 20\d\d)|\b(last |re-)?(verified|updated|checked) (on|as of)\b", re.IGNORECASE),
    "modelname":  re.compile(r"\b(claude-\d|claude-[a-z]+-\d|gpt-[34]|gpt-4o|gemini-\d|deepseek-v\d|qwen[0-9.]|llama[- ]?[0-9]|opus \d|sonnet \d|haiku \d)\b", re.IGNORECASE),
    "apifeature": re.compile(r"budget_tokens|tool_choice|stop_sequences|output_config|prefill|thinking: \{|effort\b|temperature|top_p"),
    "numcap":     re.compile(r"at most \d+|max(?:imum)? \d+ (words|lines|bullets|sentences)|under \d+ words|fewer than \d+", re.IGNORECASE),
    "identity":   re.compile(r"^You are (a|an|the)\b"),
    "repetition": re.compile(r"\b(Remember,|Again,|As (stated|noted|mentioned) above)\b"),
    "grader":     re.compile(r"\b(graded|grader|rubric|hidden tests?|eval suite|benchmark)\b", re.IGNORECASE),
    "cadence":    re.compile(r"every \d+ (steps|turns|tool calls|messages)|after (every|each) (third|second|three|two|few) ", re.IGNORECASE),
    "table_row":  re.compile(r"^\s*\|.*\|\s*$"),
}
FENCE = re.compile(r"^\s*```")


def walk(root, kind):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".archive", ".git", "node_modules")]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            if kind == "skill" and fn != "SKILL.md":
                continue
            if kind == "ref" and fn == "SKILL.md":
                continue
            yield os.path.join(dirpath, fn)


def frontmatter(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    return m.group(1) if m else ""


def scan(root, kind):
    per, hits = {}, []
    for path in walk(root, kind):
        rel = os.path.relpath(path, root).replace("\\", "/")
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        counts, in_fence, run, blocks = Counter(), False, [], []
        for i, line in enumerate(lines, 1):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for name, rx in SIG.items():
                if name in ("numbered", "table_row"):
                    continue
                if rx.search(line):
                    counts[name] += 1
                    hits.append({"sig": name, "file": rel, "line": i, "text": line.strip()[:220]})
            if SIG["numbered"].match(line):
                run.append(i)
            else:
                if len(run) >= 8:
                    blocks.append((run[0], run[-1], len(run)))
                run = []
        if len(run) >= 8:
            blocks.append((run[0], run[-1], len(run)))
        per[rel] = {"lines": len(lines), "counts": dict(counts),
                    "table_rows": sum(1 for l in lines if SIG["table_row"].match(l)),
                    "numbered_blocks": blocks,
                    "frontmatter_chars": len(frontmatter(path))}
    return per, hits


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.hermes/skills"))
    out = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit-data")
    os.makedirs(out, exist_ok=True)
    print(f"surface root: {root}")
    for kind, label in (("skill", "SKILL.md"), ("ref", "references / other .md")):
        per, hits = scan(root, kind)
        agg = Counter()
        for v in per.values():
            for k, n in v["counts"].items():
                agg[k] += n
        print(f"\n##### {label}: {len(per)} files, {sum(v['lines'] for v in per.values())} lines")
        print("aggregate:", dict(agg))
        print(f"table rows: {sum(v['table_rows'] for v in per.values())}  "
              f"frontmatter chars: {sum(v['frontmatter_chars'] for v in per.values())}")
        json.dump(per, open(os.path.join(out, f"per_{kind}.json"), "w", encoding="utf-8"), indent=1)
        json.dump(hits, open(os.path.join(out, f"hits_{kind}.json"), "w", encoding="utf-8"), indent=1)
        ranked = sorted(per.items(), key=lambda kv: -(kv[1]["counts"].get("caps", 0) + 0.5 * kv[1]["counts"].get("prohib", 0)))
        print("top 20 by caps+prohib:")
        for rel, v in ranked[:20]:
            c = v["counts"]
            print(f"  caps={c.get('caps', 0):3d} prohib={c.get('prohib', 0):3d} hedge={c.get('hedge', 0):2d} "
                  f"date={c.get('date', 0):2d} model={c.get('modelname', 0):2d} "
                  f"numblk={len(v['numbered_blocks'])} tables={v['table_rows']:4d} lines={v['lines']:5d}  {rel}")
    print(f"\nper-signal and every match -> {out}")


if __name__ == "__main__":
    main()
