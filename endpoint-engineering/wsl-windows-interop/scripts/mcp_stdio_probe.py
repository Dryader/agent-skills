"""Probe any stdio MCP server before configuring it: spawn, JSON-RPC initialize, tools/list.
Usage:
  python3 mcp_stdio_probe.py --command "/mnt/c/Windows/System32/cmd.exe" \
      --args "/c" "C:\\path\\launcher.cmd" \
      --env ELECTRON_RUN_AS_NODE=1 OD_DATA_DIR=C:\\...
Exits 0 with server info + tool names on a valid handshake; nonzero with diagnostics otherwise.
"""
import argparse, json, os, select, subprocess, sys, time

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--command', required=True)
    ap.add_argument('--args', nargs='*', default=[])
    ap.add_argument('--env', nargs='*', default=[], help='KEY=VALUE pairs for the child env')
    ap.add_argument('--timeout', type=int, default=20)
    a = ap.parse_args()

    env = dict(os.environ)
    for kv in a.env:
        k, _, v = kv.partition('=')
        env[k] = v

    print('spawning:', a.command, a.args)
    p = subprocess.Popen([a.command] + a.args, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    time.sleep(3)
    if p.poll() is not None:
        print(f'PROCESS EXITED EARLY code={p.returncode}')
        print('stderr:', p.stderr.read().decode(errors='replace')[:500])
        sys.exit(1)

    def send(obj):
        p.stdin.write((json.dumps(obj) + '\n').encode())
        p.stdin.flush()

    def recv():
        r, _, _ = select.select([p.stdout], [], [], a.timeout)
        if not r:
            return None
        return p.stdout.readline().decode(errors='replace')

    send({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
          'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                     'clientInfo': {'name': 'probe', 'version': '1.0'}}})
    line = recv()
    if not line:
        print('NO RESPONSE — stdin/stdout not bridged (GUI-subsystem exe? use cmd.exe bridge)')
        p.kill(); sys.exit(1)
    try:
        info = json.loads(line)['result']['serverInfo']
        print('HANDSHAKE OK:', info)
    except Exception:
        print('BAD RESPONSE:', line[:300]); p.kill(); sys.exit(1)

    send({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}})
    line2 = recv()
    if not line2:
        print('TOOLS: no response from server')
        sys.exit(1)
    try:
        tools = json.loads(line2).get('result', {}).get('tools', [])
    except ValueError:
        print('TOOLS: non-JSON response')
        sys.exit(1)
    print(f'TOOLS ({len(tools)}):', [t['name'] for t in tools][:25])
    p.kill()

if __name__ == '__main__':
    main()
