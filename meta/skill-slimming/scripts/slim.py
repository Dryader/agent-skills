#!/usr/bin/env python3
"""Context-diet extraction: move data sections out of SKILL.md bodies into references/.

Usage: python3 slim.py <spec.json> [skills_dir]

Spec format:
  [{"skill": "category/name",
    "sections": [{"start": "## Header prefix", "end": "## Next header prefix", "ref": "file.md"},
                  {"start": "## Last section", "end": null, "ref": "file.md"}]}]

- start/end are line prefixes matched with str.startswith; end null = to EOF
- sections sharing a ref filename concatenate into one references/<ref> file
- the section's header line stays in the body; content moves to the ref file
- backs up each skill dir (tar.gz) to ~/skill-slim-backup/ before editing
- idempotent: skips skills whose body already contains the "context diet" marker
"""
import os, sys, json, tarfile, datetime

BASE = os.environ.get("HERMES_SKILLS_DIR", os.path.expanduser("~/.hermes/skills"))
BACKUP = os.environ.get("SKILL_SLIM_BACKUP", os.path.expanduser("~/skill-slim-backup"))
DATE = datetime.date.today().isoformat()


def find_line(lines, prefix, start=0):
    for i in range(start, len(lines)):
        if lines[i].startswith(prefix):
            return i
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    spec_path = sys.argv[1]
    if len(sys.argv) > 2:
        global BASE
        BASE = sys.argv[2]
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    os.makedirs(BACKUP, exist_ok=True)

    all_errors = []
    report = []
    for entry in spec:
        skill_rel = entry["skill"]
        sections = entry["sections"]
        skill_dir = os.path.join(BASE, skill_rel)
        sk_path = os.path.join(skill_dir, "SKILL.md")
        refs_dir = os.path.join(skill_dir, "references")
        skill_name = os.path.basename(skill_rel)
        errs = []

        if not os.path.exists(sk_path):
            all_errors.append(f"MISSING SKILL.md: {skill_rel}")
            continue
        txt = open(sk_path, encoding="utf-8").read()
        if "context diet" in txt:
            report.append(f"{skill_rel}: SKIPPED (already slimmed)")
            continue
        lines = txt.split("\n")

        # start prefixes must each appear exactly once
        for sec in sections:
            n = sum(1 for l in lines if l.startswith(sec["start"]))
            if n != 1:
                errs.append(f"START {n}x (need 1): {skill_rel}: {sec['start'][:60]}")
        if errs:
            all_errors += errs
            continue

        # backup (once per skill)
        tarpath = os.path.join(BACKUP, skill_name + ".tar.gz")
        if not os.path.exists(tarpath):
            with tarfile.open(tarpath, "w:gz") as tar:
                tar.add(skill_dir, arcname=skill_name)

        # ref collision check
        for sec in sections:
            if os.path.exists(os.path.join(refs_dir, sec["ref"])):
                errs.append(f"REF EXISTS (abort): {skill_rel}/references/{sec['ref']}")
        if errs:
            all_errors += errs
            continue

        # Resolve all section spans on the ORIGINAL lines, process bottom-up so
        # chained sections (end == next start) and any ordering in the spec work.
        spans = []
        for sec in sections:
            s = find_line(lines, sec["start"])
            if s is None:
                errs.append(f"BOUNDARY: {skill_rel}: start not found: {sec['start'][:50]}")
                continue
            e = find_line(lines, sec["end"], s + 1) if sec.get("end") else len(lines)
            if e is None:
                errs.append(f"BOUNDARY: {skill_rel}: end not found for {sec['start'][:50]}")
                continue
            spans.append((s, e, sec))
        if errs:
            all_errors += errs
            continue
        # overlap check: a section may not contain another section's start
        spans_sorted = sorted(spans)
        for i in range(len(spans_sorted) - 1):
            s1, e1, _ = spans_sorted[i]
            s2, _, _ = spans_sorted[i + 1]
            if s2 < e1:
                errs.append(f"OVERLAP: {skill_rel}: {spans_sorted[i][2]['start'][:40]} "
                            f"contains {spans_sorted[i + 1][2]['start'][:40]} "
                            f"(end marker '{spans_sorted[i][2].get('end')}' is past the next start)")
        if errs:
            all_errors += errs
            continue

        # group by ref file, extract, replace with header+pointer
        new_lines = list(lines)
        ref_contents = {}
        for s, e, sec in sorted(spans, reverse=True):
            ref = sec["ref"]
            ref_contents.setdefault(ref, [])
            ref_contents[ref].append("\n".join(new_lines[s:e]))
            pointer = (f"\n> Data moved to references/{ref} ({DATE} context diet). "
                       f"Load on demand: skill_view(name='{skill_name}', "
                       f"file_path='references/{ref}').\n")
            new_lines[s:e] = [new_lines[s], pointer]
        for ref in ref_contents:
            # restore document order within each ref file
            ref_contents[ref] = "\n\n".join(reversed(ref_contents[ref]))
        if errs:
            all_errors += errs
            continue

        os.makedirs(refs_dir, exist_ok=True)
        for ref, content in ref_contents.items():
            header = (f"# {ref[:-3].replace('-', ' ')} — extracted {DATE} from "
                      f"{skill_rel}/SKILL.md (context diet). Loaded on demand.\n\n")
            with open(os.path.join(refs_dir, ref), "w", encoding="utf-8") as f:
                f.write(header + content + "\n")

        new_txt = "\n".join(new_lines)
        open(sk_path, "w", encoding="utf-8").write(new_txt)
        report.append(f"{skill_rel}: {len(txt)} -> {len(new_txt)}B ({len(ref_contents)} ref files)")

    print("\n".join(report))
    if all_errors:
        print("\n=== ERRORS ===")
        for e in all_errors:
            print(" ", e)
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
