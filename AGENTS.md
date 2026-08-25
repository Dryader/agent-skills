# AGENTS.md

Working conventions for this repository. Read this before adding, modifying, or auditing skills here. These conventions are load-bearing, not style.

## What this repo is

A portfolio of original, battle-tested agent skills in the open [Agent Skills](https://agentskills.io/specification) format (`SKILL.md` with YAML frontmatter). Every skill was written and exercised in real sessions. Nothing here is adapted from a public collection, nothing is personal data, and nothing is product documentation.

## Structure

- One directory per skill, grouped into 8 categories (`agent-infrastructure`, `dev-workflow`, `github`, `enterprise-security`, `finance`, `research`, `endpoint-engineering`, `documents`).
- Each skill is a **single self-contained `SKILL.md`**. Historical reference files were folded into their bodies as `## Reference:` appendix sections during the Aug 2026 restructure. Do not create new `references/` or `templates/` directories.
- Optional `scripts/` holds runnable code (`.py`, `.ps1`, `.sh`, `.kql`) that the skill invokes. Code is the only thing that lives outside the skill body.
- `README.md` (repo overview), `SKILLS.md` (registry), `LICENSE` (MIT), this file.

## Frontmatter dialect — the ONLY shape allowed

```yaml
---
name: <must match the folder name>
description: <required; tells the agent when to load this skill>
tags: [<optional, top-level>]
triggers:
  - <optional, top-level>
related_skills: [<optional, top-level>]
---
```

- `author:`, `version:`, `license:`, `platforms:`, and `metadata:` blocks are **forbidden** in this repo. Attribution belongs to the repo owner; the repo LICENSE covers licensing; versioning is git's job.
- `related_skills` must resolve to a skill in this repo or to a known bundled platform skill (`powerpoint`, `docx`, `arxiv`, `test-driven-development`, `requesting-code-review`, `systematic-debugging`, etc.). Never to a culled skill.

## Content rules

1. **Original work only.** Do not ship a skill that is a lightly-rewritten copy of someone else's public work.
2. **No personal data.** Placeholders are the convention: `[employer]`, `[institution]`, `[home city]`, `[fleet size]`, `[holdings list]`, `[Name]`, `[handle]`, `<user>`, `<REDACTED>`. Never a real name, school, employer, city, key, account number, or holdings list. Live-environment paths (`~/portfolio_audit/`, `~/.hermes/`, `C:\Users\<user>\`) are acceptable in prose as documentation of the workflow — with `<user>`, never a real username.
3. **No dangling references.** Every `scripts/…` path mentioned in a skill body must exist. Folded content lives in the body; never point at `references/…` (those directories no longer exist).
4. **No dated landscape.** Vendor pricing, tool comparisons, and adoption surveys go stale the day they are written. Capture the durable lesson, cull the landscape.
5. **Ethically sensitive or personally revealing work does not belong here.** When in doubt about whether a skill is defensible in public, leave it out.

## Adding or modifying a skill

1. Match the frontmatter dialect above; `name:` equals the folder name; keep `description` under ~200 chars.
2. If the skill needs supporting prose, fold it into the body as an appendix section. Only code goes in `scripts/`.
3. Update `SKILLS.md` (registry) and, if counts or categories change, `README.md`. The two must always match the tree.
4. Run the validation checks below before committing.

## Validation (run before every commit)

```bash
# 1. frontmatter: every SKILL.md parses, name == folder, description present, no author:
python3 - <<'EOF'
import os, re
bad = []
for root, dirs, files in os.walk('.'):
    if '.git' in root or 'SKILL.md' not in files: continue
    p = os.path.join(root, 'SKILL.md')
    c = open(p, encoding='utf-8').read()
    fm = re.search(r'^---\n(.*?)\n---', c, re.S)
    if not fm or not re.search(r'^name:\s*' + re.escape(os.path.basename(root)) + r'\s*$', c, re.M) or not re.search(r'^description:', c, re.M) or re.search(r'^author:', c, re.M):
        bad.append(p)
print(bad or 'frontmatter OK')
EOF

# 2. dangling paths (resolved per skill root):
python3 - <<'EOF'
import os, re
def skill_root(p):
    d = os.path.dirname(p)
    while d and not os.path.exists(os.path.join(d, 'SKILL.md')):
        nd = os.path.dirname(d)
        if nd == d: return None
        d = nd
    return d
hits = []
for root, dirs, files in os.walk('.'):
    if '.git' in root: continue
    for fn in files:
        if not fn.endswith(('.md', '.py', '.ps1', '.sh', '.kql')): continue
        p = os.path.join(root, fn)
        sroot = skill_root(p)
        if sroot is None: continue
        for i, line in enumerate(open(p, encoding='utf-8', errors='replace'), 1):
            if re.search(r'(~/|C:\\|/mnt/)', line):  # live-env paths are documented, not repo refs
                continue
            for m in re.finditer(r'(references|scripts|templates)/[A-Za-z0-9_.\-]+\.(?:md|py|ps1|sh|kql)', line):
                if not os.path.exists(os.path.normpath(os.path.join(sroot, m.group(0)))):
                    hits.append(f"{p}:{i}: {m.group(0)}")
print(hits or 'paths OK')
EOF

# 3. PII battery (any hit = stop):
grep -rniE "BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|[A-Fa-f0-9]{32,}|[0-9]{9}|C:\\Users\\[A-Za-z]|/home/[a-z]+" . --include="*.md" --include="*.py" --include="*.ps1" --include="*.sh" --include="*.kql" | grep -v ".git/" || echo "PII OK"

# 4. counts: README + SKILLS.md match the tree:
echo "skills: $(find . -name SKILL.md -not -path './.git/*' | wc -l), files: $(find . -type f -not -path './.git/*' | wc -l)"
```

## Git

- Repo is private, single-lineage history.
- Commit identity: `Dryader <dryader@users.noreply.github.com>`.
- Never commit secrets, real keys, or unscrubbed personal data.
