#!/usr/bin/env python3
"""Pull every number the drawings use out of the SolidCraft models (headless MCP session + cli eval).
Writes data/topo_Case.json, data/topo_Bezel.json, data/checks.json, data/asm_bboxes.json."""
import json, os, subprocess, sys
sys.path.insert(0, "/Users/elevenarms/Code/cadkey/bancouver40/tools/pocketbeagle2")
from sc import Client
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
PD = "/Users/elevenarms/Code/cadkey/bancouver40/case/pocketbeagle2"
c = Client(headless_in=f"{PD}/bancouver40_pb2_case.step")
for b in ("Case", "Bezel"):
    open(f"{D}/topo_{b}.json", "w").write(c.call("body_topology", {"body": b}))
checks = {"measure": json.loads(c.call("measure", {}))}
# point-picked measurements (diameters of cylinders, distances between faces) as cross-checks
picks = {
    "kb_boss_od": [{"type": "face", "body": "Case", "point": [19.6 - 1.8, 36.6, 3]}],
    "kb_pilot": [{"type": "face", "body": "Case", "point": [19.6 - 0.875, 36.6, 3]}],
    "so_boss_od": [{"type": "face", "body": "Case", "point": [16.225 - 2.5, 114.975, 3]}],
    "so_hole": [{"type": "face", "body": "Case", "point": [16.225 - 1.2, 114.975, 3]}],
    "so_cbore": [{"type": "face", "body": "Case", "point": [16.225 - 2.1, 114.975, 0.8]}],
    "reset": [{"type": "face", "body": "Case", "point": [62.1 - 1, 49.6, 0.5]}],
    "wall_left": [{"type": "face", "body": "Case", "point": [0, 40, 5]}, {"type": "face", "body": "Case", "point": [2, 40, 5]}],
    "floor": [{"type": "face", "body": "Case", "point": [100, 40, 0]}, {"type": "face", "body": "Case", "point": [100, 40, 1]}],
    "bz_hole": [{"type": "face", "body": "Bezel", "point": [16.225 - 1.1, 114.975, 21.3]}],
    "bz_cbore": [{"type": "face", "body": "Bezel", "point": [16.225 - 2.1, 114.975, 22.1]}],
    "bz_win_x": [{"type": "face", "body": "Bezel", "point": [30.1, 96.2, 21.45]}, {"type": "face", "body": "Bezel", "point": [141.2, 96.2, 21.45]}],
    "bz_win_y": [{"type": "face", "body": "Bezel", "point": [85.65, 77.515, 21.45]}, {"type": "face", "body": "Bezel", "point": [85.65, 114.885, 21.45]}],
}
for k, items in picks.items():
    checks[k] = c.call("execute", {"command": "inspect.measure", "params": {"items": items}})
json.dump(checks, open(f"{D}/checks.json", "w"), indent=1)
# assembly: bounding boxes of the reference bodies and the PocketBeagle 2 parts
ev = f"{D}/asm_eval_full.json"
if not os.path.exists(ev):
    subprocess.run(["/Applications/SolidCraft.app/Contents/MacOS/solidcraft-cli", "eval", f"{PD}/bancouver40_pb2.solidcraft", "--json-out", ev], check=True)
bodies = json.load(open(ev))["bodies"]
keep = {b["name"]: b["bbox"] for b in bodies if b.get("bbox") and None not in b["bbox"]["min"]}
json.dump(keep, open(f"{D}/asm_bboxes.json", "w"))
os.remove(ev)
print("ok", len(keep))
