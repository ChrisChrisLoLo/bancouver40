#!/usr/bin/env python3
"""Tiny stdio MCP client for SolidCraft (bridged to the running GUI when it is open).

Usage:
  sc.py tools                       list tool names
  sc.py call TOOL '{"json":"args"}'  call one tool, print the result
  sc.py batch FILE.json              send {"commands":[...]} through the `batch` tool
"""
import json, subprocess, sys

CLI = "/Applications/SolidCraft.app/Contents/MacOS/solidcraft-cli"
ALLOW = __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "../.."))


class Client:
    """headless_in=PATH starts a private headless session on that design (state lives as long as the
    Client); without it the server bridges to the running SolidCraft app."""
    def __init__(self, headless_in=None):
        args = [CLI, "mcp", "--allow-path", ALLOW]
        if headless_in:
            args += ["--headless", "--in", headless_in]
        self.p = subprocess.Popen(args,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.i = 0
        init = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                       "clientInfo": {"name": "sc.py", "version": "0"}})
        self.instructions = init.get("instructions", "")
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def send(self, msg):
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()

    def rpc(self, method, params):
        self.i += 1
        self.send({"jsonrpc": "2.0", "id": self.i, "method": method, "params": params})
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise SystemExit("server closed")
            msg = json.loads(line)
            if msg.get("id") == self.i:
                if "error" in msg:
                    raise SystemExit(json.dumps(msg["error"], indent=1))
                return msg["result"]

    def call(self, name, args):
        r = self.rpc("tools/call", {"name": name, "arguments": args})
        out = []
        for c in r.get("content", []):
            if c["type"] == "text":
                out.append(c["text"])
            else:
                out.append(f"<{c['type']} {c.get('mimeType','')}>")
        return ("ERROR: " if r.get("isError") else "") + "\n".join(out)


if __name__ == "__main__":
    c = Client()
    cmd = sys.argv[1]
    if cmd == "tools":
        print(c.instructions[-200:])
        print([t["name"] for t in c.rpc("tools/list", {})["tools"]])
    elif cmd == "call":
        print(c.call(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}))
    elif cmd == "batch":
        args = json.load(open(sys.argv[2]))
        args.setdefault("verbose", False)
        print(c.call("batch", args))
