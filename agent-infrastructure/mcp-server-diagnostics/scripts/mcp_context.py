#!/usr/bin/env python3
"""Measure Hermes MCP context footprint, or probe one server.

Run with the Hermes venv python, NOT system python (the `mcp` package only
lives in the venv). Find it via: head -1 $(which hermes) -> venv/bin/hermes ->
venv/bin/python. Example:

  ~/.hermes/hermes-agent/venv/bin/python mcp_context.py [server_name]

No args: connects to every server in ~/.hermes/config.yaml mcp_servers,
replicates Hermes registration (tools.include/exclude config filters,
capability-gated utility tools), and prints:
  - per server: enabled tool count, full-schema bytes (cost if NOT deferred),
    deferred-catalog bytes (what actually ships in the system prompt),
    largest single tool schema, listing form, capabilities
  - totals + token estimate (chars/4, Hermes's cheap rule)
One arg (server name): prints that server's enabled tool names + sizes only.
Useful as a standalone health probe: a server that connects and lists tools
here is healthy, isolating server/key problems from Hermes config problems.

Why this exists: Hermes defers MCP tool schemas into a compact one-line-per-tool
catalog (tools/tool_search.py build_catalog_listing_with_form: first sentence
clipped to 60 chars, grouped per server, 4000-token budget with per-server
degradation) instead of shipping full JSON schemas on every request. Measured
Aug 2026: 67 tools across 6 servers cost ~6.7KB (~1,700 tok) catalog vs ~100KB
(~25.5k tok) if fully expanded. Detail: the SKILL.md mcp-context-footprint section.
"""
import asyncio, json, os, sys

sys.path.insert(0, os.path.expanduser("~/.hermes/hermes-agent"))
import yaml
from tools.tool_search import build_catalog_listing_with_form
from tools.mcp_tool import _build_utility_schemas, mcp_prefixed_tool_name

HERMES_HOME = os.path.expanduser("~/.hermes")
cfg = yaml.safe_load(open(f"{HERMES_HOME}/config.yaml"))
servers = cfg.get("mcp_servers", {})
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def eodhd_token():
    # eodhd.client.json has NO access_token (only client registration);
    # the token lives in eodhd.json. Check expires_at if you get 401s.
    d = json.load(open(f"{HERMES_HOME}/mcp-tokens/eodhd.json"))
    return d.get("access_token")

def apply_filter(name, tools):
    f = (servers.get(name) or {}).get("tools") or {}
    inc, exc = f.get("include"), f.get("exclude")
    out = []
    for t in tools:
        if inc is not None and t.name not in inc:
            continue
        if exc is not None and t.name in exc:
            continue
        out.append(t)
    return out

async def connect(name, sconf):
    if "command" in sconf:
        from mcp.client.stdio import stdio_client, StdioServerParameters
        from mcp import ClientSession
        params = StdioServerParameters(command=sconf["command"], args=sconf.get("args", []),
                                       env={**os.environ, **sconf.get("env", {})})
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                init = await s.initialize()
                return init, (await s.list_tools()).tools
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession
    headers = dict(sconf.get("headers") or {})
    if name == "eodhd":
        headers["Authorization"] = f"Bearer {eodhd_token()}"
    if name == "parallel_search":
        headers.setdefault("User-Agent", UA)  # Cloudflare blocks default UAs
    async with streamablehttp_client(sconf["url"], headers=headers or None) as (r, w, _):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            return init, (await s.list_tools()).tools

def has_cap(init, cap):
    c = getattr(init, "capabilities", None)
    return c is not None and getattr(c, cap, None) is not None

def make_def(name, tool_name, desc, params):
    return {"type": "function", "function": {
        "name": mcp_prefixed_tool_name(name, tool_name), "description": desc,
        "parameters": params or {"type": "object", "properties": {}},
    }}

async def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    rows, tot_t, tot_s, tot_c = [], 0, 0, 0
    for name, sconf in sorted(servers.items()):
        if only and name != only:
            continue
        try:
            init, tools = await connect(name, sconf)
        except Exception as e:
            print(f"{name}: CONNECT ERROR {type(e).__name__}: {e}")
            continue
        tools = apply_filter(name, tools)
        defs = [make_def(name, t.name, t.description or f"MCP tool {t.name} from {name}",
                         getattr(t, "inputSchema", None)) for t in tools]
        if has_cap(init, "prompts") or has_cap(init, "resources"):
            for u in _build_utility_schemas(name):
                defs.append({"type": "function", "function": u["schema"]})
        if only:
            print(f"{name}: {len(defs)} tools enabled")
            for d in defs:
                print(f"  {d['function']['name']}: "
                      f"{len(json.dumps(d, separators=(',', ':')))/1024:.1f}KB")
            return
        schema_bytes = len(json.dumps(defs, separators=(",", ":")))
        listing, form = build_catalog_listing_with_form(defs)
        listing_bytes = len(listing) if listing else 0
        mx = max(len(json.dumps(d, separators=(",", ":"))) for d in defs) if defs else 0
        caps = ("p+r" if has_cap(init, "prompts") and has_cap(init, "resources")
                else "p" if has_cap(init, "prompts")
                else "r" if has_cap(init, "resources") else "-")
        tot_t += len(defs); tot_s += schema_bytes; tot_c += listing_bytes
        rows.append((name, len(defs), schema_bytes, listing_bytes, mx, form, caps))
    print(f"{'server':<15}{'tools':>6}{'full-schema':>13}{'catalog':>9}{'maxTool':>9}  form caps")
    for name, n, sb, cb, mx, form, caps in rows:
        print(f"{name:<15}{n:>6}{sb/1024:>9.1f}KB{cb:>8}B{mx/1024:>8.1f}KB  {form:<6}{caps}")
    print("-" * 60)
    print(f"{'TOTAL':<15}{tot_t:>6}{tot_s/1024:>9.1f}KB{tot_c:>8}B")
    print(f"\nToken estimate (chars/4): catalog ~{tot_c/4:,.0f} tok/request; "
          f"full-schema ~{tot_s/4:,.0f} tok/request")

asyncio.run(main())
