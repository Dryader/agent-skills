#!/usr/bin/env python3
"""Verify a context-diet run: every moved section fully contained in its ref file,
frontmatter still parses, header+pointer present in body.

Usage: python3 verify.py <spec.json> [skills_dir]

The truth test is FULL SECTION containment (the entire moved section text from the
backup must appear in its ref file). Line-level checks give false positives on
common tokens (---, imports, braces) that legitimately exist in kept sections.
"""
import os, sys, json, tarfile, yaml

BASE = os.environ.get("HERMES_SKILLS_DIR", os.path.expanduser("~/.hermes/skills"))
BACKUP = os.environ.get("SKILL_SLIM_BACKUP", os.path.expanduser("~/skill-slim-backup"))


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

    ok = True
    total = 0
    for entry in spec:
        skill_rel = entry["skill"]
        sections = entry["sections"]
        skill_name = os.path.basename(skill_rel)
        tarpath = os.path.join(BACKUP, skill_name + ".tar.gz")
        if not os.path.exists(tarpath):
            print(f"FAIL {skill_rel}: no backup tarball")
            ok = False
            continue
        with tarfile.open(tarpath, "r:gz") as tar:
            orig = tar.extractfile(tar.getmember(skill_name + "/SKILL.md")).read().decode("utf-8")
        orig_lines = orig.split("\n")
        slim = open(os.path.join(BASE, skill_rel, "SKILL.md"), encoding="utf-8").read()

        # frontmatter
        try:
            fm = yaml.safe_load(slim.split("---\n", 2)[1])
            assert fm.get("name") == skill_name
        except Exception as ex:
            print(f"FAIL {skill_rel}: frontmatter: {ex}")
            ok = False

        ref_txts = {}
        for ref in set(s["ref"] for s in sections):
            rp = os.path.join(BASE, skill_rel, "references", ref)
            if not os.path.exists(rp) or os.path.getsize(rp) == 0:
                print(f"FAIL {skill_rel}: ref missing/empty {ref}")
                ok = False
            else:
                ref_txts[ref] = open(rp, encoding="utf-8").read()

        for sec in sections:
            s = find_line(orig_lines, sec["start"])
            e = find_line(orig_lines, sec["end"], s + 1) if sec.get("end") else len(orig_lines)
            seg = "\n".join(orig_lines[s:e])
            total += 1
            ref_txt = ref_txts.get(sec["ref"], "")
            if seg.rstrip() not in ref_txt:
                print(f"FAIL {skill_rel}: section NOT contained in {sec['ref']}: {sec['start'][:50]}")
                ok = False
            # header + pointer present in body
            hs = find_line(slim.split("\n"), sec["start"])
            if hs is None:
                print(f"FAIL {skill_rel}: header gone from body: {sec['start'][:50]}")
                ok = False
            elif "context diet" not in "\n".join(slim.split("\n")[hs:hs + 4]):
                print(f"FAIL {skill_rel}: no pointer after header: {sec['start'][:50]}")
                ok = False

        print(f"{skill_rel}: {len(orig)} -> {len(slim)}B, {len(set(s['ref'] for s in sections))} ref files")

    print(f"checked {total} sections")
    print("ALL OK" if ok else "FAILURES PRESENT")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
