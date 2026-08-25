#!/usr/bin/env python3
"""Audit the Hermes session corpus to answer the pain-inventory gates for
"would a memory provider / tool be worth it?" questions.

Measures:
- corpus size, time span, source mix (cli vs subagent vs acp)
- how often user messages reference PRIOR sessions (cross-session recall need)
- how often user messages complain about forgotten context (re-explanation)

Usage: python3 session_corpus_audit.py [path-to-state.db]
Default: ~/.hermes/state.db

Baseline measured Aug 2026 (user corpus): a corpus spanning months of
sessions; recall and complaint phrases in a small fraction of sessions —
far below the pain threshold for adopting a memory system.
"""
import sqlite3, os, sys, datetime
from collections import Counter

def main():
    db = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else '~/.hermes/state.db')
    sz = os.path.getsize(db)//1024 if os.path.exists(db) else 0
    print('db:', db, '| exists:', os.path.exists(db), '| size:', sz, 'KB')
    con = sqlite3.connect(db)
    rows = con.execute('SELECT started_at, title, source FROM sessions ORDER BY started_at').fetchall()
    if not rows:
        print('no sessions found'); return
    print('sessions:', len(rows))
    print('span:', datetime.datetime.fromtimestamp(rows[0][0]).isoformat(),
          '->', datetime.datetime.fromtimestamp(rows[-1][0]).isoformat())
    years = Counter(datetime.datetime.fromtimestamp(r[0]).year for r in rows)
    print('sessions/year:', dict(sorted(years.items())))
    print('by source:', dict(Counter(r[2] for r in rows)))
    titled = [r[1] for r in rows if r[1]]
    print('titled:', len(titled), '/', len(rows))
    if titled:
        print('recent titles:', titled[-8:])
    print('messages:', con.execute('SELECT COUNT(*) FROM messages').fetchone()[0],
          '| user msgs:', con.execute("SELECT COUNT(*) FROM messages WHERE role='user'").fetchone()[0])

    recall_phrases = ['we discussed', 'we talked', 'as we said', 'as i said',
                      'previous discussion', 'earlier we', 'remember when',
                      'last time we', 'in our previous', 'you said before',
                      'we agreed', 'we decided', 'what did we', 'why did we']
    complaint_phrases = ['you forgot', 'i told you', 'i already said',
                         'i already told', 'you keep asking', 'did you forget',
                         'we went over', 'i explained', 'you should know',
                         "you don't remember", 'wrong again']
    for label, phrases in [('CROSS-SESSION RECALL', recall_phrases),
                           ('RE-EXPLANATION COMPLAINTS', complaint_phrases)]:
        hits, sess = Counter(), set()
        for sid, content in con.execute("SELECT session_id, content FROM messages WHERE role='user'"):
            if not content:
                continue
            low = content.lower()
            for p in phrases:
                if p in low:
                    hits[p] += 1
                    sess.add(sid)
        print(f'--- {label}: {sum(hits.values())} messages across {len(sess)} sessions')
        for p, c in hits.most_common():
            if c:
                print(f'    {p}: {c}')

if __name__ == '__main__':
    main()
