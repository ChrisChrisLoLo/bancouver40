#!/usr/bin/env python3
"""Lay out the dimensioned A3 sheets over the SolidCraft orthographic renders.
Every dimension value is read from data/ (body_topology / inspect.measure of bancouver40_pb2_case.step and the
bounding boxes from `solidcraft-cli eval bancouver40_pb2.solidcraft`); the generator's nominal values (case_v2.py)
are used only to *find* a face, and any face that is not within 0.02 mm of its nominal is reported.
Writes sheet1..4.svg, sheets.html, data/values.json, data/mismatches.json."""
import json, math, os
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
VIEWS = json.load(open(os.path.join(HERE, "img", "views.json")))
TOPO = {b: json.load(open(f"{D}/topo_{b}.json")) for b in ("Case", "Bezel")}
ASM = json.load(open(f"{D}/asm_bboxes.json"))
MISMATCH, VALUES = [], {}
AX = {"x": 0, "y": 1, "z": 2}
DATE = "2026-11-05"
PROJECT = "Zine Machine v0 – bancouver40 + PocketBeagle 2 + 4.58in bar display"


# ---------------------------------------------------------------- model look-ups
def P(body, axis, nominal, name=None):
    """Measured coordinate of the planar face of `body` normal to `axis` nearest `nominal`."""
    i = AX[axis]
    best = None
    for f in TOPO[body]["faces"]:
        if "cylinder" in f:
            continue
        n = f["plane_normal"]
        if abs(abs(n[i]) - 1) > 1e-6:
            continue
        v = f["point"][i]
        if best is None or abs(v - nominal) < abs(best - nominal):
            best = v
    if best is None or abs(best - nominal) > 0.02:
        raise SystemExit(f"no {axis}-face of {body} near {nominal} (nearest {best})")
    best = round(best, 4)
    if abs(best - nominal) > 0.0005:
        MISMATCH.append({"what": name or f"{body} {axis}-face", "nominal": nominal, "measured": best})
    if name:
        VALUES[name] = best
    return best


def CYL(body, x, y, dia, name=None):
    """Measured centre and diameter of the vertical cylinder of `body` at (x, y) with diameter ~dia."""
    for f in TOPO[body]["faces"]:
        c = f.get("cylinder")
        if not c:
            continue
        o, r = c["origin"], c["radius"]
        if abs(o[0] - x) < 0.02 and abs(o[1] - y) < 0.02 and abs(2 * r - dia) < 0.02:
            out = (round(o[0], 4), round(o[1], 4), round(2 * r, 4))
            for a, b, w in ((out[0], x, "x"), (out[1], y, "y"), (out[2], dia, "dia")):
                if abs(a - b) > 0.0005:
                    MISMATCH.append({"what": f"{name or body} {w}", "nominal": b, "measured": a})
            if name:
                VALUES[name] = out
            return out
    raise SystemExit(f"no cylinder of {body} at {x},{y} d{dia}")


def BB(name, label=None):
    b = ASM[name]
    out = ([round(v, 3) for v in b["min"]], [round(v, 3) for v in b["max"]])
    VALUES[label or name] = out
    return out


def f(v):
    s = f"{abs(v):.3f}".rstrip("0").rstrip(".")
    return s


# ---------------------------------------------------------------- SVG primitives
class Sheet:
    def __init__(self, num, title, scale, source):
        self.num, self.title, self.scale, self.source, self.el, self.imgs = num, title, scale, source, [], []

    def add(self, s):
        self.el.append(s)

    def line(self, x1, y1, x2, y2, cls="thin"):
        self.add(f'<line class="{cls}" x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}"/>')

    def text(self, x, y, s, size=3.2, anchor="middle", rot=0, cls="t", weight=None):
        tr = f' transform="rotate({rot} {x:.3f} {y:.3f})"' if rot else ""
        w = f' font-weight="{weight}"' if weight else ""
        self.add(f'<text class="{cls}" x="{x:.3f}" y="{y:.3f}" font-size="{size}" text-anchor="{anchor}"{w}{tr}>{escape(s)}</text>')

    def arrow(self, tx, ty, dx, dy, L=2.6, W=0.85):
        n = math.hypot(dx, dy); dx, dy = dx / n, dy / n
        bx, by = tx - dx * L, ty - dy * L
        self.add(f'<polygon class="arr" points="{tx:.3f},{ty:.3f} {bx - dy * W / 2:.3f},{by + dx * W / 2:.3f} {bx + dy * W / 2:.3f},{by - dx * W / 2:.3f}"/>')

    def rect(self, x, y, w, h, cls="frame"):
        self.add(f'<rect class="{cls}" x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}"/>')

    def image(self, name, view):
        m = VIEWS[name]
        x, y = view.paper_uv(m["u"][0], m["v"][1])
        w, h = (m["u"][1] - m["u"][0]) * view.k, (m["v"][1] - m["v"][0]) * view.k
        self.imgs.append(f'<image href="img/{name}.png" x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" preserveAspectRatio="none"/>')
        return x, y, w, h

    def image_box(self, name, x, y, w):
        m = VIEWS[name]
        h = w * m["H"] / m["W"]
        self.imgs.append(f'<image href="img/{name}.png" x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}"/>')
        return h

    # ---- dimensions (paper coordinates)
    def dim(self, p1, p2, orient, at, text, flip_text=False, outside=None, tpos=None):
        """Linear dimension between paper points p1, p2. orient 'h' (dimension line y=at) or 'v' (x=at)."""
        if orient == "h":
            a, b = sorted((p1, p2), key=lambda p: p[0])
            for p in (a, b):
                s = 1 if at > p[1] else -1
                if abs(at - p[1]) > 0.3:
                    self.line(p[0], p[1] + s * 0.8, p[0], at + s * 1.5, "ext")
            x1, x2, L = a[0], b[0], b[0] - a[0]
            tw = 0.56 * 3.2 * len(text)
            out = outside if outside is not None else L < 7
            if out:
                self.line(x1 - 5, at, x2 + 5, at, "dim")
                self.arrow(x1, at, 1, 0); self.arrow(x2, at, -1, 0)
            else:
                self.line(x1, at, x2, at, "dim")
                self.arrow(x1, at, -1, 0); self.arrow(x2, at, 1, 0)
            if tpos == "right" or (tpos is None and out and L < tw + 1):
                self.text(x2 + 6, at - 0.8, text, anchor="start")
            elif tpos == "left":
                self.text(x1 - 6, at - 0.8, text, anchor="end")
            else:
                self.text((x1 + x2) / 2, at - 0.8, text)
        else:
            a, b = sorted((p1, p2), key=lambda p: p[1])
            for p in (a, b):
                s = 1 if at > p[0] else -1
                if abs(at - p[0]) > 0.3:
                    self.line(p[0] + s * 0.8, p[1], at + s * 1.5, p[1], "ext")
            y1, y2, L = a[1], b[1], b[1] - a[1]
            tw = 0.56 * 3.2 * len(text)
            out = outside if outside is not None else L < 7
            if out:
                self.line(at, y1 - 5, at, y2 + 5, "dim")
                self.arrow(at, y1, 0, 1); self.arrow(at, y2, 0, -1)
            else:
                self.line(at, y1, at, y2, "dim")
                self.arrow(at, y1, 0, -1); self.arrow(at, y2, 0, 1)
            if tpos == "below" or (tpos is None and out and L < tw + 1):
                self.text(at - 0.8, y2 + 6, text, rot=-90, anchor="end")
            elif tpos == "above":
                self.text(at - 0.8, y1 - 6, text, rot=-90, anchor="start")
            else:
                self.text(at - 0.8, (y1 + y2) / 2, text, rot=-90)

    def leader(self, tip, tx, ty, text, anchor="start", size=3.2, dot=False):
        sh = 3 if anchor == "start" else -3
        self.line(tx - sh, ty, tip[0], tip[1], "dim")
        self.line(tx - sh, ty, tx, ty, "dim")
        if dot:
            self.add(f'<circle class="arr" cx="{tip[0]:.3f}" cy="{tip[1]:.3f}" r="0.5"/>')
        else:
            self.arrow(tip[0], tip[1], tip[0] - (tx - sh), tip[1] - ty)
        lines = text.split("\n")
        for i, s in enumerate(lines):
            self.text(tx + (0.8 if anchor == "start" else -0.8), ty - 0.8 + i * (size + 1.0), s, anchor=anchor, size=size)

    def balloon(self, tip, bx, by, label, r=3.4):
        dx, dy = tip[0] - bx, tip[1] - by
        n = math.hypot(dx, dy) or 1
        self.line(bx + dx / n * r, by + dy / n * r, tip[0], tip[1], "dim")
        self.add(f'<circle class="arr" cx="{tip[0]:.3f}" cy="{tip[1]:.3f}" r="0.45"/>')
        self.add(f'<circle class="ball" cx="{bx:.3f}" cy="{by:.3f}" r="{r}"/>')
        self.text(bx, by + 1.15, label, size=3.0 if len(label) < 3 else 2.4, weight="bold")

    def cmark(self, c, r):
        e = r + 1.5
        self.line(c[0] - e, c[1], c[0] + e, c[1], "cl"); self.line(c[0], c[1] - e, c[0], c[1] + e, "cl")

    def cutline(self, p1, p2, label, arrow_dir, L=7):
        """Section line from p1 to p2 (paper); arrow_dir = viewing direction (paper vector)."""
        self.line(*p1, *p2, "cut")
        for p in (p1, p2):
            self.line(p[0], p[1], p[0] + arrow_dir[0] * L, p[1] + arrow_dir[1] * L, "cutend")
            self.arrow(p[0] + arrow_dir[0] * L, p[1] + arrow_dir[1] * L, *arrow_dir, L=3.2, W=1.4)
            ex, ey = (p2[0] - p1[0], p2[1] - p1[1])
            n = math.hypot(ex, ey); ex, ey = ex / n, ey / n
            sgn = -1 if p is p1 else 1
            self.text(p[0] + arrow_dir[0] * (L + 2) + sgn * ex * 3.5, p[1] + arrow_dir[1] * (L + 2) + sgn * ey * 3.5 + 1.8, label, size=5, weight="bold")

    def label(self, x, y, title, sub=None):
        self.text(x, y, title, size=4.6, weight="bold")
        if sub:
            self.text(x, y + 4.6, sub, size=3.0)

    # ---- frame & title block
    def svg(self):
        tb = []
        X0, Y0, X1, Y1 = 230, 247, 410, 287
        t = lambda *a, **k: tb.append(_t(*a, **k))
        tb.append(f'<rect class="frame" x="{X0}" y="{Y0}" width="{X1 - X0}" height="{Y1 - Y0}"/>')
        for x1, y1, x2, y2 in [(X0, 255, X1, 255), (X0, 264, X1, 264), (X0, 270, X1, 270), (330, 278.5, X1, 278.5),
                               (330, 270, 330, 287), (365, 270, 365, 287), (390, 270, 390, 287)]:
            tb.append(f'<line class="thin" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
        t(X0 + 2, 252.6, PROJECT, 3.6, "start", "bold")
        t(X0 + 2, 261.6, f"{self.title}", 4.4, "start", "bold")
        t(X0 + 2, 268.1, "Views and dimensions from SolidCraft model bancouver40_pb2.solidcraft; sheet layout generated", 2.5, "start")
        src = self.source.split(" (", 1)
        t(X0 + 2, 274.0, "SOURCE", 2.0, "start")
        t(X0 + 2, 278.2, src[0], 2.5, "start", "bold")
        if len(src) > 1:
            t(X0 + 2, 282.0, "(" + src[1], 2.1, "start")
        t(X0 + 2, 285.8, "Drawing: generated (make_sheets.py)", 2.1, "start")
        for x, cap, val in [(347.5, "SCALE", self.scale), (377.5, "DATE", DATE), (400, "SHEET", f"{self.num} / 4")]:
            t(x, 273.0, cap, 2.0, "middle")
            t(x, 277.3, val, 3.0 if len(val) < 9 else 2.2, "middle", "bold")
        t(347.5, 281.6, "UNITS", 2.0, "middle"); t(347.5, 285.8, "mm", 3.0, "middle", "bold")
        t(377.5, 281.4, "3RD ANGLE", 2.0, "middle"); t(400, 281.6, "SIZE", 2.0, "middle"); t(400, 285.8, "A3", 3.0, "middle", "bold")
        # third-angle symbol
        cx, cy = 377.5, 284.6
        tb.append(f'<line class="cl" x1="{cx - 8}" y1="{cy}" x2="{cx + 8}" y2="{cy}"/>')
        tb.append(f'<polygon class="sym" points="{cx - 7},{cy - 1.2} {cx - 2},{cy - 2.2} {cx - 2},{cy + 2.2} {cx - 7},{cy + 1.2}"/>')
        tb.append(f'<circle class="sym" cx="{cx + 4}" cy="{cy}" r="2.2"/><circle class="sym" cx="{cx + 4}" cy="{cy}" r="1.2"/>')
        tb.append(f'<line class="cl" x1="{cx + 4}" y1="{cy - 2.9}" x2="{cx + 4}" y2="{cy + 2.9}"/>')
        head = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                'width="420mm" height="297mm" viewBox="0 0 420 297">' + STYLE)
        border = '<rect class="border" x="10" y="10" width="400" height="277"/>'
        zones = []
        for i in range(8):
            x = 10 + 50 * i + 25
            zones.append(_t(x, 8.6, str(i + 1), 2.4, "middle")); zones.append(_t(x, 291.5, str(i + 1), 2.4, "middle"))
        for i, c in enumerate("ABCDEF"):
            y = 10 + 277 / 6 * i + 277 / 12 + 1
            zones.append(_t(6, y, c, 2.4, "middle")); zones.append(_t(414, y, c, 2.4, "middle"))
        return head + '<rect x="0" y="0" width="420" height="297" fill="white"/>' + border + "".join(zones) + \
            "".join(self.imgs) + "".join(self.el) + "".join(tb) + "</svg>"


def _t(x, y, s, size, anchor, weight=None):
    w = f' font-weight="{weight}"' if weight else ""
    return f'<text class="t" x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{w}>{escape(s)}</text>'


STYLE = """<style>
.t{font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;fill:#000}
.thin{stroke:#000;stroke-width:0.25}
.frame{fill:none;stroke:#000;stroke-width:0.5}
.border{fill:none;stroke:#000;stroke-width:0.7}
.ext{stroke:#1a3d8f;stroke-width:0.18}
.dim{stroke:#1a3d8f;stroke-width:0.22;fill:none}
.arr{fill:#1a3d8f;stroke:none}
.ball{fill:#fff;stroke:#1a3d8f;stroke-width:0.3}
.cl{stroke:#b02020;stroke-width:0.18;stroke-dasharray:4 1 0.8 1;fill:none}
.cut{stroke:#000;stroke-width:0.3;stroke-dasharray:8 1.5 1.5 1.5}
.cutend{stroke:#000;stroke-width:0.7}
.sym{fill:none;stroke:#000;stroke-width:0.25}
.tbl{fill:none;stroke:#000;stroke-width:0.25}
.hl{fill:#fff3c4;stroke:none}
.zl{stroke:#7a1f8f;stroke-width:0.2;stroke-dasharray:1.2 0.8}
.t.dimt{fill:#1a3d8f}
</style>"""
# dimension text in the dimension colour
STYLE = STYLE.replace(".t{font-family", ".t{font-family")


class View:
    """paper(u, v) = (ox + u k, oy - v k). kind gives how model coordinates map to (u, v)."""
    def __init__(self, kind, k, u_ref, v_ref, px, py):
        self.kind, self.k = kind, k
        self.ox, self.oy = px - u_ref * k, py + v_ref * k

    def paper_uv(self, u, v):
        return (self.ox + u * self.k, self.oy - v * self.k)

    def uv(self, a, b):
        return {"top": (a, b), "front": (a, b), "left": (-a, b), "right": (a, b), "bottom": (a, -b)}[self.kind]

    def __call__(self, a, b):
        """a, b: (x, y) for top/bottom, (x, z) front, (y, z) left/right."""
        return self.paper_uv(*self.uv(a, b))


# ---------------------------------------------------------------- measured values
L = P("Case", "x", 175.2, "case max x"); X0 = P("Case", "x", 0.0, "case min x")
W = P("Case", "y", 121.2, "case max y"); Y0 = P("Case", "y", 0.0, "case min y")
XI0, XI1 = P("Case", "x", 2.0, "inner wall x left"), P("Case", "x", 173.2, "inner wall x right")
YI0, YI1 = P("Case", "y", 2.0, "inner wall y front"), P("Case", "y", 119.2, "inner wall y back")
YST = P("Case", "y", 71.6, "wall step y")
Z0, ZF = P("Case", "z", 0.0, "case bottom z"), P("Case", "z", 1.0, "floor top z")
ZKB, ZDK = P("Case", "z", 12.5, "keyboard wall top z"), P("Case", "z", 21.1, "display wall top z")
ZBOSS = P("Case", "z", 4.5, "boss top z"); ZCB = P("Case", "z", 1.6, "standoff c'bore ceiling z")
ZUSB = P("Case", "z", 13.5, "USB-C opening bottom z")
YU0, YU1 = P("Case", "y", 85.775, "USB-C opening y0"), P("Case", "y", 99.775, "USB-C opening y1")
VX0, VX1 = P("Case", "x", 12.0, "vent x0"), P("Case", "x", 48.0, "vent x1")
VENTS = [(P("Case", "y", 79.275 + 5 * i, f"vent{i + 1} y0"), P("Case", "y", 81.275 + 5 * i, f"vent{i + 1} y1")) for i in range(6)]
RO = CYL("Case", 3.0, 3.0, 6.0, "outer corner (front-left)")[2] / 2
RI = CYL("Case", 3.0, 3.0, 2.0, "inner corner (front-left)")[2] / 2
KB = [CYL("Case", x, y, 3.6, f"kb boss {i + 1}") for i, (x, y) in enumerate([(19.6, 36.6), (53.6, 19.6), (53.6, 53.6), (121.6, 19.6), (121.6, 53.6), (155.6, 36.6)])]
KBP = [CYL("Case", b[0], b[1], 1.75, f"kb pilot {i + 1}") for i, b in enumerate(KB)]
SO_XY = [(16.225, 114.975), (164.225, 114.975), (164.225, 76.475)]
SO = [CYL("Case", x, y, 5.0, f"standoff boss {i + 1}") for i, (x, y) in enumerate(SO_XY)]
SOH = [CYL("Case", x, y, 2.4, f"standoff hole {i + 1}") for i, (x, y) in enumerate(SO_XY)]
SOC = [CYL("Case", x, y, 4.2, f"standoff cbore {i + 1}") for i, (x, y) in enumerate(SO_XY)]
RST = CYL("Case", 62.1, 49.6, 2.0, "reset hole")
# bezel
BX0, BX1 = P("Bezel", "x", 0.0, "bezel min x"), P("Bezel", "x", 175.2, "bezel max x")
BY0, BY1 = P("Bezel", "y", 71.6, "bezel front y"), P("Bezel", "y", 121.2, "bezel back y")
BZ0, BZ1 = P("Bezel", "z", 21.1, "bezel plate underside z"), P("Bezel", "z", 22.6, "bezel top z")
WX0, WX1 = P("Bezel", "x", 30.1, "window x0"), P("Bezel", "x", 141.2, "window x1")
WY0, WY1 = P("Bezel", "y", 77.515, "window y0"), P("Bezel", "y", 114.885, "window y1")
FX0, FX1 = P("Bezel", "x", 26.7, "frame outer x0"), P("Bezel", "x", 148.5, "frame outer x1")
FY0, FY1 = P("Bezel", "y", 73.915, "frame outer y0"), P("Bezel", "y", 118.485, "frame outer y1")
KX0, KX1 = P("Bezel", "x", 27.9, "panel pocket x0"), P("Bezel", "x", 147.3, "panel pocket x1")
KY0, KY1 = P("Bezel", "y", 75.115, "panel pocket y0"), P("Bezel", "y", 117.285, "panel pocket y1")
FZ = P("Bezel", "z", 18.6, "frame bottom z")
GY0, GY1 = P("Bezel", "y", 82.175, "FPC gap y0"), P("Bezel", "y", 106.175, "FPC gap y1")
SX0, SX1 = P("Bezel", "x", 2.3, "skirt x0"), P("Bezel", "x", 172.9, "skirt x1")
SY1 = P("Bezel", "y", 73.2, "skirt back y"); SZ0 = P("Bezel", "z", 6.8, "skirt bottom z")
CBZ = P("Bezel", "z", 21.6, "bezel c'bore floor z")
BH = [CYL("Bezel", x, y, 2.2, f"bezel hole {i + 1}") for i, (x, y) in enumerate(SO_XY)]
BC = [CYL("Bezel", x, y, 4.2, f"bezel cbore {i + 1}") for i, (x, y) in enumerate(SO_XY)]
BR = CYL("Bezel", 3.0, 118.2, 6.0, "bezel back corner")[2] / 2
# window chamfer: from the two straight edges bounding the front chamfer face (top edge on z = bezel top,
# lower edge on the window wall)
CH = CHZ = None
for e in TOPO["Bezel"]["edges"]:
    s0, s1 = e["start"], e["end"]
    if abs(s0[1] - s1[1]) < 1e-6 and abs(s0[2] - s1[2]) < 1e-6 and WY0 - 1.5 < s0[1] <= WY0 + 1e-6:
        if abs(s0[2] - BZ1) < 1e-6:
            CH = round(WY0 - s0[1], 4)
        elif BZ0 < s0[2] < BZ1:
            CHZ = round(BZ1 - s0[2], 4)
VALUES["window chamfer (horizontal, vertical)"] = (CH, CHZ)


# ================================================================ SHEET 1: case general arrangement
def sheet1():
    S = Sheet(1, "CASE – GENERAL ARRANGEMENT", "1:1", "bancouver40_pb2_case.step (body Case, exported from bancouver40_pb2.solidcraft)")
    top = View("top", 1, 0, 0, 185, 172)
    fr = View("front", 1, 0, 0, 185, 224)
    lf = View("left", 1, 0, 0, 155, 224)
    sd = View("right", 1, 0, 0, 30, 176)
    S.image("c_top", top); S.image("c_front", fr); S.image("c_left", lf); S.image("c_secD", sd)
    S.label(top(L / 2, 0)[0], 23, "TOP VIEW", "scale 1:1")
    S.text(fr(L / 2, 0)[0], 234.5, "FRONT VIEW", 4.0, weight="bold")
    S.text(lf(W / 2, 0)[0] + 20, 244, "LEFT VIEW", 4.0, weight="bold")
    S.label(sd(W / 2, 0)[0], 140, "SECTION D-D", "plane x = 87.6, viewed from +X")
    # iso
    h = S.image_box("c_iso", 25, 26, 110)
    S.text(80, 28 + h, "ISOMETRIC (bezel hidden)  not to scale", 3.0)
    # top view dims
    S.dim(top(X0, W), top(L, W), "h", top(0, W)[1] - 9, f(L - X0))
    S.dim(top(L, Y0), top(L, W), "v", top(L, 0)[0] + 22, f(W - Y0))
    S.dim(top(L, Y0), top(L, YST), "v", top(L, 0)[0] + 12, f(YST - Y0))
    S.dim(top(L, YST), top(L, W), "v", top(L, 0)[0] + 12, f(W - YST))
    S.text(top(L, YST)[0] + 1.5, top(L, YST)[1] - 1.2, "wall step", 2.4, "start")
    # wall thickness (left & front) and corner radii
    S.dim(top(X0, 30), top(XI0, 30), "h", top(0, 30)[1], f(XI0 - X0), tpos="right", outside=True)
    S.dim(top(100, Y0), top(100, YI0), "v", top(100, 0)[0], f(YI0 - Y0), tpos="above", outside=True)
    S.text(top(100, 0)[0] + 1.5, top(100, YI0)[1] - 8, "wall", 2.4, "start")
    S.text(top(XI0, 30)[0] + 8.5, top(XI0, 30)[1] + 3.6, "wall", 2.4, "start")
    c = top(L - RO, W - RO)
    S.leader((c[0] + RO * 0.7071, c[1] - RO * 0.7071), c[0] + 12, c[1] - 14, f"R{f(RO)} (4x outer)")
    c = top(XI1 - RI, YI0 + RI)
    S.leader((c[0] + RI * 0.7071, c[1] + RI * 0.7071), c[0] + 14, c[1] + 12, f"R{f(RI)} (4x inner)")
    S.cutline(top(87.6, W + 4), top(87.6, -4), "D", (-1, 0))
    # front view: heights
    S.dim(fr(L, Z0), fr(L, ZKB), "v", fr(L, 0)[0] + 10, f(ZKB - Z0))
    S.dim(fr(L, Z0), fr(L, ZDK), "v", fr(L, 0)[0] + 20, f(ZDK - Z0))
    S.text(fr(L, 0)[0] + 23, fr(L, ZDK)[1] + 1, "display walls", 2.4, "start")
    S.text(fr(L, 0)[0] + 23, fr(L, ZKB)[1] + 1, "keyboard walls", 2.4, "start")
    # left view: y positions
    S.dim(lf(Y0, ZDK), lf(YST, ZDK), "h", lf(0, ZDK)[1] - 6, f(YST - Y0))
    S.dim(lf(YST, ZDK), lf(W, ZDK), "h", lf(0, ZDK)[1] - 6, f(W - YST))
    S.leader(lf((YU0 + YU1) / 2, (ZUSB + ZDK) / 2), lf(70, 0)[0] - 10, 236, "USB-C opening\n(detail on sheet 2)", anchor="start", size=2.6)
    # section D-D: floor, walls, heights
    S.dim(sd(62, Z0), sd(62, ZF), "v", sd(62, 0)[0], f(ZF - Z0), tpos="below", outside=True)
    S.text(sd(62, 0)[0] + 1.5, sd(62, Z0)[1] + 9, "floor", 2.4, "start")
    S.dim(sd(Y0, 8), sd(YI0, 8), "h", sd(0, 8)[1], f(YI0 - Y0), tpos="right", outside=True)
    S.dim(sd(YI1, 16), sd(W, 16), "h", sd(0, 16)[1], f(W - YI1), tpos="left", outside=True)
    S.dim(sd(Y0, Z0), sd(Y0, ZKB), "v", sd(0, 0)[0] - 6, f(ZKB - Z0))
    S.dim(sd(W, Z0), sd(W, ZDK), "v", sd(W, 0)[0] + 9, f(ZDK - Z0))
    S.leader(sd(KB[2][1], ZBOSS), sd(70, 0)[0], sd(0, 26)[1], "bosses: see sheet 2", size=2.6)
    # notes
    notes = ["NOTES",
             "1. Origin: front-left-bottom outer corner; +Y toward the display, +Z up.",
             "2. Keyboard area walls (y < 71.6) 12.5 high; display section 21.1 high.",
             "3. Shaded views are SolidCraft orthographic renders; hidden lines not shown.",
             "4. Section D-D hatch = cut material."]
    for i, s in enumerate(notes):
        S.text(20, 262 + i * 4, s, 2.8 if i else 3.2, "start", weight="bold" if i == 0 else None)
    return S


# ================================================================ SHEET 2: case features
def sheet2():
    S = Sheet(2, "CASE – FEATURES, HOLE TABLE, DETAILS", "1:1 (details as noted)", "bancouver40_pb2_case.step (body Case)")
    top = View("top", 1, 0, 0, 30, 160)
    S.image("c_top", top)
    S.label(top(L / 2, 0)[0], 18, "TOP VIEW – FEATURE CALLOUTS", "scale 1:1")
    # origin & axes
    o = top(0, 0)
    S.line(o[0], o[1], o[0] + 12, o[1], "dim"); S.arrow(o[0] + 12, o[1], 1, 0)
    S.line(o[0], o[1], o[0], o[1] - 12, "dim"); S.arrow(o[0], o[1] - 12, 0, -1)
    S.text(o[0] + 13, o[1] + 1, "X", 2.8, "start"); S.text(o[0] - 1.5, o[1] - 13, "Y", 2.8, "middle")
    S.text(o[0] - 1, o[1] + 4, "0,0", 2.6, "end")
    rows = []
    off = {0: (-9, 7), 1: (-8, -8), 2: (-8, 8), 3: (8, -8), 4: (8, 8), 5: (9, 7)}
    for i, b in enumerate(KB):
        p = top(b[0], b[1]); S.cmark(p, b[2] / 2)
        S.balloon((p[0] + 1.27, p[1] - 1.27), p[0] + off[i][0], p[1] - off[i][1], f"A{i + 1}")
        rows.append((f"A{i + 1}", "Keyboard boss", b[0], b[1], f"Ø{f(b[2])} boss, Ø{f(KBP[i][2])} pilot (blind)", f"z {f(ZF)}–{f(ZBOSS)}; pilot DP {f(ZBOSS - ZF)}"))
    boff = {0: (9, -6), 1: (-9, -6), 2: (-9, 7)}
    for i, b in enumerate(SO):
        p = top(b[0], b[1]); S.cmark(p, b[2] / 2)
        S.balloon((p[0] - 1.77 * (1 if boff[i][0] < 0 else -1), p[1] + 1.77), p[0] + boff[i][0], p[1] - boff[i][1], f"B{i + 1}")
        rows.append((f"B{i + 1}", "Standoff boss", b[0], b[1], f"Ø{f(b[2])} boss, Ø{f(SOH[i][2])} thru, C'BORE Ø{f(SOC[i][2])} DP {f(ZCB - Z0)} from below", f"z {f(Z0)}–{f(ZBOSS)}"))
    p = top(RST[0], RST[1]); S.cmark(p, RST[2] / 2)
    S.balloon((p[0] + 0.7, p[1] + 0.7), p[0] + 8, p[1] + 7, "C")
    rows.append(("C", "Reset access hole", RST[0], RST[1], f"Ø{f(RST[2])} thru floor", f"z {f(Z0)}–{f(ZF)}"))
    for i, (y0, y1) in enumerate(VENTS):
        rows.append((f"D{i + 1}", "Floor vent slot", VX0, y0, f"{f(VX1 - VX0)} x {f(y1 - y0)} thru floor", f"x {f(VX0)}–{f(VX1)}, y {f(y0)}–{f(y1)}"))
    S.balloon(top(VX1, VENTS[5][1]), top(VX1, 0)[0] + 9, top(0, VENTS[5][1])[1] - 5, "D")
    S.text(top(VX1, 0)[0] + 13.5, top(0, VENTS[5][1])[1] - 4, "D1–D6", 2.6, "start")
    S.balloon(top(X0, (YU0 + YU1) / 2), top(0, 0)[0] - 8, top(0, W)[1] - 6, "E")
    rows.append(("E", "USB-C opening, left wall", X0, (YU0 + YU1) / 2, f"{f(YU1 - YU0)} wide, open to top", f"z {f(ZUSB)}–{f(ZDK)}, y {f(YU0)}–{f(YU1)}"))
    S.cutline(top(-4, KB[1][1]), top(L + 4, KB[1][1]), "A", (0, 1))
    S.cutline(top(-4, SO[0][1]), top(L + 4, SO[0][1]), "B", (0, 1))
    # ---- hole table
    tx, ty = 218, 18
    cols = [(0, "ID"), (8, "FEATURE"), (41, "X"), (54, "Y"), (67, "SIZE"), (148, "Z / DEPTH")]
    cw = [9, 35, 13, 13, 85, 52]
    rh = 5.2
    S.text(tx, ty, "FEATURE TABLE  (X, Y = centre from origin; vents: slot start)", 3.2, "start", weight="bold")
    ty += 2.5
    tw = 190
    S.rect(tx, ty, tw, rh * (len(rows) + 1), "tbl")
    for j, (cx, h) in enumerate(cols):
        S.text(tx + cx + 1, ty + 3.7, h, 2.6, "start", weight="bold")
        if j:
            S.line(tx + cx, ty, tx + cx, ty + rh * (len(rows) + 1), "thin")
    for i, r in enumerate(rows):
        y = ty + rh * (i + 1)
        S.line(tx, y, tx + tw, y, "thin")
        vals = [r[0], r[1], f(r[2]), f(r[3]), r[4], r[5]]
        for (cx, _), v in zip(cols, vals):
            S.text(tx + cx + 1, y + 3.7, v, 2.45 if len(v) > 34 else 2.6, "start")
    # ---- detail V (vents) 2:1
    vv = View("top", 2, -3, 111, 18, 176)
    S.image("c_vent", vv)
    S.label(vv(25.5, 0)[0], 254, "DETAIL V – FLOOR VENTS", "scale 2:1 (top view)")
    yb = VENTS[0]
    S.dim(vv(X0, yb[0]), vv(VX0, yb[0]), "h", vv(0, 75.5)[1] + 2, f(VX0 - X0))
    S.dim(vv(VX0, VENTS[5][1]), vv(VX1, VENTS[5][1]), "h", vv(0, VENTS[5][1])[1] - 6, f(VX1 - VX0))
    S.dim(vv(VX1, yb[0]), vv(VX1, yb[1]), "v", vv(VX1, 0)[0] + 8, f(yb[1] - yb[0]), outside=True, tpos="below")
    S.dim(vv(VX1, VENTS[1][0]), vv(VX1, VENTS[2][0]), "v", vv(VX1, 0)[0] + 16, f"{f(VENTS[2][0] - VENTS[1][0])} pitch")
    S.text(vv((VX0 + VX1) / 2, 0)[0], vv(0, VENTS[5][1])[1] - 13, f"6 slots, y {f(VENTS[0][0])} … {f(VENTS[5][1])}, thru floor", 2.8)
    # ---- USB-C detail 2:1 (left view)
    m = VIEWS["c_usb"]
    uv = View("left", 2, m["u"][0], m["v"][1], 140, 180)
    S.image("c_usb", uv)
    S.label(uv(92.775, 0)[0], 254, "DETAIL E – USB-C OPENING", "scale 2:1 (left view, outside of left wall)")
    S.dim(uv(YU1, ZDK), uv(YU0, ZDK), "h", uv(0, ZDK)[1] - 6, f(YU1 - YU0))
    S.dim(uv(YU0, Z0), uv(YU0, ZUSB), "v", uv(YU0, 0)[0] + 9, f(ZUSB - Z0))
    S.dim(uv(YU0, ZUSB), uv(YU0, ZDK), "v", uv(YU0, 0)[0] + 9, f(ZDK - ZUSB))
    S.line(*uv((YU0 + YU1) / 2, ZDK + 3), *uv((YU0 + YU1) / 2, Z0 - 1), "cl")
    S.text(uv((YU0 + YU1) / 2, 0)[0], uv(0, Z0)[1] + 5, f"centred y = {f((YU0 + YU1) / 2)}", 2.8)
    # ---- section A-A 5:1
    ma = VIEWS["c_secA"]
    av = View("front", 5, ma["u"][0], ma["v"][1], 228, 182)
    S.image("c_secA", av)
    S.label(av((ma["u"][0] + ma["u"][1]) / 2, 0)[0], 228, "SECTION A-A", "scale 5:1 – keyboard boss A2 (y = 19.6)")
    b = KB[1]
    S.dim(av(b[0] - b[2] / 2, ZBOSS), av(b[0] + b[2] / 2, ZBOSS), "h", av(0, ZBOSS)[1] - 7, f"Ø{f(b[2])}")
    S.dim(av(b[0] - KBP[1][2] / 2, ZBOSS), av(b[0] + KBP[1][2] / 2, ZBOSS), "h", av(0, ZBOSS)[1] - 3, f"Ø{f(KBP[1][2])}", tpos="right", outside=True)
    S.dim(av(b[0] + b[2] / 2, Z0), av(b[0] + b[2] / 2, ZBOSS), "v", av(b[0] + b[2] / 2, 0)[0] + 12, f(ZBOSS - Z0))
    S.dim(av(b[0] + b[2] / 2, ZF), av(b[0] + b[2] / 2, ZBOSS), "v", av(b[0] + b[2] / 2, 0)[0] + 5, f(ZBOSS - ZF))
    S.dim(av(49, Z0), av(49, ZF), "v", av(49, 0)[0], f(ZF - Z0), tpos="above", outside=True)
    S.line(*av(b[0], ZBOSS + 1.2), *av(b[0], Z0 - 0.5), "cl")
    # ---- section B-B 5:1
    mb = VIEWS["c_secB"]
    bv = View("front", 5, mb["u"][0], mb["v"][1], 318, 182)
    S.image("c_secB", bv)
    S.label(bv((mb["u"][0] + mb["u"][1]) / 2, 0)[0], 228, "SECTION B-B", "scale 5:1 – standoff boss B1 (y = 114.975)")
    b, hh, cb = SO[0], SOH[0], SOC[0]
    S.dim(bv(b[0] - b[2] / 2, ZBOSS), bv(b[0] + b[2] / 2, ZBOSS), "h", bv(0, ZBOSS)[1] - 7, f"Ø{f(b[2])}")
    S.dim(bv(b[0] - hh[2] / 2, ZBOSS), bv(b[0] + hh[2] / 2, ZBOSS), "h", bv(0, ZBOSS)[1] - 3, f"Ø{f(hh[2])} thru", tpos="right", outside=True)
    S.dim(bv(b[0] - cb[2] / 2, Z0), bv(b[0] + cb[2] / 2, Z0), "h", bv(0, Z0)[1] + 6, f"C'BORE Ø{f(cb[2])}")
    S.dim(bv(b[0] + cb[2] / 2, Z0), bv(b[0] + cb[2] / 2, ZCB), "v", bv(b[0] + b[2] / 2, 0)[0] + 5, f(ZCB - Z0), tpos="below", outside=True)
    S.dim(bv(b[0] + b[2] / 2, Z0), bv(b[0] + b[2] / 2, ZBOSS), "v", bv(b[0] + b[2] / 2, 0)[0] + 14, f(ZBOSS - Z0))
    S.line(*bv(b[0], ZBOSS + 1.2), *bv(b[0], Z0 - 0.5), "cl")
    S.text(bv(b[0] + b[2] / 2, 0)[0] + 7.5, bv(0, Z0)[1] + 11, "(c'bore from underside)", 2.3, "start")
    return S


# ================================================================ SHEET 3: bezel
def sheet3():
    S = Sheet(3, "BEZEL – VIEWS, WINDOW, FRAME, HOLES", "1:1 (details as noted)", "bancouver40_pb2_case.step (body Bezel)")
    top = View("top", 1, 0, BY1, 27, 37)
    fr = View("front", 1, 0, BZ1, 27, 115)
    bt = View("bottom", 1, 0, -BY0, 27, 160)
    S.image("b_top", top); S.image("b_front", fr); S.image("b_bot", bt)
    S.text(top(87.6, 0)[0], 16.5, "TOP VIEW  1:1", 4.0, weight="bold")
    S.text(fr(87.6, 0)[0], 141, "FRONT VIEW  1:1", 4.0, weight="bold")
    S.text(bt(87.6, 0)[0], 233, "UNDERSIDE (BOTTOM) VIEW  1:1", 4.0, weight="bold")
    # --- top view
    yt = top(0, BY1)[1]
    S.dim(top(BX0, BY1), top(WX0, BY1), "h", yt - 8, f(WX0 - BX0))
    S.dim(top(WX0, BY1), top(WX1, BY1), "h", yt - 8, f"{f(WX1 - WX0)} window")
    S.dim(top(WX1, BY1), top(BX1, BY1), "h", yt - 8, f(BX1 - WX1))
    S.dim(top(BX0, BY1), top(BX1, BY1), "h", yt - 15, f(BX1 - BX0))
    xl = top(BX0, 0)[0]
    S.dim(top(BX0, BY0), top(BX0, WY0), "v", xl - 6, f(WY0 - BY0), tpos="below", outside=True)
    S.dim(top(BX0, WY0), top(BX0, WY1), "v", xl - 6, f(WY1 - WY0))
    S.dim(top(BX0, WY1), top(BX0, BY1), "v", xl - 6, f(BY1 - WY1), tpos="above", outside=True)
    S.dim(top(BX1, BY0), top(BX1, BY1), "v", top(BX1, 0)[0] + 8, f(BY1 - BY0))
    wc = top((WX0 + WX1) / 2, (WY0 + WY1) / 2)
    S.line(wc[0] - 4, wc[1], wc[0] + 4, wc[1], "cl"); S.line(wc[0], wc[1] - 4, wc[0], wc[1] + 4, "cl")
    S.text(wc[0], wc[1] + 7, f"window centre ({f((WX0 + WX1) / 2)}, {f((WY0 + WY1) / 2)})", 2.8)
    S.text(wc[0], wc[1] + 11, f"edge chamfer {f(CH)} x 45° (top side)", 2.8)
    for i, h in enumerate(BH):
        S.cmark(top(h[0], h[1]), BC[i][2] / 2)
    h0 = top(BH[0][0], BH[0][1])
    S.leader((h0[0] + 1.5, h0[1] + 1.5), h0[0] + 6, h0[1] + 14, f"3x Ø{f(BH[0][2])} thru\nC'BORE Ø{f(BC[0][2])} DP {f(BZ1 - CBZ)}", size=2.6)
    # hole positions
    yb2 = top(0, BY0)[1] + 6
    S.dim(top(BX0, BH[0][1]), top(BH[0][0], BH[0][1]), "h", yb2, f(BH[0][0] - BX0))
    S.dim(top(BH[1][0], BH[1][1]), top(BX1, BH[1][1]), "h", yb2, f(BX1 - BH[1][0]))
    xr2 = top(BX1, 0)[0] + 16
    S.dim(top(BH[2][0], BY0), top(BH[2][0], BH[2][1]), "v", xr2, f(BH[2][1] - BY0), tpos="above", outside=True)
    S.dim(top(BH[1][0], BH[1][1]), top(BH[1][0], BY1), "v", xr2, f(BY1 - BH[1][1]), tpos="below", outside=True)
    # --- front view
    S.dim(fr(SX0, SZ0), fr(SX1, SZ0), "h", fr(0, SZ0)[1] + 6, f"{f(SX1 - SX0)} skirt")
    S.dim(fr(BX0, BZ0), fr(SX0, SZ0), "h", fr(0, SZ0)[1] + 6, f(SX0 - BX0), tpos="left", outside=True)
    S.dim(fr(BX1, BZ0), fr(BX1, BZ1), "v", fr(BX1, 0)[0] + 7, f(BZ1 - BZ0), tpos="above", outside=True)
    S.dim(fr(SX1, SZ0), fr(SX1, BZ0), "v", fr(BX1, 0)[0] + 7, f(BZ0 - SZ0))
    S.dim(fr(SX1, SZ0), fr(BX1, BZ1), "v", fr(BX1, 0)[0] + 15, f(BZ1 - SZ0))
    S.text(fr(BX1, 0)[0] + 2, fr(0, SZ0)[1] + 4.5, f"z {f(SZ0)}", 2.4, "start")
    # --- bottom view (frame, FPC gap, skirt)
    yb = bt(0, BY1)[1]
    S.dim(bt(BX0, BY1), bt(FX0, BY1), "h", yb + 6, f(FX0 - BX0))
    S.dim(bt(FX0, BY1), bt(FX1, BY1), "h", yb + 6, f"{f(FX1 - FX0)} frame")
    S.dim(bt(KX0, BY1), bt(KX1, BY1), "h", yb + 12, f"{f(KX1 - KX0)} pocket")
    xr = bt(BX1, 0)[0]
    S.dim(bt(FX1, GY0), bt(FX1, GY1), "v", bt(FX1, 0)[0] + 9, f"{f(GY1 - GY0)} FPC gap")
    S.dim(bt(BX1, FY0), bt(BX1, FY1), "v", xr + 7, f(FY1 - FY0))
    S.dim(bt(BX1, KY0), bt(BX1, KY1), "v", xr + 16, f"{f(KY1 - KY0)} pocket")
    S.dim(bt(KX0 - 1, BY0), bt(KX0 - 1, FY0), "v", bt(FX0, 0)[0] - 5, f(FY0 - BY0), tpos="above", outside=True)
    S.dim(bt(SX0, BY0), bt(SX0, SY1), "v", bt(SX0, 0)[0] + 9, f(SY1 - BY0), tpos="above", outside=True)
    S.text(bt(SX0, 0)[0] + 10.2, bt(0, BY0)[1] - 9, "skirt", 2.4, "start")
    S.text(bt(87.6, 0)[0], bt(0, (KY0 + KY1) / 2)[1] + 3, f"frame wall {f(KX0 - FX0)}, depth {f(BZ0 - FZ)} (z {f(FZ)}–{f(BZ0)})", 3.0)
    S.text(bt(87.6, 0)[0], bt(0, (KY0 + KY1) / 2)[1] + 7.5, f"FPC gap centred y = {f((GY0 + GY1) / 2)}", 3.0)
    S.leader(bt(BR * 0.3 + 0.88, BY1 - BR + BR * 0.7071 + 0.88), bt(BX0, 0)[0] + 6, yb + 17, f"R{f(BR)} (2x back corners)", size=2.6)
    # --- section E-E (window) 3:1
    me = VIEWS["b_secE"]
    ev = View("right", 3, me["u"][0], me["v"][1], 240, 30)
    S.image("b_secE", ev)
    S.cutline(top(60, BY1 + 1.5), top(60, BY0 - 1.5), "E", (-1, 0))
    S.label(ev((me["u"][0] + me["u"][1]) / 2, 0)[0], 98, "SECTION E-E", "scale 3:1 – plane x = 60 (through window), viewed from +X")
    S.dim(ev(WY0, BZ1), ev(WY1, BZ1), "h", ev(0, BZ1)[1] - 5, f"{f(WY1 - WY0)} window")
    S.dim(ev(FY0, FZ), ev(FY1, FZ), "h", ev(0, FZ)[1] + 13, f"{f(FY1 - FY0)} frame")
    S.dim(ev(KY0, FZ), ev(KY1, FZ), "h", ev(0, FZ)[1] + 6, f"{f(KY1 - KY0)} pocket")
    S.dim(ev(BY1, BZ0), ev(BY1, BZ1), "v", ev(BY1, 0)[0] + 6, f(BZ1 - BZ0), tpos="above", outside=True)
    S.dim(ev(BY1, FZ), ev(BY1, BZ0), "v", ev(BY1, 0)[0] + 6, f(BZ0 - FZ))
    S.dim(ev(BY0, SZ0), ev(BY0, BZ1), "v", ev(BY0, 0)[0] - 6, f(BZ1 - SZ0))
    S.dim(ev(BY0, SZ0 + 3), ev(SY1, SZ0 + 3), "h", ev(0, SZ0 + 3)[1], f(SY1 - BY0), tpos="right", outside=True)
    S.text(ev(SY1, 0)[0] + 13.5, ev(0, SZ0 + 3)[1] + 3.5, "skirt", 2.4, "start")
    S.text(ev(BY0, 0)[0] + 1, ev(0, SZ0)[1] + 4.5, "front", 2.4, "start")
    # --- detail C chamfer 10:1
    mc = VIEWS["b_detC"]
    cv = View("right", 10, mc["u"][0], mc["v"][1], 228, 112)
    S.image("b_detC", cv)
    S.label(cv((mc["u"][0] + mc["u"][1]) / 2, 0)[0], 175, "DETAIL C (of E-E)", "scale 10:1 – window edge, frame")
    S.dim(cv(WY0 - CH, BZ1), cv(WY0, BZ1), "h", cv(0, BZ1)[1] - 4, f(CH), tpos="right", outside=True)
    S.dim(cv(WY0, BZ1 - CHZ), cv(WY0, BZ1), "v", cv(WY0, 0)[0] + 6, f(CHZ), tpos="above", outside=True)
    S.text(cv(WY0, 0)[0] + 7.5, cv(0, BZ1 - CHZ)[1] + 5, "45° chamfer", 2.6, "start")
    S.dim(cv(KY0, FZ), cv(FY0, FZ), "h", cv(0, FZ)[1] + 5, f(KY0 - FY0), tpos="left", outside=True)
    S.text(cv(FY0, 0)[0] - 11, cv(0, FZ)[1] + 9.5, "frame wall", 2.4, "middle")
    S.dim(cv(KY0, FZ), cv(KY0, BZ0), "v", cv(KY0, 0)[0] + 5, f(BZ0 - FZ))
    S.dim(cv(mc["u"][0] + 0.2, BZ0), cv(mc["u"][0] + 0.2, BZ1), "v", cv(mc["u"][0], 0)[0] - 3, f(BZ1 - BZ0), tpos="above", outside=True)
    panel = BB("REF_LCD_Panel")
    S.text(cv(KY0, 0)[0] + 9, cv(0, FZ)[1] - 1, f"panel edge y {f(panel[0][1])} (assembly)", 2.3, "start")
    S.text(cv(KY0, 0)[0] + 9, cv(0, FZ)[1] + 2.3, f"→ clearance {f(panel[0][1] - KY0)} to pocket", 2.3, "start")
    # --- section F-F (bezel hole) 6:1
    mf = VIEWS["b_secF"]
    fv = View("front", 6, mf["u"][0], mf["v"][1], 330, 118)
    S.image("b_secF", fv)
    S.cutline(top(BH[0][0] - 7, BH[0][1]), top(BH[0][0] + 7, BH[0][1]), "F", (0, -1), L=4)
    S.label(fv((mf["u"][0] + mf["u"][1]) / 2, 0)[0], 160, "SECTION F-F", "scale 6:1 – bezel hole (y = 114.975)")
    h, cb = BH[0], BC[0]
    S.dim(fv(h[0] - cb[2] / 2, BZ1), fv(h[0] + cb[2] / 2, BZ1), "h", fv(0, BZ1)[1] - 5, f"C'BORE Ø{f(cb[2])}")
    S.dim(fv(h[0] - h[2] / 2, BZ0), fv(h[0] + h[2] / 2, BZ0), "h", fv(0, BZ0)[1] + 5, f"Ø{f(h[2])} thru")
    S.dim(fv(h[0] + cb[2] / 2, CBZ), fv(h[0] + cb[2] / 2, BZ1), "v", fv(mf["u"][1], 0)[0] + 3, f(BZ1 - CBZ), tpos="above", outside=True)
    S.line(*fv(h[0], BZ1 + 1), *fv(h[0], FZ - 0.3), "cl")
    # hole position table (bezel)
    tx, ty = 330, 182
    S.text(tx, ty, "BEZEL HOLES (centres, case origin)", 2.8, "start", weight="bold")
    for i, hh in enumerate(BH):
        S.text(tx, ty + 4.5 + i * 4, f"H{i + 1}:  x {f(hh[0])}   y {f(hh[1])}", 2.7, "start")
    S.text(tx, ty + 18, f"= standoff axes B1–B3 of the case", 2.5, "start")
    S.text(tx, ty + 22, f"bezel spans y {f(BY0)}–{f(BY1)}, z {f(SZ0)}–{f(BZ1)}", 2.5, "start")
    return S


# ================================================================ SHEET 4: assembly stack-up
def sheet4():
    S = Sheet(4, "ASSEMBLY – DISPLAY-SECTION STACK-UP", "4:1 / 2:1 / 1:1", "bancouver40_pb2.solidcraft (full assembly incl. official PocketBeagle 2 STEP)")
    pcb = BB("REF_PCB"); pan = BB("REF_LCD_Panel"); s1 = BB("REF_PB2_Socket1"); s2 = BB("REF_PB2_Socket2")
    brd = BB("BOARD_OUTLINE", "PB2 board (BOARD_OUTLINE)")
    soc = BB("Cut-Extrude2", "PB2 tallest part under panel (Cut-Extrude2)")
    usb = BB("Chamfer9", "PB2 USB-C receptacle (Chamfer9)")
    kc = BB("REF_Keycap"); sw = BB("REF_Switch"); so = BB("REF_Standoff1"); j3 = BB("REF_J3_FPC_Conn")
    fpc = BB("REF_FPC_Fold"); case = BB("Case"); bez = BB("Bezel")
    # lowest PB2 part below its board
    pbparts = {k: v for k, v in ASM.items() if not (k.startswith("REF") or k in ("Case", "Bezel"))}
    below = min((v["min"][2], k) for k, v in pbparts.items() if v["min"][2] > 6.2)
    VALUES["PB2 lowest bottom-side part"] = below
    mh = VIEWS["a_detH"]
    hv = View("right", 4, mh["u"][0], mh["v"][1], 18, 24)
    x0, y0, w, h = S.image("a_detH", hv)
    S.label(x0 + w / 2, y0 + h + 6, "DETAIL H – SECTION G-G, DISPLAY SECTION",
            "scale 4:1 – plane x = 48 through PocketBeagle 2 SoC and sockets, viewed from +X (front at left)")
    # z ladder on the right
    lev = [
        (bez[1][2], f"{f(bez[1][2])}  bezel top", 0), (pan[1][2], f"{f(pan[1][2])}  panel top = bezel underside = wall top", 0),
        (pan[0][2], f"{f(pan[0][2])}  LCD panel bottom", 0), (soc[1][2], f"{f(soc[1][2])}  tallest PB2 part under panel", 0),
        (brd[1][2], f"{f(brd[1][2])}  PB2 board top", 0), (brd[0][2], f"{f(brd[0][2])}  PB2 board bottom = socket top", 0),
        (pcb[1][2], f"{f(pcb[1][2])}  main PCB top = socket base", 0), (pcb[0][2], f"{f(pcb[0][2])}  main PCB bottom (boss top)", 0),
        (ZF, f"{f(ZF)}  floor top", 0), (Z0, f"{f(Z0)}  case bottom", 0)]
    xe = x0 + w
    for z, s, _ in lev:
        y = hv(0, z)[1]
        S.line(hv(118.5, z)[0], y, xe + 3, y, "zl")
        S.text(xe + 4, y + 1.0, s, 2.6, "start")
    S.text(xe + 4, y0 - 2.5, "z (mm)", 3.0, "start", weight="bold")
    gu = (soc[0][1] + soc[1][1]) / 2 - 3
    S.dim(hv(gu, pan[0][2]), hv(gu, soc[1][2]), "v", hv(gu, 0)[0], "", outside=False)
    S.text(hv(gu, 0)[0] + 1.5, hv(0, pan[0][2])[1] + 4.3, f"{f(pan[0][2] - soc[1][2])} clearance", 2.6, "start")
    S.leader(hv(90, 15.4), hv(84, 0)[0], hv(0, 9.3)[1], "PocketBeagle 2\n(official STEP)", size=2.6)
    S.leader(hv(80, 10), hv(75, 0)[0], hv(0, 2.2)[1], "8.5 mm sockets\n(REF_PB2_Socket1/2)", size=2.6, anchor="start")
    S.leader(hv(112, 5.3), hv(104, 0)[0], hv(0, 2.4)[1], "main PCB (REF_PCB)", size=2.6)
    S.leader(hv(100, 19.8), hv(98, 0)[0], y0 - 3, "LCD panel (REF_LCD_Panel)", size=2.6)
    S.leader(hv(116.2, 12), hv(118, 0)[0] + 2, hv(0, 9.5)[1], "M2 standoff\n(REF_Standoff1)", size=2.6, anchor="start")
    # z table
    tx, ty = 302, 108
    S.text(tx, ty, "Z LEVELS – MEASURED vs STATED", 3.2, "start", weight="bold")
    rows = [("Floor (Case)", f"{f(Z0)}–{f(ZF)}", "0–1"),
            ("Main PCB (REF_PCB)", f"{f(pcb[0][2])}–{f(pcb[1][2])}", "4.5–6.1"),
            ("PB2 sockets (REF)", f"{f(s1[0][2])}–{f(s1[1][2])}", "6.1–14.6"),
            ("PB2 board", f"{f(brd[0][2])}–{f(brd[1][2])}", "14.6–16.1"),
            ("PB2 tallest under panel", f"{f(soc[1][2])}", "≈17.2"),
            ("LCD panel (REF)", f"{f(pan[0][2])}–{f(pan[1][2])}", "18.6–21.1"),
            ("Bezel plate", f"{f(BZ0)}–{f(bez[1][2])}", "21.1–22.6"),
            ("Keycaps (REF) top", f"{f(kc[1][2])}", "15.6"),
            ("Switches (REF)", f"{f(sw[0][2])}–{f(sw[1][2])}", "–"),
            ("Standoffs (REF)", f"{f(so[0][2])}–{f(so[1][2])}", "6.1–21.1"),
            ("PB2 USB-C top*", f"{f(usb[1][2])}", "~19.3"),
            ("PB2 lowest part (under board)", f"{f(below[0])}", "–")]
    cw = [0, 47, 72, 92]
    rh = 4.6
    ty += 2
    S.rect(tx, ty, 106, rh * (len(rows) + 1), "tbl")
    for j, hd in enumerate(["ITEM", "MODEL z", "STATED", "OK?"]):
        S.text(tx + cw[j] + 1, ty + 3.4, hd, 2.4, "start", weight="bold")
        if j:
            S.line(tx + cw[j], ty, tx + cw[j], ty + rh * (len(rows) + 1), "thin")
    for i, (a, m_, st) in enumerate(rows):
        y = ty + rh * (i + 1)
        S.line(tx, y, tx + 106, y, "thin")
        if st == "–":
            ok = "info"
        else:
            mv = [float(v) for v in m_.split("–")]
            sv = [float(v) for v in st.lstrip("≈~").split("–")]
            d = max(abs(a_ - b_) for a_, b_ in zip(mv, sv))
            tol = 0.05 if st[0] in "≈~" else 0.0005
            ok = "yes" if d <= tol else (f"DIFF {d:+.3f}".replace("+", "") if d > 0.01 else f"≈ ({d:.3f})")
            ok = "DIFF" if ok.startswith("DIFF") else ok
        if ok != "yes" and ok != "info":
            S.add(f'<rect class="hl" x="{tx + 0.2}" y="{y + 0.2}" width="105.6" height="{rh - 0.4}"/>')
        for j, v in enumerate([a, m_, st, ok]):
            S.text(tx + cw[j] + 1, y + 3.4, v, 2.4, "start", weight="bold" if ok not in ("yes", "info") and j == 3 else None)
    yn = ty + rh * (len(rows) + 1) + 4
    notes = [f"PB2 board top measures {f(brd[1][2])} (board 1.504 thick in the STEP),",
             "  not 16.1: 0.004 mm, negligible.",
             f"Clearance tallest PB2 part → panel: {f(pan[0][2] - soc[1][2])} mm.",
             f"* USB-C top {f(usb[1][2])} is above the panel bottom but outside",
             f"  the panel footprint (x {f(usb[0][0])}–{f(usb[1][0])} vs panel x {f(pan[0][0])}–{f(pan[1][0])});",
             f"  {f(ZDK - usb[1][2])} below wall top; {f(usb[0][0] - XI0)} mm from inner wall x={f(XI0)}.",
             "PB2 STEP header bodies (z 6.1–16.6) occupy the same",
             "  space as REF_PB2_Socket1/2 (duplicate representation)."]
    for i, s in enumerate(notes):
        S.text(tx, yn + i * 3.5, s, 2.35, "start")
    # section G-G full 2:1
    mg = VIEWS["a_secG"]
    gv = View("right", 2, mg["u"][0], mg["v"][1], 18, 160)
    x0, y0, w, h = S.image("a_secG", gv)
    S.label(x0 + w / 2, y0 + h + 5, "SECTION G-G (full)", "scale 2:1 – plane x = 48, viewed from +X")
    S.leader(gv(kc[0][1] + 8, kc[1][2]), gv(kc[0][1] + 2, 0)[0], y0 - 1.5, f"keycap top z {f(kc[1][2])} (REF_Keycap)", size=2.6)
    S.leader(gv(40, 9), gv(30, 0)[0], gv(0, 26.5)[1], f"switch z {f(sw[0][2])}–{f(sw[1][2])}", size=2.6)
    S.leader(gv(YST - 0.5, ZKB), gv(YST - 4, 0)[0], gv(0, 26.5)[1], f"keyboard wall top z {f(ZKB)}", size=2.6, anchor="end")
    # section K-K 1:1
    mk = VIEWS["a_secK"]
    kv = View("front", 1, mk["u"][0], mk["v"][1], 18, 226)
    x0, y0, w, h = S.image("a_secK", kv)
    S.label(x0 + w / 2, y0 + h + 10, "SECTION K-K", "scale 1:1 – plane y = 96 (lengthwise), viewed from front")
    S.leader(kv(fpc[0][0], 15), kv(fpc[0][0], 0)[0] + 12, y0 - 2, f"folded FPC (REF) z {f(fpc[0][2])}–{f(fpc[1][2])}", size=2.4)
    S.leader(kv(j3[0][0] + 2, 7), kv(j3[0][0], 0)[0] - 6, y0 + h + 3.5, f"J3 FPC conn z {f(j3[0][2])}–{f(j3[1][2])}", size=2.4, anchor="end")
    S.leader(kv(30, 10), kv(60, 0)[0], y0 + h + 3.5, "PocketBeagle 2", size=2.4)
    return S


def main():
    sheets = [sheet1(), sheet2(), sheet3(), sheet4()]
    pages = []
    for s in sheets:
        svg = s.svg()
        open(os.path.join(HERE, f"sheet{s.num}.svg"), "w").write(svg)
        pages.append(f'<div class="page">{svg}</div>')
    html = ("<!DOCTYPE html><html><head><meta charset='utf-8'><title>bancouver40 PB2 drawings</title><style>"
            "@page{size:420mm 297mm;margin:0}html,body{margin:0;padding:0}"
            ".page{width:420mm;height:297mm;overflow:hidden;page-break-after:always;break-after:page}"
            ".page:last-child{page-break-after:auto;break-after:auto}.page svg{display:block}"
            "</style></head><body>" + "".join(pages) + "</body></html>")
    open(os.path.join(HERE, "sheets.html"), "w").write(html)
    json.dump({k: v for k, v in VALUES.items()}, open(f"{D}/values.json", "w"), indent=1, default=str)
    json.dump(MISMATCH, open(f"{D}/mismatches.json", "w"), indent=1)
    print("mismatches:", MISMATCH)


if __name__ == "__main__":
    main()
