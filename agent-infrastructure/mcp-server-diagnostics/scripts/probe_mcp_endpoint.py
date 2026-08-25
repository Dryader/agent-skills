#!/usr/bin/env python3
"""Probe an MCP endpoint with a raw initialize POST to classify connection failures.

Usage: python3 probe_mcp_endpoint.py <url> [Header-Name=value ...]

Classification:
  HTTP 404 on all paths        -> server outage / moved endpoint (config not at fault)
  HTTP 401/403                 -> auth problem (missing/wrong key, or OAuth required)
  text/html content-type       -> not an MCP endpoint (web page); find the real /mcp path
  HTTP 200 + JSON-RPC response -> endpoint fine; client-side issue (try /reload-mcp)

Probe BOTH with and without the credential header to separate auth from availability.
"""
import json
import sys
import urllib.error
import urllib.request

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(2)

url = sys.argv[1]
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
for h in sys.argv[2:]:
    k, _, v = h.partition("=")
    headers[k] = v

payload = json.dumps(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "probe", "version": "1"},
        },
    }
).encode()

req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        body = r.read(400).decode("utf-8", "replace")
        print(f"HTTP {r.status} content-type={r.headers.get('Content-Type')}")
        print(f"body: {body[:250]!r}")
except urllib.error.HTTPError as e:
    body = e.read(300).decode("utf-8", "replace")
    print(f"HTTP {e.code} content-type={e.headers.get('Content-Type')}")
    if body.strip():
        print(f"body: {body[:200]!r}")
except Exception as e:
    print(f"{type(e).__name__}: {e}")
