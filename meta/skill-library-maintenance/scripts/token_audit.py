#!/usr/bin/env python3
"""Skill-library token-cost audit (read-only).

Usage:  python token_audit.py [SKILLS_DIR]        # default: ~/.hermes/skills

Pass a NATIVE path (C:/Users/<user>/.hermes/skills) when invoking from git-bash: bash
expands ~ to /c/Users/..., which native Python resolves against the current drive and
finds nothing (reports 0 skills).

Prints:
  - index cost (name + description of every active skill) in tokens/turn
  - load cost = body_tokens * use_count, ranked (the bigger number, optimize first)
  - dead skills (0 uses, idle > 30d or never touched)
  - slimming candidates (body > 8 KB, > 35% tables/fenced code)
  - cross-skill duplication (8-line shingles shared by two or more skills)

Cost rule: chars / 4 ~ tokens (Hermes's own cheap rule; real tokenizers differ ~20%).
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.path.expanduser('~/.hermes/skills'))
ARCHIVE_DAYS, FAT_BYTES, DATA_PCT, K = 30, 8000, 35, 8

usage = {}
up = HOME / '.usage.json'
if up.is_file():
    try:
        usage = json.loads(up.read_text(encoding='utf-8'))
    except Exception:
        usage = {}


def parse(ts):
    try:
        d = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def last_activity(rec):
    """Real keys: last_used_at / last_viewed_at / last_patched_at.

    'last_activity_at' does NOT exist in .usage.json; reading it falls back to created_at
    and silently inflates every idle count.
    """
    stamps = [parse(rec.get(k)) for k in ('last_used_at', 'last_viewed_at', 'last_patched_at')]
    stamps = [s for s in stamps if s]
    return max(stamps) if stamps else None


def frontmatter(text):
    if not text.startswith('---'):
        return {}
    try:
        import yaml
        return yaml.safe_load(text.split('---', 2)[1]) or {}
    except Exception:
        return {}


def ref_bytes(sdir):
    total = 0
    for f in sdir.rglob('*'):
        try:
            if f.is_file() and f.name != 'SKILL.md':
                total += f.stat().st_size
        except OSError:
            continue  # broken junction / reparse point (WinError 1920)
    return total


now = datetime.now(timezone.utc)
rows = []

# The loader prunes a skill's progressive-disclosure dirs (references/templates/assets/scripts)
# from its index walk, so a SKILL.md nested under one is never offered and costs no index line.
# rglob sees it anyway: without this filter the index total is inflated by every folded pack.
SUPPORT_DIRS = {'references', 'templates', 'assets', 'scripts'}
EXCLUDED_DIRS = {'.git', '.github', '.hub', '.archive', '.curator_backups', '.locks',
                 '.venv', 'venv', 'node_modules', 'site-packages', '__pycache__',
                 '.tox', '.nox', '.pytest_cache', '.mypy_cache', '.ruff_cache'}


def indexed(md):
    parts = md.parts
    if any(p in EXCLUDED_DIRS for p in parts):
        return False
    return not any(p in SUPPORT_DIRS for p in parts[:-1])


for md in HOME.rglob('SKILL.md'):
    if not indexed(md):
        continue
    try:
        if not md.is_file():
            continue
        text = md.read_text(encoding='utf-8', errors='replace')
    except OSError:
        continue
    meta = frontmatter(text)
    name = str(meta.get('name') or md.parent.name)
    desc = str(meta.get('description') or '')
    rec = usage.get(name) or {}
    anchor = last_activity(rec) or parse(rec.get('created_at'))
    body = text.split('---', 2)[-1]
    data = sum(len(b) for b in re.findall(r'```.*?```', body, re.S))
    data += sum(len(l) + 1 for l in body.splitlines() if l.strip().startswith('|'))
    rows.append(dict(name=name, index_chars=len(name) + len(desc), body_bytes=len(text),
                     refs_bytes=ref_bytes(md.parent), uses=int(rec.get('use_count', 0) or 0),
                     idle=None if anchor is None else (now - anchor).days,
                     data_pct=100 * data / max(1, len(body)), state=rec.get('state')))

def rendered_index_chars():
    """The skills block that actually loads each turn (indentation + boilerplate included).

    The field sum below counts name+description only, so it understates the real cost by the
    per-line indent, the surrounding guidance text, and any skill the loader hides by condition
    (apps/environment/platform). Import the real builder when the Hermes package is reachable;
    otherwise say so instead of presenting the smaller number as the per-turn cost.
    """
    try:
        repo = Path(os.environ.get('LOCALAPPDATA', '')) / 'hermes' / 'hermes-agent'
        if repo.is_dir() and str(repo) not in sys.path:
            sys.path.insert(0, str(repo))
        import contextlib
        import io as _io
        from agent.prompt_builder import build_skills_system_prompt
        # the import and the build both print config warnings on stdout; keep them out of the report
        with contextlib.redirect_stdout(_io.StringIO()), contextlib.redirect_stderr(_io.StringIO()):
            return len(build_skills_system_prompt())
    except Exception:
        return None


idx = sum(r['index_chars'] for r in rows) + 2 * len(rows)
rendered = rendered_index_chars()
print('skills dir: %s' % HOME)
print('active skills: %d' % len(rows))
print('index fields (name+description, no formatting): %d chars ~ %d tokens' % (idx, idx / 4))
if rendered:
    print('rendered skills block (what loads per turn): %d chars ~ %d tokens/turn (x1000 turns = %d tokens)'
          % (rendered, rendered / 4, rendered / 4 * 1000))
else:
    print('rendered skills block: not measured (needs the Hermes package importable; run with its venv python)')
print('bodies: %d bytes (~%d tokens if every skill were loaded once); references: %d bytes (lazy)'
      % (sum(r['body_bytes'] for r in rows), sum(r['body_bytes'] for r in rows) / 4,
         sum(r['refs_bytes'] for r in rows)))

print('\n=== load cost = body_tokens * uses (rank FIRST) ===')
print('%-42s %7s %5s %6s %9s' % ('skill', 'bodytok', 'uses', 'idle', 'spent_est'))
for r in sorted(rows, key=lambda r: -(r['body_bytes'] / 4 * r['uses']))[:20]:
    print('%-42s %7d %5d %6s %9d' % (r['name'][:42], r['body_bytes'] / 4, r['uses'],
                                     r['idle'] if r['idle'] is not None else '-',
                                     r['body_bytes'] / 4 * r['uses']))

dead = [r for r in rows if r['uses'] == 0 and (r['idle'] is None or r['idle'] > ARCHIVE_DAYS)]
print('\n=== dead (0 uses, idle > %dd or never): %d skills, %d index chars = %d tokens/turn ==='
      % (ARCHIVE_DAYS, len(dead), sum(r['index_chars'] for r in dead),
         sum(r['index_chars'] for r in dead) / 4))
for r in sorted(dead, key=lambda r: -r['index_chars'])[:15]:
    print('   %-44s idxch=%-4d idle=%-5s state=%s' % (
        r['name'][:44], r['index_chars'], r['idle'] if r['idle'] is not None else '-', r['state']))

fat = [r for r in rows if r['body_bytes'] > FAT_BYTES and r['data_pct'] > DATA_PCT]
print('\n=== slimming candidates (body > %dB, > %d%% tables/code): %d ==='
      % (FAT_BYTES, DATA_PCT, len(fat)))
for r in sorted(fat, key=lambda r: -r['body_bytes'])[:15]:
    print('   %-44s body=%6dB (%5d tok) data=%2.0f%% uses=%d' % (
        r['name'][:44], r['body_bytes'], r['body_bytes'] / 4, r['data_pct'], r['uses']))


def norm(line):
    line = re.sub(r'^\s*[-*#>|\d.]+\s*', '', line)
    return re.sub(r'\s+', ' ', line).strip().lower()


shingles = {}
for md in HOME.rglob('SKILL.md'):
    if '.archive' in md.parts:
        continue
    try:
        body = md.read_text(encoding='utf-8', errors='replace').split('---', 2)[-1]
    except OSError:
        continue
    lines = [norm(l) for l in body.splitlines()]
    lines = [l for l in lines if len(l) > 3 and not l.startswith('```')]
    shingles[md.parent.name] = {tuple(lines[i:i + K]) for i in range(len(lines) - K + 1)}

names = sorted(shingles)
print('\n=== cross-skill duplication (>=3 shared %d-line blocks) ===' % K)
hits = 0
for i, a in enumerate(names):
    for b in names[i + 1:]:
        n = len(shingles[a] & shingles[b])
        if n >= 3:
            hits += 1
            print('   %3d blocks (%d lines)  %s <-> %s' % (n, n + K - 1, a, b))
if not hits:
    print('   none (expected: this is rarely a real waste class)')
