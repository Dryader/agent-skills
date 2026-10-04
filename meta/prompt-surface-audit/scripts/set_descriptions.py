#!/usr/bin/env python3
"""Rewrite SKILL.md description lines safely: guard, back up, verify.

    python3 set_descriptions.py edits.json [skills_dir] [--force] [--allow-hub]

edits.json maps skill name -> new description text.

Per skill the script refuses and reports instead of guessing:
  * hub-installed names (the hub owns that path; `hermes skills update` overwrites
    local edits) unless --allow-hub
  * YAML block-scalar descriptions (`description: |` / `>`), which must be rewritten by hand
  * descriptions over 60 chars or missing the trailing period, unless --force

It writes every replaced original to ~/.hermes/backups/desc-backup-<stamp>.json (the
revert source), preserves each file's line endings, then re-reads every edited file and
re-parses its frontmatter. Exit code is 1 if anything was skipped or failed verification,
so a caller can gate on it.

Reverting: feed the backup file straight back in as edits.json.
"""
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

BAR = 60
FRONTMATTER = re.compile(r'^---\r?\n(.*?)\r?\n---\r?\n', re.S)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('edits', help='JSON file: {"skill-name": "new description"}')
    ap.add_argument('skills_dir', nargs='?', default=os.path.expanduser('~/.hermes/skills'))
    ap.add_argument('--force', action='store_true', help='ignore the bar and period checks')
    ap.add_argument('--allow-hub', action='store_true', help='also edit hub-installed skills')
    args = ap.parse_args()

    skills = Path(args.skills_dir).expanduser()
    edits = json.loads(Path(args.edits).read_text(encoding='utf-8'))
    if not isinstance(edits, dict):
        print('edits file must be a JSON object of name -> description')
        return 2

    hub = set()
    lock = skills / '.hub' / 'lock.json'
    if lock.is_file():
        try:
            hub = set(json.loads(lock.read_text(encoding='utf-8')).get('installed', {}))
        except Exception:
            hub = set()

    paths = {md.parent.name: md for md in skills.rglob('SKILL.md')
             if '.archive' not in md.parts}

    backup, skipped, changed = {}, [], []
    for name, new in sorted(edits.items()):
        new = str(new).strip()
        if name in hub and not args.allow_hub:
            skipped.append((name, 'hub-installed: hub owns the path, update would overwrite'))
            continue
        if len(new) > BAR and not args.force:
            skipped.append((name, 'description is %d chars (bar is %d)' % (len(new), BAR)))
            continue
        if not new.endswith('.') and not args.force:
            skipped.append((name, 'description does not end with a period'))
            continue
        md = paths.get(name)
        if md is None:
            skipped.append((name, 'not in the active tree'))
            continue
        text = md.read_text(encoding='utf-8')
        m = re.search(r'^description:[^\r\n]*', text, re.M)
        if not m:
            skipped.append((name, 'no description line'))
            continue
        if re.match(r'^description:\s*[|>]', m.group(0)):
            skipped.append((name, 'block-scalar description: rewrite by hand'))
            continue
        old = m.group(0).split(':', 1)[1].strip().strip('"').strip("'")
        if old == new:
            continue
        backup[name] = old
        md.write_text(text[:m.start()] + 'description: "%s"' % new.replace('"', '\\"') + text[m.end():],
                      encoding='utf-8')
        changed.append(name)

    bak_path = None
    if backup:
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        bak_path = Path(os.path.expanduser('~/.hermes/backups/desc-backup-%s.json' % stamp))
        bak_path.parent.mkdir(parents=True, exist_ok=True)
        bak_path.write_text(json.dumps(backup, indent=1, ensure_ascii=False), encoding='utf-8')

    try:
        import yaml
    except ImportError:
        yaml = None

    bad = []
    for name in changed:
        text = paths[name].read_text(encoding='utf-8')
        fm = FRONTMATTER.match(text)
        if fm is None:
            bad.append((name, 'frontmatter no longer matches --- ... ---'))
            continue
        line = re.search(r'^description:[^\r\n]*', text, re.M)
        value = line.group(0).split(':', 1)[1].strip().strip('"') if line else ''
        if not value or len(value) > BAR:
            bad.append((name, 'description line missing or over the bar'))
        if yaml is not None:
            try:
                data = yaml.safe_load(fm.group(1)) or {}
                if data.get('name') != name:
                    bad.append((name, 'frontmatter name is now %r' % data.get('name')))
            except Exception as exc:
                bad.append((name, 'frontmatter does not parse: %s' % exc))

    print('changed: %d' % len(changed))
    for n in changed:
        print('   ', n)
    for n, why in skipped:
        print('SKIP %s - %s' % (n, why))
    if bak_path:
        print('originals (revert source): %s' % bak_path)
    if yaml is None:
        print('NOTE pyyaml unavailable: only line-level checks ran')
    for n, why in bad:
        print('FAIL %s - %s' % (n, why))
    print('verification: %d/%d edited files clean' % (len(changed) - len(bad), len(changed)))
    return 1 if (bad or skipped) else 0


if __name__ == '__main__':
    sys.exit(main())
