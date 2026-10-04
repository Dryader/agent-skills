#!/usr/bin/env python3
"""Catalogue accounting for a Hermes skills tree: provenance, cost, orphans, dead weight.

    python3 skill_inventory.py [skills_dir]

skills_dir defaults to ~/.hermes/skills. Read-only.

Prints, in order:
  1. library size and provenance split (bundled / hub / local)
  2. bundled skills whose bytes no longer match their manifest origin hash
     (user-modified -> sync skips them, so they stop receiving upstream fixes)
  3. catalogue cost: name+description chars over every active skill, as ~tokens
  4. descriptions over the 60-char authoring bar, longest first
  5. manifest rows with no file on disk (removed upstream / archived), which is how
     an upstream removal leaves an orphan behind
  6. skills no session has ever loaded (use_count and view_count both zero)
  7. rows without created_by=agent, which the curator will never stale-detect

Interpretation notes are printed with each block so a future session does not have to
re-derive the sync and curator rules from source.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

BAR = 60


def dir_hash(directory: Path) -> str:
    """MD5 over (relative path, bytes) for every file, sorted. Mirrors
    tools/skills_sync.py::_dir_hash. A package carrying generated runtime cache
    files will not match its recorded origin hash — re-check before calling it edited."""
    hasher = hashlib.md5()
    for f in sorted(directory.rglob('*')):
        if f.is_file():
            hasher.update(str(f.relative_to(directory)).encode('utf-8'))
            hasher.update(f.read_bytes())
    return hasher.hexdigest()


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def read_manifest(skills: Path):
    """{.bundled_manifest is 'name:origin_hash' per line.}"""
    out = {}
    path = skills / '.bundled_manifest'
    if path.is_file():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                name, _, h = line.partition(':')
                out[name.strip()] = h.strip()
    return out


def description(skill_md: Path) -> str:
    """Frontmatter description, single-line or folded."""
    try:
        text = skill_md.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''
    m = re.search(r'^description:\s*(.+)$', text, re.M)
    if not m:
        return ''
    raw = m.group(1).strip()
    if raw in ('|', '>', '|-', '>-', '|+', '>+'):
        m2 = re.search(r'^description:\s*[|>][^\n]*\n((?:[ \t]+[^\n]*\n)+)', text, re.M)
        return ' '.join(line.strip() for line in m2.group(1).splitlines()) if m2 else ''
    return raw.strip('"').strip("'")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('skills_dir', nargs='?', default=os.path.expanduser('~/.hermes/skills'))
    args = ap.parse_args()
    skills = Path(args.skills_dir).expanduser()
    if not skills.is_dir():
        print('not a directory: %s' % skills)
        return 2

    manifest = read_manifest(skills)
    hub = set(load_json(skills / '.hub' / 'lock.json', {}).get('installed', {}))
    usage = load_json(skills / '.usage.json', {})

    active, archived = {}, {}
    for md in skills.rglob('SKILL.md'):
        rel = md.relative_to(skills).as_posix()
        (archived if rel.startswith('.archive/') else active)[md.parent.name] = md

    rows, total = [], 0
    for name, md in active.items():
        src = 'bundled' if name in manifest else ('hub' if name in hub else 'local')
        origin = ''
        if src == 'bundled':
            origin = 'clean' if dir_hash(md.parent) == manifest[name] else 'MODIFIED (updates skipped)'
        desc = description(md)
        total += len(name) + len(desc)
        u = usage.get(name, {})
        rows.append(dict(name=name, desc=desc, src=src, origin=origin,
                         use=u.get('use_count', 0), view=u.get('view_count', 0),
                         created_by=u.get('created_by')))

    print('library      : %d active, %d archived' % (len(active), len(archived)))
    print('provenance   : %d bundled, %d hub, %d local' % (
        sum(1 for r in rows if r['src'] == 'bundled'),
        sum(1 for r in rows if r['src'] == 'hub'),
        sum(1 for r in rows if r['src'] == 'local')))

    print('\ncatalogue cost: %d chars of name+description (~%d tokens) across %d skills'
          % (total, total // 4, len(rows)))
    print('  rides the cached prefix: context every turn plus a full re-send on each cache write')
    over = [r for r in rows if len(r['desc']) > BAR]
    print('  descriptions over the %d-char bar: %d' % (BAR, len(over)))
    for r in sorted(over, key=lambda r: -len(r['desc']))[:10]:
        print('    %4d  %s' % (len(r['desc']), r['name']))

    modified = sorted(r['name'] for r in rows if r['origin'].startswith('MODIFIED'))
    print('\nbundled but user-modified (frozen from upstream updates): %d' % len(modified))
    for n in modified:
        print('   ', n)
    if modified:
        print('    see with `hermes skills list-modified`, revert with `hermes skills reset <name>`')

    gone = sorted(n for n in manifest if n not in active)
    print('\nmanifest rows with no active file: %d' % len(gone))
    for n in gone:
        print('    %-38s %s' % (n, 'archived' if n in archived else 'MISSING'))
    if gone:
        print('    an upstream removed skill leaves its file behind: sync drops the manifest row')
        print('    and never deletes from the user tree, so the orphan can trail its successor.')
        print('    history: commits?path=skills/<cat>/<skill>/SKILL.md on the repo API')

    local_only = sorted(n for n, md in active.items() if n not in manifest and n not in hub)
    print('\nlocally owned (neither manifest nor hub): %d' % len(local_only))

    dead = sorted(r['name'] for r in rows if not r['use'] and not r['view'])
    print('\nnever loaded (use_count and view_count both 0): %d' % len(dead))
    print('   ', ', '.join(dead) if dead else '-')

    unmanaged = sorted(r['name'] for r in rows if r['created_by'] != 'agent')
    print('\nwithout created_by=agent (curator never stale-detects these): %d' % len(unmanaged))
    print('    keep live: `hermes curator adopt <name>`   retire: `hermes curator archive <name>`')
    return 0


if __name__ == '__main__':
    sys.exit(main())
