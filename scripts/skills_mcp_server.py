#!/usr/bin/env python3
"""Serve this repository's skills over MCP (stdio), with no dependencies.

An agent that speaks MCP can list, search and read these skills without cloning
the repo or copying directories into its own skills folder. Read-only: the server
never writes to the tree.

    python3 scripts/skills_mcp_server.py

Wire it into an MCP client as a stdio server, e.g. for Hermes:

    hermes mcp add agent-skills --command python3 \
        --args scripts/skills_mcp_server.py

Tools: list_skills, search_skills, get_skill.

Implemented against the MCP stdio transport directly (newline-delimited JSON-RPC
2.0) so the script runs on a bare Python 3.11+ interpreter with nothing installed.
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "__pycache__", "node_modules", "scripts", ".github"}
SERVER_INFO = {"name": "agent-skills", "version": "1.0.0"}
DEFAULT_PROTOCOL = "2024-11-05"

TOOLS = [
    {
        "name": "list_skills",
        "description": "List every skill in this repository, optionally filtered by category.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": 'optional category, e.g. "meta", "agent-infrastructure"',
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "search_skills",
        "description": "Search skill bodies and descriptions for a keyword, substring or regex.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "text or regular expression to look for"}
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_skill",
        "description": "Return the full SKILL.md text for one skill by name.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": 'skill folder name, optionally prefixed with its category, e.g. "skills-repo-audit"',
                }
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
]


def skill_paths() -> list[tuple[str, str]]:
    """(category/name, path) for every skill in the tree, sorted."""
    found = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if "SKILL.md" in filenames:
            rel = os.path.relpath(dirpath, ROOT).replace(os.sep, "/")
            found.append((f"{rel.split('/')[0]}/{os.path.basename(dirpath)}",
                          os.path.join(dirpath, "SKILL.md")))
    return sorted(found)


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    out: dict[str, str] = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        mm = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if mm:
            out[mm.group(1)] = mm.group(2).strip().strip('"')
    return out


def read_skill(name: str) -> str | None:
    for path_name, path in skill_paths():
        if path_name == name or path_name.split("/")[-1] == name:
            return open(path, encoding="utf-8").read()
    return None


# --- tools ---------------------------------------------------------------

def tool_list_skills(args: dict) -> str:
    category = (args or {}).get("category") or ""
    rows = []
    for name, path in skill_paths():
        if category and not name.startswith(f"{category}/"):
            continue
        fm = frontmatter(open(path, encoding="utf-8").read())
        rows.append(f"{name}  --  {fm.get('description', '(no description)')}")
    return "\n".join(rows) if rows else f"no skills found for category {category!r}"


def tool_search_skills(args: dict) -> str:
    query = (args or {}).get("query", "")
    if not query:
        return "give a query to search for"
    try:
        rx = re.compile(query, re.I)
    except re.error:
        rx = re.compile(re.escape(query), re.I)
    hits = []
    for name, path in skill_paths():
        for i, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
            if rx.search(line):
                hits.append(f"{name}:{i}: {line.strip()[:160]}")
    return "\n".join(hits[:80]) if hits else f"no matches for {query!r}"


def tool_get_skill(args: dict) -> str:
    name = (args or {}).get("name", "")
    text = read_skill(name)
    if text is None:
        raise ValueError(f"no skill named {name!r}; call list_skills for the index")
    fm = frontmatter(text)
    return f"{fm.get('description', '')}\n\n{text}"


HANDLERS = {
    "list_skills": tool_list_skills,
    "search_skills": tool_search_skills,
    "get_skill": tool_get_skill,
}


# --- JSON-RPC plumbing ---------------------------------------------------

def handle(msg: dict) -> dict | None:
    method = msg.get("method")
    rid = msg.get("id")
    if method is None:
        return None  # a response, not a request

    if method == "initialize":
        params = msg.get("params") or {}
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": params.get("protocolVersion") or DEFAULT_PROTOCOL,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": "Read-only index of the skills in this repository.",
            },
        }
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name", "")
        handler = HANDLERS.get(name)
        if handler is None:
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "content": [{"type": "text", "text": f"unknown tool {name!r}"}],
                    "isError": True,
                },
            }
        try:
            text = handler(params.get("arguments") or {})
        except Exception as exc:  # a tool failure is a result, not a protocol error
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "content": [{"type": "text", "text": f"{name} failed: {exc}"}],
                    "isError": True,
                },
            }
        return {"jsonrpc": "2.0", "id": rid,
                "result": {"content": [{"type": "text", "text": text}], "isError": False}}
    if method in ("resources/list", "prompts/list"):
        key = "resources" if method.startswith("resources") else "prompts"
        return {"jsonrpc": "2.0", "id": rid, "result": {key: []}}
    if rid is None:
        return None  # unknown notification: ignore
    return {
        "jsonrpc": "2.0",
        "id": rid,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        out = handle(msg)
        if out is not None:
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
