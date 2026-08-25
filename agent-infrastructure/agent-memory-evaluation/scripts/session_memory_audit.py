"""Audit ~/.hermes/state.db to decide whether an external memory provider is warranted.
Counts sessions/messages, scans user messages for cross-session recall phrases and
re-explanation complaints. Verdict rule: <3 concrete recall-need sessions in the
corpus (or none since the last audit) => no provider needed; re-check later.

Usage: python3 session_memory_audit.py [path-to-state.db]
"""
import sqlite3
import os
import sys
from collections import Counter

DB = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else '~/.hermes/state.db')

RECALL_PHRASES = [
    'we discussed', 'we talked', 'as we said', 'as i said', 'previous discussion',
    'earlier we', 'remember when', 'last time we', 'in our previous', 'you said before',
    'we agreed', 'we decided', 'what did we', 'why did we', 'our previous discussions',
]
COMPLAINT_PHRASES = [
    'you forgot', 'i told you', 'i already said', 'i already told', 'you keep asking',
    'did you forget', 'you asked me before', 'we went over', 'i explained',
    'you should know', 'you dont remember', "you don't remember", 'wrong again',
]

con = sqlite3.connect(DB)
rows = con.execute('SELECT started_at, title, source FROM sessions ORDER BY started_at').fetchall()
import datetime
if rows:
    print(f'corpus span: {datetime.datetime.fromtimestamp(rows[0][0]).date()} -> '
          f'{datetime.datetime.fromtimestamp(rows[-1][0]).date()}')
print(f'sessions: {len(rows)}')
print('by source:', dict(Counter(r[2] for r in rows)))
print('titled sessions:', sum(1 for r in rows if r[1]), '/', len(rows))
for r in rows[-5:]:
    if r[1]:
        print(f'  recent title: {r[1]}')

msgs = con.execute("SELECT session_id, content FROM messages WHERE role='user'").fetchall()
print(f'user messages: {len(msgs)}')

recall_hits, recall_sess = Counter(), set()
complaint_hits, complaint_sess = Counter(), set()
for sid, content in msgs:
    if not content:
        continue
    low = content.lower()
    for p in RECALL_PHRASES:
        if p in low:
            recall_hits[p] += 1
            recall_sess.add(sid)
    for p in COMPLAINT_PHRASES:
        if p in low:
            complaint_hits[p] += 1
            complaint_sess.add(sid)

print(f'\ncross-session recall phrases: {sum(recall_hits.values())} hits in '
      f'{len(recall_sess)} distinct sessions')
for p, c in recall_hits.most_common():
    if c:
        print(f'  {p}: {c}')
print(f're-explanation complaints: {sum(complaint_hits.values())} hits in '
      f'{len(complaint_sess)} distinct sessions (read "again?" as re-run, not forget)')
for p, c in complaint_hits.most_common():
    if c:
        print(f'  {p}: {c}')

print('\nVERDICT heuristic:')
print(f'  recall-need sessions: {len(recall_sess)} '
      f'({len(recall_sess) / max(len(rows), 1) * 100:.1f}% of sessions)')
if len(recall_sess) < 3:
    print('  -> pain inventory gate FAILS: no external memory provider warranted. '
          'Re-check when 3 real session_search failures are logged.')
else:
    print('  -> pain inventory gate PASSES: worth running the 30-day trial + contamination audit '
          '(see agent-memory-evaluation skill).')
