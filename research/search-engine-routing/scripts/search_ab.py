#!/usr/bin/env python3
"""5-engine search A/B harness (Exa, Parallel, Tavily, Firecrawl, Brave).

Usage:
  python3 search_ab.py queries.txt [--n 10] [--engines exa,parallel,tavily,firecrawl,brave]
                                   [--answers answers.json] [--out /tmp/ab_out]

queries.txt: one query per line.
answers.json (optional): {"0": ["substring", ...]} keyed by query line index.
Keys are read from ~/.hermes/.env (EXA_API_KEY, TAVILY_API_KEY, FIRECRAWL_API_KEY,
BRAVE_API_KEY, optional PARALLEL_API_KEY). Brave also falls back to
/mnt/c/Users/<user>/brave.env if the key is absent from ~/.hermes/.env.
Parallel falls back to anonymous MCP if no key.
Firecrawl is paced 35s/call (free tier 10 req/min) and retries 429 once.
A missing required key aborts that engine with a clear error.
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error

ENV_PATH = os.path.expanduser("~/.hermes/.env")

def env_key(name):
    try:
        env = open(ENV_PATH).read()
    except OSError:
        return None
    m = re.search(rf'{name}=["\']?([^"\'\n]+)', env)
    return m.group(1) if m else None

def post(url, body, headers, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode()), time.perf_counter() - t0, None
    except urllib.error.HTTPError as e:
        return {}, time.perf_counter() - t0, f"HTTP {e.code}: {e.read().decode()[:200]}"

# ---------- Exa ----------
def exa_search(query, n):
    key = env_key("EXA_API_KEY")
    if not key:
        return [], 0.0, "missing EXA_API_KEY (set in ~/.hermes/.env)"
    out, dt, err = post("https://api.exa.ai/search",
        {"query": query, "numResults": n, "type": "auto", "contents": {"highlights": True}},
        {"Content-Type": "application/json", "x-api-key": key})
    items = [{"url": r.get("url", ""), "title": r.get("title", ""),
              "date": r.get("publishedDate"),
              "text": " ".join(r.get("highlights") or [])} for r in out.get("results", [])]
    return items, dt, err

# ---------- Parallel (MCP JSON-RPC, anonymous or Bearer) ----------
P_URL = "https://search.parallel.ai/mcp"
P_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
P_SID = None

def p_post(payload):
    global P_SID
    req = urllib.request.Request(P_URL, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    req.add_header("User-Agent", P_UA)
    pkey = env_key("PARALLEL_API_KEY")
    if pkey:
        req.add_header("Authorization", f"Bearer {pkey}")
    if P_SID:
        req.add_header("Mcp-Session-Id", P_SID)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            P_SID = resp.headers.get("Mcp-Session-Id") or P_SID
            body = resp.read().decode()
        dt = time.perf_counter() - t0
        if not body.strip():
            return {}, dt, None
        if body.lstrip().startswith("event:"):
            msgs = [json.loads(l[5:].strip()) for l in body.splitlines() if l.startswith("data:")]
            return msgs[-1], dt, None
        return json.loads(body), dt, None
    except urllib.error.HTTPError as e:
        return {}, time.perf_counter() - t0, f"HTTP {e.code}: {e.read().decode()[:200]}"

def parallel_search(query, n):
    if P_SID is None:
        p_post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "search-ab-harness", "version": "1.0"}}})
        p_post({"jsonrpc": "2.0", "method": "notifications/initialized"})
    r, dt, err = p_post({"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {
        "name": "web_search",
        "arguments": {"objective": query, "search_queries": [query]}}})
    if err:
        return [], dt, err
    try:
        inner = json.loads(r["result"]["content"][0]["text"])
    except Exception:
        return [], dt, "parse failure"
    items = [{"url": x.get("url", ""), "title": x.get("title", ""),
              "date": x.get("publish_date"),
              "text": " ".join(x.get("excerpts") or [])} for x in inner.get("results", [])]
    return items[:n], dt, None

# ---------- Tavily ----------
def tavily_search(query, n):
    key = env_key("TAVILY_API_KEY")
    if not key:
        return [], 0.0, "missing TAVILY_API_KEY (set in ~/.hermes/.env)"
    out, dt, err = post("https://api.tavily.com/search",
        {"api_key": key, "query": query, "max_results": n,
         "search_depth": "basic", "include_answer": False},
        {"Content-Type": "application/json"})
    items = [{"url": r.get("url", ""), "title": r.get("title", ""),
              "date": r.get("published_date"),
              "text": r.get("content") or ""} for r in out.get("results", [])]
    return items, dt, err

# ---------- Firecrawl (paced) ----------
FC_LAST = [0.0]
def firecrawl_search(query, n):
    key = env_key("FIRECRAWL_API_KEY")
    if not key:
        return [], 0.0, "missing FIRECRAWL_API_KEY (set in ~/.hermes/.env)"
    wait = 35 - (time.time() - FC_LAST[0])
    if wait > 0:
        time.sleep(wait)
    out, dt, err = post("https://api.firecrawl.dev/v1/search",
        {"query": query, "limit": n, "lang": "en"},
        {"Content-Type": "application/json",
         "Authorization": f"Bearer {key}"})
    FC_LAST[0] = time.time()
    if err and "429" in err:
        time.sleep(35)
        out, dt, err = post("https://api.firecrawl.dev/v1/search",
            {"query": query, "limit": n, "lang": "en"},
            {"Content-Type": "application/json",
             "Authorization": f"Bearer {key}"})
    web = out.get("data") or []
    if isinstance(web, dict):
        web = web.get("web") or []
    items = [{"url": r.get("url", ""), "title": r.get("title", ""),
              "date": None,
              "text": (r.get("description") or "") + " " + " ".join(r.get("highlights") or [])}
             for r in web]
    return items, dt, err

# ---------- Brave (REST web search API) ----------
def brave_search(query, n):
    import urllib.parse
    key = env_key("BRAVE_API_KEY")
    if not key:
        try:
            key = open("/mnt/c/Users/<user>/brave.env").read().strip()
        except OSError:
            key = None
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
        {"q": query, "count": n})
    req = urllib.request.Request(url, headers={
        "X-Subscription-Token": key or "", "Accept": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.loads(resp.read().decode())
        dt = time.perf_counter() - t0
        results = (out.get("web") or {}).get("results", [])
        items = [{"url": r.get("url", ""), "title": r.get("title", ""),
                  "date": r.get("age") or r.get("page_age"),
                  "text": r.get("description") or ""} for r in results]
        return items[:n], dt, None
    except urllib.error.HTTPError as e:
        return [], time.perf_counter() - t0, f"HTTP {e.code}: {e.read().decode()[:200]}"

ENGINES = {
    "exa": exa_search, "parallel": parallel_search,
    "tavily": tavily_search, "firecrawl": firecrawl_search,
    "brave": brave_search,
}

def jaccard(a, b):
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("queries_file")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--engines", default="exa,parallel,tavily,firecrawl")
    ap.add_argument("--answers", default=None)
    ap.add_argument("--out", default="/tmp/ab_out")
    args = ap.parse_args()

    queries = [l.strip() for l in open(args.queries_file) if l.strip()]
    if not queries:
        print('no queries found; nothing to compare')
        return
    engines = [e for e in args.engines.split(",") if e in ENGINES]
    os.makedirs(args.out, exist_ok=True)
    answers = json.load(open(args.answers)) if args.answers else {}

    results = {e: {} for e in engines}
    for qi, q in enumerate(queries):
        print(f"[{qi}] {q[:60]}")
        for e in engines:
            items, dt, err = ENGINES[e](q, args.n)
            results[e][qi] = {"items": items, "lat": dt, "err": err}
            json.dump(results[e][qi], open(f"{args.out}/{e}_{qi}.json", "w"))
            print(f"    {e:<9} {len(items):>2} res  {dt:.1f}s  {err or ''}")

    print("\n=== pairwise URL Jaccard (mean over queries) ===")
    names = list(engines)
    print("        " + "".join(f"{x[:6]:>9}" for x in names))
    for a in names:
        row = f"{a[:6]:<8}"
        for b in names:
            if a == b:
                row += f"{'--':>9}"
                continue
            m = sum(jaccard([x["url"] for x in results[a][q]["items"]],
                            [x["url"] for x in results[b][q]["items"]])
                    for q in range(len(queries))) / len(queries)
            row += f"{m*100:>8.0f}%"
        print(row)

    print("\n=== payload / latency / dates ===")
    for e in names:
        texts = [x["text"] for q in range(len(queries)) for x in results[e][q]["items"]]
        tot = sum(len(t) for t in texts)
        n = max(len(texts), 1)
        lats = [results[e][q]["lat"] for q in range(len(queries))]
        dated = sum(1 for q in range(len(queries)) for x in results[e][q]["items"] if x["date"])
        total = sum(len(results[e][q]["items"]) for q in range(len(queries)))
        print(f"  {e:<9} {n:>3} res, {tot/1000:>5.0f}KB, {tot/n:>5.0f} ch/res, "
              f"lat {sum(lats)/len(lats):.1f}s, dated {dated}/{total}")

    if answers:
        print("\n=== answer containment (top-3) ===")
        print("        " + "".join(f"{x[:6]:>9}" for x in names))
        for qi, subs in answers.items():
            qi = int(qi)
            row = f"q{qi:<6}"
            for e in names:
                blob = " ".join(x["text"] for x in results[e][qi]["items"][:3]).lower()
                row += f"{str(any(s.lower() in blob for s in subs)):>9}"
            print(row)

if __name__ == "__main__":
    main()
