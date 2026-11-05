"""Stage 0: strip the bancouver40's USB-C (J1, CC resistors, its tracks) and the old outline.
Separate process from pcb_extend.py because this KiCad's SWIG proxies go stale after Remove()."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
# NB: this KiCad's SWIG iterators break after any Remove(), so collect everything first
edge_items = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
dead = [t for t in b.GetTracks()
        if t.GetNetname() in ("VBUS", "D+", "D-", "Net-(J1-PadA5)", "Net-(J1-PadB5)")]
# J1's ground stubs (shield + GND pads, R2/R3 ground) and row1's B.Cu hop over the old J1 shield trace
M = pcbnew.ToMM
STUBS = [  # (net, layer, x0, y0, x1, y1)
    ("GND", "B.Cu", 107.48, 23.5, 106.76, 24.22), ("GND", "B.Cu", 107.75, 23.5, 107.48, 23.5),
    ("GND", "B.Cu", 107.45, 20.67, 106.89, 20.1), ("GND", "B.Cu", 108.16, 20.67, 107.45, 20.67),
    ("GND", "B.Cu", 114.96, 20.67, 115.53, 20.1), ("GND", "B.Cu", 114.26, 20.67, 114.96, 20.67),
    ("GND", "F.Cu", 106.89, 24.09, 106.89, 20.1), ("GND", "F.Cu", 106.76, 24.22, 106.89, 24.09),
    ("GND", "F.Cu", 106.89, 15.92, 115.53, 15.92), ("GND", "F.Cu", 115.53, 15.92, 115.53, 20.1),
    ("row1", "B.Cu", 114.04, 16.78, 114.32, 17.05), ("row1", "B.Cu", 114.32, 17.05, 116.83, 17.05),
    ("row1", "B.Cu", 116.83, 17.05, 116.87, 17.0),
    ("row1", "VIA", 114.04, 16.78, 114.04, 16.78), ("row1", "VIA", 116.87, 17.0, 116.87, 17.0),
]


def match(t, stub):
    net, layer, *c = stub
    if t.GetNetname() != net:
        return False
    if (layer == "VIA") != (t.GetClass() == "PCB_VIA") or (layer != "VIA" and t.GetLayerName() != layer):
        return False
    a = [M(t.GetStart().x), M(t.GetStart().y), M(t.GetEnd().x), M(t.GetEnd().y)]
    close = lambda p, q: all(abs(u - v) < 0.02 for u, v in zip(p, q))
    return (close(a[:2], c[:2]) and close(a[2:], c[2:])) or (close(a[:2], c[2:]) and close(a[2:], c[:2]))


stub_hits = [t for t in b.GetTracks() if any(match(t, st) for st in STUBS)]
assert len(stub_hits) == len(STUBS), f"matched {len(stub_hits)} of {len(STUBS)} stubs"
dead += stub_hits
for t in dead:
    b.Remove(t)
for ref in ("J1", "R2", "R3"):
    b.Remove(b.FindFootprintByReference(ref))

for d in edge_items:
    b.Remove(d)
pcbnew.SaveBoard(sys.argv[2], b)
