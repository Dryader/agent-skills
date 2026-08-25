#!/usr/bin/env python3
"""Extract URL + head excerpt from persisted MCP search results.

Hermes persists oversized MCP tool results (>~50KB) to
/tmp/hermes-results/call_XX_*.txt, wrapped in <untrusted_tool_result>.
json.loads on the file body can raise "Extra data" because trailing
content follows the JSON object — use JSONDecoder.raw_decode instead.

Usage:
  python3 extract_persisted_mcp_results.py /tmp/hermes-results/call_00_*.txt [url_fragment] [maxchars]

Prints per result: URL, published date, author, first maxchars chars
(default 900) of body text with newlines flattened. Pass a url_fragment
(e.g. 'wavect') to print only results whose URL contains it.
"""

import json
import sys


def extract(path, url_frag=None, maxchars=900):
    raw = open(path, encoding="utf-8", errors="replace").read()
    idx = raw.find('{"result"')
    if idx == -1:
        sys.exit("No JSON result object found in %s" % path)
    # raw_decode tolerates trailing content after the JSON object
    data, _ = json.JSONDecoder().raw_decode(raw[idx:])
    inner = json.loads(data["result"])
    results = inner.get("results", [])
    print("results:", len(results))
    for r in results:
        if url_frag and url_frag not in r.get("url", ""):
            continue
        print("-" * 90)
        print("URL:", r.get("url"))
        print("DATE:", r.get("publishedDate"), "| AUTHOR:", r.get("author"))
        txt = r.get("text") or ""
        print(txt[:maxchars].replace("\n", " "))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    frag = sys.argv[2] if len(sys.argv) > 2 else None
    maxchars = int(sys.argv[3]) if len(sys.argv) > 3 else 900
    extract(path, frag, maxchars)
