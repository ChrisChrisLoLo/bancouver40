"""Stage 2 (v2): fixed routes, GND pours, then Freerouting for the panel/backlight nets.

  pcb_route.py IN OUT WORKDIR
Needs Java >= 25 (brew install openjdk) and freerouting-2.5.0.jar in ~/.local/share/freerouting/.

Hand-routed (B.Cu, through the gaps between PocketBeagle header columns):
  D-, D+  : 22R resistors R5/R4 -> P1.09/P1.11 (USB1 host)
  VBUS    : F1 -> P1.24 VOUT
  GND/row1: repairs for what removing the old USB-C (J1) cut
Everything already on the board is locked and exported as protected wiring, so Freerouting only
adds copper for the new nets (panel RGB/SPI, backlight boost) and never touches the keyboard.
"""
import os
import re
import subprocess
import sys
import pcbnew
from pcbnew import VECTOR2I, FromMM as MM

SRC, DST, WORK = sys.argv[1], sys.argv[2], sys.argv[3]
JAVA = "/opt/homebrew/opt/openjdk/bin/java"
FREEROUTING = os.path.expanduser("~/.local/share/freerouting/freerouting-2.5.0.jar")
Y_TOP = -33.125

b = pcbnew.LoadBoard(SRC)
F, B = pcbnew.F_Cu, pcbnew.B_Cu


def track(netname, layer, width, pts):
    net = b.FindNet(netname)
    assert net is not None, netname
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(VECTOR2I(MM(c[0]), MM(c[1])))
        t.SetLayer(layer); t.SetWidth(MM(width)); t.SetNet(net)
        b.Add(t)


def via(netname, x, y, d=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(VECTOR2I(MM(x), MM(y))); v.SetDrill(MM(drill)); v.SetWidth(MM(d)); v.SetNet(b.FindNet(netname))
    b.Add(v)


SIG, PWR = 0.25, 0.4
# --- USB from the ATmega's 22R series resistors to PocketBeagle USB1 (P1.09 D-, P1.11 D+) ---
track("D-", B, SIG, [(113.0, 23.24), (113.0, 14.0), (112.56, 13.56), (112.56, -20.0), (113.0, -20.0), (113.83, -21.27)])
track("D+", B, SIG, [(114.25, 23.24), (114.25, 14.0), (115.1, 13.15), (115.1, -23.5), (111.29, -23.5), (111.29, -21.27)])
# --- 5 V from PocketBeagle VOUT (P1.24) into the keyboard's fuse ---
track("VBUS", B, PWR, [(103.0, 22.6), (103.0, 14.0), (102.4, 13.4), (102.4, -16.0), (96.05, -16.0), (96.05, -18.73)])
# --- repairs for removing J1 ---
track("row1", F, 0.25, [(114.04, 16.78), (116.65, 16.78), (116.87, 17.0)])   # no longer needs the B.Cu hop
track("GND", B, PWR, [(106.76, 24.22), (106.76, 15.0)])                       # keyboard GND -> new pour
track("GND", B, PWR, [(118.01, 21.0), (118.01, 15.0)])                        # C3 ground (was via R3/J1)
via("GND", 119.52, 34.6); via("GND", 118.685, 31.79)                          # crystal-cap ground <-> C3
track("GND", F, SIG, [(119.52, 34.6), (118.685, 31.79)])

# --- GND pours over the extension on both layers (overlapping the old pour by 1 mm) ---
gnd = b.FindNet("GND")
NEWZ = {}                       # layer -> zone (ZONE.GetLayer() is unreliable for these in this build)
for layer in (F, B):
    z = pcbnew.ZONE(b)
    NEWZ[layer] = z
    z.SetLayer(layer); z.SetNet(gnd)
    z.SetLocalClearance(MM(0.3)); z.SetMinThickness(MM(0.25))
    z.SetAssignedPriority(1)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    o = z.Outline(); o.NewOutline()
    for x, y in [(74.375, Y_TOP), (244.375, Y_TOP), (244.375, 15.875), (74.375, 15.875)]:
        o.Append(MM(x), MM(y))
    b.Add(z)
for x in (78.0, 140.0, 200.0, 241.0):           # stitching
    for y in (Y_TOP + 1.2, 13.0):
        via("GND", x, y, 0.8, 0.4)

# --- J3 ground pins: 0.5 mm pitch is too tight for the pour, so stub east (under the connector body) to vias
J3X = 210.5 - 2.9                                          # J3 pad row x
for y in (-0.45, -6.45, -12.45, -15.45, -18.45):          # pins 4, 16 (DB0), 28 (DB12), 34, 40
    track("GND", F, SIG, [(J3X, y), (J3X + 1.8, y)])
    via("GND", J3X + 1.8, y)

# --- backlight SMD ground pads: a via beside each, placed before autorouting so the pour can't strand them
import math as _m
for ref, padnum in (("U3", "4"), ("C8", "2"), ("C9", "2"), ("C10", "2"), ("R7", "2"), ("R8", "2")):
    fpt = b.FindFootprintByReference(ref)
    pd = [q for q in fpt.Pads() if q.GetNumber() == padnum][0]
    px, py = pcbnew.ToMM(pd.GetPosition().x), pcbnew.ToMM(pd.GetPosition().y)
    cx, cy = pcbnew.ToMM(fpt.GetPosition().x), pcbnew.ToMM(fpt.GetPosition().y)
    dx, dy = px - cx, py - cy
    n = _m.hypot(dx, dy) or 1.0
    reach = max(pcbnew.ToMM(pd.GetSize().x), pcbnew.ToMM(pd.GetSize().y)) / 2 + 0.6
    vx, vy = round(px + dx / n * reach, 3), round(py + dy / n * reach, 3)
    track("GND", F, SIG, [(px, py), (vx, vy)])
    via("GND", vx, vy)

# --- autoroute only the new nets ------------------------------------------------------
ROUTE = lambda n: n.startswith(("VOUT_", "LCD_", "BL_")) or n in ("VBUS", "+3V3")
for t in b.GetTracks():
    t.SetLocked(True)
dsn, ses = os.path.join(WORK, "board.dsn"), os.path.join(WORK, "board.ses")
assert pcbnew.ExportSpecctraDSN(b, dsn)


def sexp_end(s, i):
    depth, j = 0, i
    while True:
        c = s[j]
        if c == '"':
            j = s.index('"', j + 1)
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
        j += 1


def netname(tok):
    return tok[1:-1] if tok.startswith('"') else tok


# trim (network ...) to the nets we want routed; everything else stays as fixed copper / plain pads
d = open(dsn).read()
ns = d.index("(network")
ne = sexp_end(d, ns)
body = d[ns:ne + 1]
pieces = []
for m in re.finditer(r'\n    \((net|class) ', body):
    st = m.start() + 5
    en = sexp_end(body, st)
    pieces.append((st, en, m.group(1)))
newbody, last = "", 0
for st, en, kind in pieces:
    newbody += body[last:st]
    blk = body[st:en + 1]
    if kind == "net":
        name = netname(re.match(r'\(net ("[^"]*"|\S+)', blk).group(1))
        if ROUTE(name):
            newbody += blk
    else:  # class: keep only routed net names
        head = re.match(r'\(class (\S+)', blk).group(0)
        names = [n for n in re.findall(r'"[^"]*"|[^\s()]+', blk[len(head):blk.index("(circuit") if "(circuit" in blk else len(blk)])
                 if ROUTE(netname(n))]
        tail = blk[blk.index("(circuit"):] if "(circuit" in blk else ")"
        newbody += head + " " + " ".join(names) + "\n      " + tail
    last = en + 1
newbody += body[last:]
d = d[:ns] + newbody + d[ne + 1:]
open(dsn, "w").write(d)

# Freerouting is not deterministic; retry until a run finishes with nothing unrouted
for attempt in range(1, 5):
    if os.path.exists(ses):
        os.remove(ses)
    r = subprocess.run([JAVA, "-jar", FREEROUTING, "-de", dsn, "-do", ses, "-mp", "60", "-mt", "1",
                        "--gui.enabled=false"], capture_output=True, text=True, timeout=3600)
    log = r.stdout + r.stderr
    open(os.path.join(WORK, f"freerouting-{attempt}.log"), "w").write(log)
    left = [int(n) for n in re.findall(r"\((\d+) unrouted and", log)]
    print(f"freerouting attempt {attempt}: unrouted after routing = {left[-1] if left else '?'}")
    if os.path.exists(ses) and left and left[-1] == 0:
        break
assert os.path.exists(ses), "freerouting produced no .ses; see freerouting-*.log"

# import only the routed nets' wires and vias (ImportSpecctraSES would replace the whole board's tracks)
S = open(ses).read()
res = 10000.0                                   # (resolution um 10): 1e-4 mm per unit
lay = {"F.Cu": F, "B.Cu": B}
added = 0
no = S.index("(network_out")
for m in re.finditer(r'\n      \(net ("[^"]*"|\S+)', S[no:]):
    st = no + m.start() + 7
    blk = S[st:sexp_end(S, st) + 1]
    name = netname(m.group(1))
    if not ROUTE(name):
        continue
    net = b.FindNet(name)
    for w in re.finditer(r'\(path (\S+) (\d+)\s+([-\d\s]+)\)', blk):
        nums = [int(v) for v in w.group(3).split()]
        pts = [(nums[k] / res, -nums[k + 1] / res) for k in range(0, len(nums), 2)]
        for a, c in zip(pts, pts[1:]):
            if a == c:
                continue
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(VECTOR2I(MM(c[0]), MM(c[1])))
            t.SetLayer(lay[w.group(1)]); t.SetWidth(int(int(w.group(2)) / res * 1e6)); t.SetNet(net)
            b.Add(t); added += 1
    for v in re.finditer(r'\(via "Via\[0-1\]_(\d+):(\d+)_um" (-?\d+) (-?\d+)', blk):
        dia, drill, x, y = (int(g) for g in v.groups())
        vv = pcbnew.PCB_VIA(b)
        vv.SetPosition(VECTOR2I(MM(x / res), MM(-y / res))); vv.SetWidth(MM(dia / 1000)); vv.SetDrill(MM(drill / 1000))
        vv.SetNet(net); b.Add(vv); added += 1
print("imported", added, "routed items")

# --- stitch: GND vias on a 2.5 mm grid wherever they clear every other net, so the routed-through
#     F.Cu/B.Cu pours become one plane
import math


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


obst = []   # (kind, geometry, keepout radius) for everything not on GND
for t in b.GetTracks():
    if t.GetNetname() == "GND":
        if t.GetClass() == "PCB_VIA":   # hole-to-hole only
            obst.append(("p", (pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)), 0.5))
        continue
    if t.GetClass() == "PCB_VIA":
        obst.append(("p", (pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)), pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2))
    else:
        obst.append(("s", (pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y),
                           pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y)), pcbnew.ToMM(t.GetWidth()) / 2))
gnd_items = []
for f in b.GetFootprints():
    for pd in f.Pads():
        bb = pd.GetBoundingBox()
        c = ((pcbnew.ToMM(bb.GetLeft()) + pcbnew.ToMM(bb.GetRight())) / 2, (pcbnew.ToMM(bb.GetTop()) + pcbnew.ToMM(bb.GetBottom())) / 2)
        rr = math.hypot(pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())) / 2
        if pd.GetNetname() == "GND" and pd.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
            continue
        if pd.GetNetname() == "GND":                 # GND through-hole: keep hole-to-hole distance
            obst.append(("p", c, pcbnew.ToMM(pd.GetDrillSize().x) / 2 + 0.25))
            continue
        obst.append(("p", c, rr + (0.25 if pd.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else 0)))
VIA_R, CLR = 0.3, 0.3
STITCH = set()                 # positions of the vias this script scatters (only these may be removed)
stitched = 0
y = Y_TOP + 1.5
while y < 14.0:
    x = 75.6
    while x < 243.2:
        ok = True
        for kind, g, rr in obst:
            dd = math.hypot(x - g[0], y - g[1]) if kind == "p" else seg_dist(x, y, *g)
            if dd < rr + VIA_R + CLR:
                ok = False
                break
        if ok:
            STITCH.add((round(x, 3), round(y, 3)))
            via("GND", round(x, 3), round(y, 3))
            obst.append(("p", (x, y), 3.4))           # stitching vias ~4 mm apart
            stitched += 1
        x += 2.5
    y += 2.5
print("stitching vias", stitched)

# Freerouting necks down to 0.187 mm (one 0.125 mm jog) entering the 0.5 mm-pitch FPC pads
b.GetDesignSettings().m_TrackMinWidth = MM(0.12)

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())

# ---- make the new pours one plane -------------------------------------------------------
# union-find over filled pieces (both layers) joined by GND vias / through-hole pads; the main plane is
# the B.Cu piece fed by the keyboard ground (106.76, 15.0).  Isolated pieces get a via into the main plane
# where one fits; vias left in orphan pieces are removed (the pours drop those islands on refill).
ZONES = b.Zones()


def analyse():
    pieces = []                                  # (layer, SHAPE_POLY_SET)
    for lyr, z in NEWZ.items():
        ps = z.GetFilledPolysList(lyr)
        for k in range(ps.OutlineCount()):
            pc = pcbnew.SHAPE_POLY_SET(); pc.AddOutline(ps.Outline(k)); pieces.append((lyr, pc))
    parent = list(range(len(pieces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    def piece_at(lyr, pt):
        for i, (l, pc) in enumerate(pieces):
            if l == lyr and pc.Contains(pt):
                return i
        return None

    vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
    joins = [(v.GetPosition(), v) for v in vias]
    joins += [(pd.GetPosition(), None) for f in b.GetFootprints() for pd in f.Pads()
              if pd.GetNetname() == "GND" and pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
    for pt, _ in joins:
        a_, b_ = piece_at(F, pt), piece_at(B, pt)
        if a_ is not None and b_ is not None:
            parent[find(a_)] = find(b_)
    main = find(piece_at(B, VECTOR2I(MM(106.76), MM(15.0))))
    return pieces, find, main, joins, piece_at


fixed = 0
pieces, find, main, joins, piece_at = analyse()
for i, (lyr, pc) in enumerate(pieces):
    if find(i) == main:
        continue
    other = [q for j, (l, q) in enumerate(pieces) if l != lyr and find(j) == main]
    bb = pc.BBox()
    yy, done = pcbnew.ToMM(bb.GetTop()) + 0.4, False
    while yy < pcbnew.ToMM(bb.GetBottom()) and not done:
        xx = pcbnew.ToMM(bb.GetLeft()) + 0.4
        while xx < pcbnew.ToMM(bb.GetRight()) and not done:
            pt = VECTOR2I(MM(xx), MM(yy))
            if pc.Contains(pt) and any(o.Contains(pt) for o in other) and all(
                    (math.hypot(xx - g[0], yy - g[1]) if kind == "p" else seg_dist(xx, yy, *g)) >= rr + VIA_R + CLR
                    for kind, g, rr in obst if rr < 3.0):
                via("GND", round(xx, 3), round(yy, 3)); STITCH.add((round(xx, 3), round(yy, 3)))
                fixed += 1; done = True
            xx += 0.25
        yy += 0.25
filler.Fill(ZONES)
pieces, find, main, joins, piece_at = analyse()
orphans = []
for pt, v in joins:
    if v is None or (round(pcbnew.ToMM(pt.x), 3), round(pcbnew.ToMM(pt.y), 3)) not in STITCH:
        continue                                  # only our stitching vias; never the hand-routed ones
    hit = [i for i in (piece_at(F, pt), piece_at(B, pt)) if i is not None]
    if not any(find(i) == main for i in hit):     # isolated, or sitting in a void on both layers
        orphans.append(v)
for v in orphans:
    b.Remove(v)
filler.Fill(ZONES)
print(f"pour: {fixed} joining vias added, {len(orphans)} orphan vias removed")
pcbnew.SaveBoard(DST, b)
print("routed + filled")
