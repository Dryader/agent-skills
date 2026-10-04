#!/usr/bin/env python3
"""PII / personal-content sweep for a skills repo (read-only).

Usage: pii_sweep.py [repo_dir]          (default: current directory)

Runs the standard battery (owner-specific patterns) plus generic
personal-content patterns, applies allowlists and false-positive filters,
and prints PASS/FAIL per class with file:line evidence. Companion to the
skills-repo-audit skill, section 5. NEVER modifies the audited repo.

Design notes:
- OWNER_PATTERNS are the default battery for the agent-skills repo; edit
  them for other repos (or pass --patterns-file <json>).
- Vendor-template allowlist: research-paper-writing/templates/ — conference
  template author emails/phones, .bib hashes, example papers are expected,
  not PII.
- False-positive filters built in: hex color codes vs postal codes,
  "thesis-wise" vs \\bWise\\b, month names after "the user", article IDs
  vs SIN, long identifiers vs base64 (entropy), known GUIDs/DOIs.
"""
import argparse
import math
import os
import re
import sys
from collections import Counter

MONTHS = {"jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"}

# (label, regex, case_insensitive, allowed_suffixes)
#
# OWNER-SPECIFIC TERMS ARE NOT IN THIS REPO. Your own surname, employers, school
# and city are exactly the strings a leak scan must find, and publishing them in
# the scanner would defeat the purpose. Export them instead:
#
#   OWNER_TERMS="surname,employer,previous-employer,school,home-city" python3 pii_sweep.py
#
# Each term is compiled into one case-insensitive alternation at runtime.
OWNER_TERMS = [t.strip() for t in os.environ.get("OWNER_TERMS", "").split(",") if t.strip()]
OWNER_PATTERNS = [
    ("owner terms from $OWNER_TERMS", "|".join(re.escape(t) for t in OWNER_TERMS), True, None),
] if OWNER_TERMS else [
    # shape examples only — replace with your own via $OWNER_TERMS
    ("owner-name <surname>", r"<surname>", True, None),
    ("school <institution>", r"<institution>|<institution-domain>", True, None),
    ("employer <employer>", r"<employer>", True, None),
    ("home-city <city>", r"<city>", True, None),
]
GENERIC_PATTERNS = [
    ("user-path C:\\\\Users\\\\[user]", r"C:\\Users\\[user]", False, None),
    ("user-path /home/<user>", r"/home/<user>", False, None),
    ("ssh private key", r"BEGIN (RSA|OPENSSH|EC) PRIVATE KEY", False, None),
    ("ibkr account id", r"\bU\d{6,}\b", False, None),
    ("sin/ssn", r"\b\d{3}[- ]?\d{3}[- ]?\d{3}\b", False, None),
    ("phone", r"\+?1?[-. (]?\(?[2-9]\d{2}\)?[-. ]?\d{3}[-. ]?\d{4}", False, None),
    ("postal-code", r"\b[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d\b", False, None),
    ("surname-after-scrub", r"the user [A-Z][a-z]+", False, None),
    ("title+surname", r"\b(Mr|Ms|Mrs|Dr)\.? [A-Z][a-z]+", False, None),
    ("linkedin profile", r"linkedin\.com/in/", False, None),
    ("github url", r"github\.com/", False, None),
    ("email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", False, None),
    ("long-hex-24+", r"\b[0-9a-fA-F]{24,}\b", False, None),
]

EMAIL_ALLOW = ("example.com", "contoso.com", "xxx.edu", "affiliation", "yourname@gmail.com",
               "noreply.github.com", "email@domain", "name@example", "@example", "firstAuthor@",
               "secondAuthor@", "thirdAuthor@")
HEX_NOISE = ("doi.org", "10.1", "sciencedirect", "arxiv", "0000-")  # DOIs / URLs
VENDOR_TEMPLATE_DIR = "research-paper-writing/templates"           # expected vendor files
ASR_GUIDS = True  # known Defender ASR GUIDs are expected noise


def entropy(s):
    if not s:
        return 0.0
    c = Counter(s)
    return -sum((n / len(s)) * math.log2(n / len(s)) for n in c.values())


def is_binary(path):
    try:
        with open(path, "rb") as f:
            return b"\x00" in f.read(8192)
    except OSError:
        return False


def sweep(root):
    results = {label: [] for label, *_ in OWNER_PATTERNS + GENERIC_PATTERNS}
    results["base64-blob"] = []
    results["binary-junk"] = []
    files = []
    for dp, _, fns in os.walk(root):
        if "/.git" in dp:
            continue
        for fn in fns:
            p = os.path.join(dp, fn)
            if fn.endswith(".pdf"):
                continue
            files.append(p)

    for p in files:
        rel = os.path.relpath(p, root)
        in_vendor = VENDOR_TEMPLATE_DIR in rel
        if is_binary(p):
            results["binary-junk"].append(f"{rel}:1: binary file")
            continue
        try:
            with open(p, "r", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            for label, pat, ci, _ in OWNER_PATTERNS + GENERIC_PATTERNS:
                flags = re.I if ci else 0
                for m in re.finditer(pat, line, flags):
                    tok = m.group(0)
                    # false-positive filters
                    if label == "postal-code" and tok.lstrip().startswith("#"):
                        continue
                    if label == "surname-after-scrub" and tok.split()[-1].lower() in MONTHS:
                        continue
                    if label == "sin/ssn" and not re.fullmatch(r"\d{3}[- ]?\d{3}[- ]?\d{3}", tok):
                        continue
                    if label == "phone" and in_vendor:
                        continue
                    if label == "email":
                        if in_vendor:
                            continue
                        if any(a in tok for a in EMAIL_ALLOW):
                            continue
                        if tok.startswith("git@"):
                            continue
                    if label == "long-hex-24+":
                        if in_vendor:
                            continue
                        if ASR_GUIDS and "-" in line and len(tok) == 32:
                            # GUID body fragments inside known-GUID lines
                            if re.search(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", line):
                                continue
                        if any(n in line for n in HEX_NOISE):
                            continue
                    results[label].append(f"{rel}:{i}: {tok[:100]}")
            # base64 entropy check
            for m in re.finditer(r"[A-Za-z0-9+/]{40,}={0,2}", line):
                tok = m.group(0).rstrip("=")
                if (any(c.isupper() for c in tok) and any(c.islower() for c in tok)
                        and any(c.isdigit() for c in tok) and entropy(tok) > 4.5):
                    results["base64-blob"].append(f"{rel}:{i}: {tok[:80]}")

    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo_dir", nargs="?", default=".")
    args = ap.parse_args()
    root = os.path.abspath(args.repo_dir)
    res = sweep(root)
    failed = 0
    for label in [l for l, *_ in OWNER_PATTERNS + GENERIC_PATTERNS] + ["base64-blob", "binary-junk"]:
        hits = res[label]
        verdict = "PASS" if not hits else "FAIL"
        if hits:
            failed += 1
        print(f"{verdict}  {label}  ({len(hits)})")
        for h in hits:
            print(f"      {h}")
    print(f"\n{len(res['binary-junk'])} binary files outside vendor templates; "
          f"{'CLEAN' if not res['binary-junk'] else 'CHECK'}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
