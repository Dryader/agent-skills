#!/usr/bin/env python3
"""Post-cull integrity audit for a skills repo. READ-ONLY — never modifies the repo.

Usage:
  python3 post_cull_audit.py <repo> \
      [--culled a,b,c|@file] [--trimmed a.md,b.md|@file] [--allowed x,y|@file] \
      [--expect-skills N] [--expect-files N] [--expect-single-commit] \
      [--exempt1 @file] [--exempt2 @file]

--culled     : skill names that were deleted in the cull (comma list or @file, one per line)
--trimmed    : reference files that were deleted (filenames)
--allowed    : bundled skill names that related_skills may legitimately name
--exempt1    : operator-reviewed false positives for check 1, lines "path:line:ref"
--exempt2    : operator-reviewed false positives for check 2, lines "path:line:name"
Exempted hits are PRINTED as 'EXEMPT (reviewed)' — evidence stays visible, verdict stays honest.

Seven checks: (1) references/scripts/templates path resolution from SKILL.md root,
(2) culled names as loadable targets, (3) trimmed file references, (4) frontmatter
name/description/related_skills, (5) hygiene (empty dirs, stray files), (6) README
claims vs tree, (7) git state (1 commit + clean tree after a PII history wipe).
"""
import os, re, sys, subprocess, fnmatch, argparse

TEXT_EXTS = {'.md','.py','.sh','.ps1','.yaml','.yml','.json','.txt','.csv','.toml',
             '.cfg','.conf','.ini','.rst','.html','.js','.ts','.sql'}
SCAN1_EXTS = {'.md','.py','.sh','.ps1'}

PROV_KWS = ['former','absorb','merg','cull','prun','remov','previous','histor','provenance',
            'supersed','replac','legac','delet','retir','dropped','no longer','not in this repo',
            'not part','out of scope','exclud','gone','withdrawn',' was ']
LOAD_KWS = ['related_skills','skill_view','skill','see ','load ','use the','reference','path',
            'import','scripts','templates','install','copy']

def read_list(arg):
    if not arg:
        return []
    if arg.startswith('@'):
        with open(arg[1:]) as f:
            return [l.strip() for l in f if l.strip()]
    return [x.strip() for x in arg.split(',') if x.strip()]

def read_exempts(arg):
    """Return set of (path, line:int, ref) tuples from 'path:line:ref' lines."""
    out = set()
    for l in read_list(arg):
        parts = l.split(':', 2)
        if len(parts) == 3:
            try:
                out.add((parts[0], int(parts[1]), parts[2]))
            except ValueError:
                pass
    return out

def walk_files(root):
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != '.git']
        for fn in fns:
            out.append(os.path.join(dp, fn))
    return out

def skill_root_for(path):
    d = os.path.dirname(path)
    while True:
        if os.path.exists(os.path.join(d, 'SKILL.md')):
            return d
        p = os.path.dirname(d)
        if p == d:
            return None
        d = p

def read_lines(p):
    try:
        with open(p, 'r', encoding='utf-8', errors='replace') as f:
            return f.read().splitlines()
    except Exception:
        return []

# ---------- CHECK 1 ----------
FWD_RE = re.compile(r'(?<![A-Za-z0-9_./\\:~$\-])((?:\.\./)*(?:\./)?(?:references|scripts|templates)/[A-Za-z0-9_.\-*]+)')
BS_RE  = re.compile(r'(?<![A-Za-z0-9_./\\:~$\-])((?:\.\.?\\)*(?:references|scripts|templates)\\[A-Za-z0-9_.\-*]+)')

def resolve(ref, skill_root, file_dir, all_files):
    ref2 = ref.replace('\\', '/')
    if ref2.startswith('../'):
        base = file_dir
        rel = ref2
    else:
        base = skill_root
        rel = ref2.lstrip('./')
    cand = os.path.normpath(os.path.join(base, rel))
    if '*' in cand:
        return any(fnmatch.fnmatch(f, cand) or
                   fnmatch.fnmatch(os.path.relpath(f, os.path.dirname(cand)), os.path.basename(cand))
                   for f in all_files)
    return os.path.exists(cand)

def check1(root, all_files, exempt1):
    misses, n_cand, scanned = [], 0, 0
    for f in all_files:
        if os.path.splitext(f)[1] not in SCAN1_EXTS:
            continue
        sroot = skill_root_for(f)
        if sroot is None:
            continue
        scanned += 1
        fdir = os.path.dirname(f)
        for i, line in enumerate(read_lines(f), 1):
            for m in list(FWD_RE.finditer(line)) + list(BS_RE.finditer(line)):
                n_cand += 1
                ref = m.group(1).rstrip('.')
                if not resolve(ref, sroot, fdir, all_files):
                    misses.append((f, i, ref))
    real = [m for m in misses if m not in exempt1]
    return real, [m for m in misses if m in exempt1], n_cand, scanned

# ---------- CHECK 2 ----------
def expand_token(line, m):
    s, e = m.start(), m.end()
    while s > 0 and line[s-1] in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._~:/?#@!$&'()*+,;=%-":
        s -= 1
    while e < len(line) and line[e] in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._~:/?#@!$&'()*+,;=%-":
        e += 1
    return line[s:e]

def is_url_context(tok):
    return '://' in tok or bool(re.match(r'^[A-Za-z0-9.-]+\.[a-z]{2,}(/|$)', tok))

def is_live_env_path(tok):
    return tok.startswith('~/') or '~/.hermes' in tok

def classify(line, name, m):
    low = line.lower()
    if any(k in low for k in PROV_KWS):
        return 'OK'
    has_load = any(k in low for k in LOAD_KWS)
    bt = (m.start() > 0 and line[m.start()-1] == '`') or (m.end() < len(line) and line[m.end()] == '`')
    pathlike = (m.end() < len(line) and line[m.end()] == '/') or \
               (m.start() >= 3 and line[m.start()-3:m.start()] == '../')
    if has_load or bt or pathlike:
        return 'FAIL'
    return 'REVIEW'

def check2(root, all_files, culled, exempt2):
    hits = []  # (file, line, name, class, snippet)
    for f in all_files:
        if os.path.splitext(f)[1] not in TEXT_EXTS:
            continue
        for i, line in enumerate(read_lines(f), 1):
            for name in culled:
                pat = re.compile(r'(?<![a-z0-9-])' + re.escape(name) + r'(?![a-z0-9-])', re.IGNORECASE)
                for m in pat.finditer(line):
                    tok = expand_token(line, m)
                    if is_url_context(tok):
                        continue
                    if is_live_env_path(tok):
                        hits.append((f, i, name, 'EXEMPT', line.strip()[:160]))
                        continue
                    if (f, i, name) in exempt2:
                        hits.append((f, i, name, 'EXEMPT', line.strip()[:160]))
                        continue
                    hits.append((f, i, name, classify(line, name, m), line.strip()[:160]))
    return hits

# ---------- CHECK 3 ----------
def check3(root, all_files, trimmed):
    hits = []
    stems = [t[:-3] for t in trimmed]
    for f in all_files:
        if os.path.splitext(f)[1] not in TEXT_EXTS:
            continue
        for i, line in enumerate(read_lines(f), 1):
            low = line.lower()
            for stem, full in zip(stems, trimmed):
                if full in low:
                    hits.append((f, i, full, line.strip()[:160]))
                    continue
                if re.search(r'(?<![a-z0-9-])' + re.escape(stem) + r'(?![a-z0-9-])', low):
                    hits.append((f, i, stem + '.md', line.strip()[:160]))
    ondisk = [f for f in all_files if os.path.basename(f) in trimmed]
    return hits, ondisk

# ---------- CHECK 4 ----------
def check4(skill_dirs, skill_names, culled, allowed):
    probs = []
    try:
        import yaml
    except ImportError:
        probs.append('pyyaml not installed — frontmatter checks skipped')
        return probs
    for sd in sorted(skill_dirs):
        name = os.path.basename(sd)
        sk = os.path.join(sd, 'SKILL.md')
        lines = read_lines(sk)
        if not lines or lines[0].strip() != '---':
            probs.append(f'{sk}:1: missing frontmatter delimiter')
            continue
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == '---'), None)
        if end is None:
            probs.append(f'{sk}:1: unterminated frontmatter')
            continue
        try:
            fm = yaml.safe_load('\n'.join(lines[1:end]))
        except Exception as e:
            probs.append(f'{sk}:1: yaml parse error: {e}')
            continue
        if not isinstance(fm, dict):
            probs.append(f'{sk}:1: frontmatter not a mapping')
            continue
        if fm.get('name') != name:
            ln = next((i for i, l in enumerate(lines, 1) if l.strip().startswith('name:')), 1)
            probs.append(f'{sk}:{ln}: name {fm.get("name")!r} != folder {name!r}')
        if not str(fm.get('description') or '').strip():
            ln = next((i for i, l in enumerate(lines, 1) if l.strip().startswith('description:')), 1)
            probs.append(f'{sk}:{ln}: missing/empty description')
        rs = fm.get('related_skills') or []
        if isinstance(rs, str):
            rs = [x.strip() for x in re.split(r'[,\s]+', rs) if x.strip()]
        for ent in rs:
            if not isinstance(ent, str):
                probs.append(f'{sk}: related_skills entry not a string: {ent!r}')
                continue
            e2 = re.sub(r'^(plugin|superpowers|community):', '', ent.strip()).lower()
            if e2 in culled:
                ln = next((i for i, l in enumerate(lines, 1) if ent.strip().split(':')[-1].strip() in l), 1)
                probs.append(f'{sk}:{ln}: related_skills references CULLED skill {ent!r}')
            elif e2 not in skill_names and e2 not in allowed:
                ln = next((i for i, l in enumerate(lines, 1) if ent.strip().split(':')[-1].strip() in l), 1)
                probs.append(f'{sk}:{ln}: related_skills {ent!r} neither in-repo nor allowed bundled')
    return probs

# ---------- CHECK 5 ----------
def check5(root):
    strays, empties = [], []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != '.git']
        if not dns and not fns:
            empties.append(dp)
            continue
        for d in dns:
            if d == '__pycache__' or d == 'node_modules' or d.startswith('.curator'):
                strays.append(os.path.join(dp, d))
        for fn in fns:
            if fn in ('.usage.json', '.DS_Store') or fn.startswith('.curator') or fn.endswith('.pyc'):
                strays.append(os.path.join(dp, fn))
    return strays, empties

# ---------- CHECK 6 ----------
def check6(root, all_files, skill_dirs, cat_map, expect_skills, expect_files):
    probs = []
    readme = os.path.join(root, 'README.md')
    if not os.path.exists(readme):
        return ['README.md missing'], {}
    text = open(readme, encoding='utf-8', errors='replace').read()
    lines = text.splitlines()
    actual_skills = {os.path.basename(s) for s in skill_dirs}
    if expect_skills and len(actual_skills) != expect_skills:
        probs.append(f'actual skill count {len(actual_skills)} != expected {expect_skills}')
    if expect_files and len(all_files) != expect_files:
        probs.append(f'actual file count {len(all_files)} != expected {expect_files}')
    if expect_skills and f'{expect_skills} skills' not in text:
        probs.append(f'README lacks "{expect_skills} skills" claim')
    if expect_files and f'{expect_files} files' not in text:
        probs.append(f'README lacks "{expect_files} files" claim')
    cats, cur = {}, None
    for i, l in enumerate(lines, 1):
        m = re.match(r'^### ([a-z0-9-]+) \((\d+)\)\s*$', l)
        if m:
            cur = m.group(1)
            cats[cur] = {'count': int(m.group(2)), 'line': i, 'skills': None}
            continue
        if cur and cats[cur]['skills'] is None and l.strip():
            cats[cur]['skills'] = [s.strip() for s in l.split(',') if s.strip()]
            cur = None
    listed = set()
    for cname, info in cats.items():
        if info['skills'] is None:
            probs.append(f'README:{info["line"]}: category {cname} has no skill list')
            continue
        if len(info['skills']) != info['count']:
            probs.append(f'README:{info["line"]}: {cname} header says ({info["count"]}) but lists {len(info["skills"])}')
        actual = cat_map.get(cname, set())
        if set(info['skills']) != actual:
            probs.append(f'README:{info["line"]}: {cname} mismatch README={info["skills"]} actual={sorted(actual)}')
        listed |= set(info['skills'])
    if listed != actual_skills:
        probs.append(f'README union mismatch only-in-readme={sorted(listed-actual_skills)} only-in-repo={sorted(actual_skills-listed)}')
    return probs, cats

# ---------- CHECK 7 ----------
def check7(root, expect_single_commit):
    probs = []
    n = subprocess.run(['git', '-C', root, 'rev-list', '--count', 'HEAD'], capture_output=True, text=True)
    cnt = n.stdout.strip()
    if expect_single_commit and cnt != '1':
        probs.append(f'commit count = {cnt!r}, expected 1 (history was wiped for PII)')
    st = subprocess.run(['git', '-C', root, 'status', '--porcelain'], capture_output=True, text=True)
    if st.stdout.strip():
        probs.append(f'working tree not clean:\n{st.stdout.strip()}')
    return probs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo')
    ap.add_argument('--culled', default='')
    ap.add_argument('--trimmed', default='')
    ap.add_argument('--allowed', default='')
    ap.add_argument('--expect-skills', type=int, default=0)
    ap.add_argument('--expect-files', type=int, default=0)
    ap.add_argument('--expect-single-commit', action='store_true')
    ap.add_argument('--exempt1', default='')
    ap.add_argument('--exempt2', default='')
    a = ap.parse_args()

    culled = read_list(a.culled)
    trimmed = read_list(a.trimmed)
    allowed = {x.lower() for x in read_list(a.allowed)}
    exempt1 = read_exempts(a.exempt1)
    exempt2 = read_exempts(a.exempt2)

    all_files = walk_files(a.repo)
    skill_dirs = [os.path.dirname(f) for f in all_files if os.path.basename(f) == 'SKILL.md']
    skill_names = {os.path.basename(s) for s in skill_dirs}
    cat_map = {}
    for sd in skill_dirs:
        cat_map.setdefault(os.path.basename(os.path.dirname(sd)), set()).add(os.path.basename(sd))

    print(f'AUDIT: {a.repo}')
    print(f'skills={len(skill_dirs)} files={len(all_files)}')

    # 1
    real1, ex1, n_cand, scanned = check1(a.repo, all_files, exempt1)
    print(f'\n===== CHECK 1: path resolution =====\n{"PASS" if not real1 else "FAIL"} ({scanned} files, {n_cand} candidates)')
    for f, i, ref in real1: print(f'  MISS {f}:{i}: {ref}')
    for f, i, ref in ex1: print(f'  EXEMPT (reviewed) {f}:{i}: {ref}')

    # 2
    hits = check2(a.repo, all_files, culled, exempt2)
    fails = [h for h in hits if h[3] == 'FAIL']
    revs = [h for h in hits if h[3] == 'REVIEW']
    oks = [h for h in hits if h[3] == 'OK']
    ex2 = [h for h in hits if h[3] == 'EXEMPT']
    v2 = 'FAIL' if fails else ('REVIEW' if revs else 'PASS')
    print(f'\n===== CHECK 2: culled names =====\n{v2} ({len(hits)} mentions: {len(fails)} FAIL, {len(revs)} REVIEW, {len(oks)} provenance-OK, {len(ex2)} exempt)')
    for f, i, name, cls, snip in fails + revs + oks + ex2:
        print(f'  [{cls}] {f}:{i}: ({name}) {snip}')

    # 3
    hits3, ondisk = check3(a.repo, all_files, trimmed)
    print(f'\n===== CHECK 3: trimmed files =====\n{"PASS" if not hits3 and not ondisk else "FAIL"}')
    for f, i, full, snip in hits3: print(f'  REF {f}:{i}: {full} | {snip}')
    for f in ondisk: print(f'  ON-DISK (should not exist): {f}')

    # 4
    probs4 = check4(skill_dirs, skill_names, culled, allowed)
    print(f'\n===== CHECK 4: frontmatter =====\n{"PASS" if not probs4 else "FAIL"}')
    for p in probs4: print(f'  {p}')

    # 5
    strays, empties = check5(a.repo)
    print(f'\n===== CHECK 5: hygiene =====\n{"PASS" if not strays and not empties else "FAIL"}')
    for s in strays: print(f'  STRAY {s}')
    for e in empties: print(f'  EMPTY {e}')

    # 6
    probs6, cats = check6(a.repo, all_files, skill_dirs, cat_map, a.expect_skills, a.expect_files)
    print(f'\n===== CHECK 6: README =====\n{"PASS" if not probs6 else "FAIL"} ({len(cats)} categories)')
    for p in probs6: print(f'  {p}')

    # 7
    probs7 = check7(a.repo, a.expect_single_commit)
    print(f'\n===== CHECK 7: git state =====\n{"PASS" if not probs7 else "FAIL"}')
    for p in probs7: print(f'  {p}')

    ok = not real1 and not fails and not revs and not hits3 and not ondisk and not probs4 \
         and not strays and not empties and not probs6 and not probs7
    print(f'\nOVERALL: {"PASS" if ok else "FAIL"}')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
