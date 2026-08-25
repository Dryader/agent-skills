---
name: wsl-windows-interop
description: "WSL-Windows interop: paths, exes, GUI-stdio, MCP wiring."
tags: [wsl, windows, interop, mcp, stdio, electron]
triggers:
  - WSL and Windows interop
  - running Windows executables from WSL
  - MCP wiring across WSL and Windows

---

# WSL ↔ Windows Interop

This machine is a WSL (Ubuntu) primary with a Windows host. Many tools, keys, and apps live Windows-side (Git, IBKR Python, Electron apps, `C:\Users\<user>\*.env` keys). This skill is the playbook for crossing the boundary.

## Path translation rules

- Linux tools (`curl`, `python3`, Hermes file tools) need `/mnt/c/...` paths. Windows tools need `C:\...` paths.
- When spawning a Windows executable FROM Linux: the executable path resolves via interop (use `/mnt/c/...` or the `C:\...` form in bash), but **arguments are passed to the Windows process literally — never auto-converted**. A Windows Electron/Node child cannot open `/mnt/c/...` args; keep `C:\...` style for anything the child reads (scripts, files).
- Env vars pass through interop unchanged (`ELECTRON_RUN_AS_NODE=1` etc. work).
- Keys in Windows env files: read via `/mnt/c/Users/<user>/<name>.env`, strip whitespace.

## THE GUI-SUBSYSTEM STDIO BUG (verified Aug 2026, Open Design MCP)

Spawning a Windows GUI-subsystem exe (Electron apps like `Open Design.exe`) **directly** from WSL gives it dead stdin/stdout: the process starts and exits 0 silently, `console.log` output goes nowhere, MCP daemons die instantly. Console-subsystem apps (`cmd.exe`, `powershell.exe`) bridge fine.

**Fix: cmd.exe launcher bridge.** Write a `.cmd` launcher next to the app that sets the env vars and runs the exe, then invoke it via `cmd.exe /c`:

```cmd
@echo off
set ELECTRON_RUN_AS_NODE=1
set OD_DATA_DIR=C:\Users\<user>\AppData\Roaming\...\data
set OD_SIDECAR_IPC_PATH=\\.\pipe\...
set OD_MCP_BOOTSTRAP_COMMAND=C:\...\Open Design.exe
set OD_MCP_BOOTSTRAP_ARGS=["--headless"]
"C:\...\Open Design.exe" "C:\...\daemon-cli.mjs" mcp
```

Invoke from WSL: `cmd.exe /c "C:\Users\...\launcher.cmd"` — cmd is a console app, so WSL's pipes bridge through it and the GUI child inherits working handles (verified: full MCP handshake through this chain).

Diagnosis recipe: `ELECTRON_RUN_AS_NODE=1 <exe> -e "console.log('X')"` → empty output = dead stdio. Same via cmd.exe → PID prints = bridge works.

## Wiring a Windows MCP server into Hermes (verify BEFORE configuring)

1. Probe the server first — spawn command+args+env, send a JSON-RPC `initialize` then `tools/list` over stdin, confirm a valid response (use `scripts/mcp_stdio_probe.py`). Never configure blind.
2. Add via CLI (config.yaml is write-protected from agents): `hermes mcp add <name> --command "/mnt/c/Windows/System32/cmd.exe" --args "/c" "C:\\...\\launcher.cmd" --connect-timeout 60`. The `--args` list must come last.
3. The add flow prompts `Enable all N tools?` — pipe `printf 'Y\n'` (no TTY).
4. Verify: `hermes mcp list` then `hermes mcp test <name>`.
5. MCP servers load at agent startup; `/reload-mcp` exists in-session.

## Exposing a WSL-only CLI to a Windows process (PATH shim)

Windows daemons resolve agent CLIs on the WINDOWS PATH — a WSL-only tool is invisible to them. Fix: drop a `.cmd` shim into `C:\Users\<user>\AppData\Local\Microsoft\WindowsApps\` (already on the user PATH — no setx needed):

```bat
@echo off
wsl.exe -d Ubuntu -e /home/<user>/.local/bin/<tool> %*
```

- Version probes (`<tool> --version`) and interactive stdio sessions both bridge through `wsl.exe` (console app).
- **No daemon restart needed** if its inherited PATH already contains the dir: PATH is captured at process spawn, but file *existence* is re-checked per probe. Verified: Open Design's `list_agents` flipped hermes to available seconds after the shim appeared.
- Check the tool's source for a bin-override env var first — e.g. Open Design supports `HERMES_BIN` / `CLAUDE_BIN` / `CODEX_BIN` (`apps/daemon/src/runtimes/executables.ts`). An env override in the launcher is cleaner than PATH surgery.
- **Disable by rename, not delete**: `<tool>.cmd` → `<tool>.cmd.disabled` achieves the same (binary no longer resolves) and is reversible. The user explicitly denied an `rm` on such a file — they prefer non-destructive disable. Verify with `cmd.exe /c "where <tool>"` → "Could not find files".

## Agent adapters vs MCP — check the live registry, not the docs

A desktop app may expose BOTH directions: MCP (agent → app daemon) and an agent adapter (app daemon → agent CLI, often over ACP JSON-RPC). Before claiming an integration doesn't exist, query the daemon's own registries (`list_agents`, `list_skills`, `list_plugins` via its MCP tools) — this session's docs-based claim that Open Design had no Hermes connector was wrong: `list_agents` showed a hermes adapter (spawns `hermes acp --accept-hooks`, streamFormat `acp-json-rpc`) that was merely *unavailable* because the CLI wasn't on the Windows PATH. Adapter availability is gated by a version probe (`--version`); the `available: false` field + installUrl appears in the registry until the binary resolves.

## Process verification from WSL (identifying Windows daemons)

- **PowerShell from bash: ALWAYS single-quote the `-Command`** — double quotes let bash expand `$_` (to the previous command's last arg), silently corrupting the script; with stderr discarded you get empty output that reads as "no process found" when the query never ran. Cost two verification attempts in one session.
- System32 exes may not resolve from WSL (`wevtutil: command not found`) — call via full path `/mnt/c/Windows/System32/<exe>.exe` (e.g. wevtutil, sigcheck).
- UEFI-variable cmdlets (`Get-SecureBootUEFI`, `Confirm-SecureBootUEFI`) require elevation; from non-elevated WSL they fail with "Unable to set proper privileges. Access was denied." — don't retry, hand the user the command to run in an elevated PowerShell instead. Plain `reg.exe query` of HKLM policy/state keys works un-elevated from WSL.
- Identify daemons by command line, not process name: `powershell.exe -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "something" } | ForEach-Object { "{0} | {1}" -f $_.ProcessId, $_.Name }'`
- `tasklist.exe //FO CSV` works from WSL (the `//` escapes the slash). GUI apps legitimately run 8-10 processes with the same image name (Electron main + GPU + renderers + node) — many PIDs is normal, not a leak.
- cmd.exe from WSL prints a `\\wsl.localhost\... UNC paths are not supported` stderr warning — filter with `grep -v "UNC\|CMD.EXE\|Defaulting"` when asserting on output.
- **WSL2 NAT**: Windows loopback (127.0.0.1) is unreachable from WSL, and Windows services binding loopback-only are also unreachable via the WSL gateway IP. A Windows daemon's HTTP API is often unusable from WSL — use its MCP/other interfaces instead. (Reverse direction — Windows→WSL localhost — works via the WSL mirror.)

## Testing PowerShell scripts from WSL (real end-to-end)

`powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\path\script.ps1" -Arg value` runs a .ps1 against the real Windows host (services, drivers, registry, network) — console app, so stdio bridges fine. Rules:

- Pass Windows paths to the script literally (`C:\...`), never `/mnt/c/...` — arguments are not auto-converted.
- A script-level `exit N` propagates to bash; check with `$?` after the call.
- Verified Aug 2026: full scanner script + positive-control sample + both data paths tested this way in one session (LOLDrivers scan; see `windows-vulnerability-scanning` skill).
- Gotchas that surfaced while writing the PS 5.1-compatible script (generic PowerShell, not WSL-specific): `ConvertFrom-Json` throws on duplicate JSON keys (use System.Web.Extensions JavaScriptSerializer with MaxJsonLength=int.MaxValue on PS 5.1); `Get-ChildItem -Include` is ignored without `-Recurse` or a wildcard path (filter with Where-Object instead); functions unroll collections on return so `AddRange((func))` fails with Object[] — use `return ,$list`; don't query CIM per-file in loops, precompute the set once.

## Misc gotchas

- `cmd.exe` from WSL with a UNC CWD prints a warning and defaults to Windows dir — harmless, but run with `workdir` set or ignore.
- Windows `.cmd` files are NOT directly executable from Linux (no binfmt) — always through `cmd.exe /c`.
- Quote hell: write batch files with `printf` (CRLF line endings) instead of fighting inline escaping.
- App updates may not touch launchers placed alongside (not inside `resources/`).

## Files

- `scripts/mcp_stdio_probe.py` — generic MCP server probe (spawn → initialize → tools/list) for verifying any stdio server before config.
