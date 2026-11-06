# Zine Machine concept model (v3 layout): an open tray the whole assembly sits in, PocketBeagle 2 turned so its USB-C
# exits the rear wall, battery under the display (held by the display chassis), three mode
# keys right of the display, rear I/O, and keycap legends for the stock bancouver40 QMK layers.
# Case coordinates: x 0..L, y 0..W from the front-left outer corner, z up. Front faces -Y.
# Concept envelopes, not final parts.  Run with the GUI offscreen (colours):
#   H=/home/bp/opt/freecad-1.1.4; env PREFIX=$H/usr PYTHONHOME=$H/usr PATH_TO_FREECAD_LIBDIR=$H/usr/lib \
#     FONTCONFIG_FILE=/etc/fonts/fonts.conf QT_QPA_PLATFORM=offscreen $H/usr/bin/freecad mech/zine_concept.py
import os, math, FreeCAD, Part
V = FreeCAD.Vector
ROOT = '/home/bp/projects/zinemachine0/.backplane/worktrees/backplane-871755f1'
OUT = ROOT + '/mech/zine_concept'
FONTDIR = '/usr/share/fonts/truetype/dejavu/'

# ---------------- parameters (mm) ----------------
L, W, R, WALL, FLOOR = 175.2, 131.2, 3.0, 2.0, 1.0     # case: 10 mm deeper than v2 (121.2)
H_KB = 12.5                     # keyboard section wall height
Z_DECK = 21.1                   # display panel top (panel glued on the display chassis)
PCB_Z0, PCB_T = 4.5, 1.6
SOCK_H = 3.55                   # PocketBeagle 2 Industrial SMT sockets
PB2_X0, PB2_REAR = 3.125, 0.5   # PocketBeagle board left edge; its rear edge sits PB2_REAR in front of the inner rear wall
PANEL = (24.2, 143.0, 75.415, 116.985); PANEL_T = 2.5
CHASSIS_T = 1.4
J3 = (130.755, 137.505, 80.005, 108.355, 2.0)
FPC_FOLD = (137.0, 149.5, 82.175, 106.175)
BATT = (9.0, 40.0, 70.0, 4.0); BATT_X0, BATT_Y0, BATT_GAP = 43.4, 74.9, 0.5   # 0.3 mm in front of the real USB-A1 body
POSTS = [(40.8, 76.0), (40.8, 118.5), (147.5, 76.0), (147.5, 118.5)]   # display-chassis standoffs (M2)
# rear I/O: name, x0, width, depth, height, colour
IO = [('Power_switch', 44.0, 12.0, 8.0, 6.0, (0.15, 0.15, 0.15)),
      ('Jack_headset_TRRS', 59.0, 6.0, 14.0, 5.0, (0.10, 0.10, 0.10)),
      ('Jack_lineout_TRS', 68.0, 6.0, 14.0, 5.0, (0.10, 0.10, 0.10)),
      ('USB_C_charge', 78.0, 9.0, 7.5, 3.3, (0.80, 0.80, 0.83)),
      ('USB_A1', 115.8, 14.5, 13.4, 7.0, (0.75, 0.75, 0.78)),
      ('USB_A2', 130.9, 14.5, 13.4, 7.0, (0.75, 0.75, 0.78))]
KEY_X = [11.1, 28.1, 45.1, 62.1, 79.1, 96.1, 113.1, 130.1, 147.1, 164.1]
KEY_Y = [62.1, 45.1, 28.1, 11.1]          # keymap row 0 (top) .. row 3
CAP, CAP_Z0, CAP_Z1 = 16.5, 12.0, 15.6    # CFX caps
MODE_X, MODE_Y = 161.6, [118.2, 101.2, 84.2]
MODE_COL = [(0.85, 0.10, 0.10), (0.95, 0.80, 0.10), (0.10, 0.30, 0.85)]   # red, yellow, blue

# stock bancouver40 QMK default keymap (ChrisChrisLoLo/qmk_firmware, branch bancouver40)
L0 = [list('QWERTYUIOP'), list('ASDFGHJKL;'), list('ZXCVBNM,./'),
      ['Esc', 'GUI', '', 'Tab', 'Space', 'L1', 'Bksp', '', 'Alt', 'Enter']]
HOLD = {(3, 3): 'Ctrl', (3, 4): 'L2', (3, 6): 'Shift'}
L1 = [list('1234567890'), ['`', '-', '=', '[', ']', '←', '↓', '↑', '→', "'"], ['\\'] + [''] * 8 + ["'"],
      ['', '', '', '', 'L3', '', '', '\\', '', '']]
L2 = [list('!@#$%^&*()'), ['~', '_', '+', '{', '}', '←', '↓', '↑', '→', '"'], ['|'] + [''] * 8 + ['"'],
      ['', '', '', '', '', 'L3', '', '|', '', '']]
L3 = [['Boot', '', '', '', '', '', '', '', '', 'Del'], ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'Vol-', 'Vol+', '', ''],
      ['F7', 'F8', 'F9', 'F10', 'F11', 'F12', '', '', '', ''], ['', 'Swap', '', 'Unswp', '', '', '', '', '', '']]
CASE_COL, CASE_TRANSPARENCY = (0.0, 0.85, 0.95), 0      # cyan tray (transparency in percent)
C_BASE, C_L1, C_L2, C_L3 = (0.12, 0.12, 0.12), (0.10, 0.35, 0.85), (0.10, 0.60, 0.25), (0.95, 0.45, 0.05)

# ---------------- helpers ----------------
objs = []                                   # (name, shape, colour, in_open_view)
def add(name, shp, col, open_view=True):
    sols = shp.Solids if shp.ShapeType == 'Compound' and shp.Solids else [shp]   # unwrap compounds, even of one solid
    for i, s in enumerate(sols):            # one object per solid: the viewer only colours single solids
        objs.append((f'{name}_{i}' if len(sols) > 1 else name, s, col, open_view))

def rrect(x0, y0, x1, y1, r, z0, z1):
    b = Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
    return b.makeFillet(r, [e for e in b.Edges if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1e-6]) if r > 0 else b

def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))

def text(s, size, font, ax, ay, ha, va, z0, h=0.3):
    chars = Part.makeWireString(s, FONTDIR, font, size, 0)
    faces = []
    for cw in chars:
        if cw:
            try: faces.append(Part.makeFace(cw, 'Part::FaceMakerBullseye'))
            except Exception: pass
    if not faces: return []
    bb = Part.makeCompound(faces).BoundBox
    dx = {'l': ax - bb.XMin, 'r': ax - bb.XMax, 'c': ax - (bb.XMin + bb.XMax) / 2}[ha]
    dy = {'t': ay - bb.YMax, 'b': ay - bb.YMin, 'c': ay - (bb.YMin + bb.YMax) / 2}[va]
    out = []
    for f in faces:
        f = f.copy(); f.translate(V(dx, dy, z0)); out.append(f.extrude(V(0, 0, h)))
    return out

pcb_top = PCB_Z0 + PCB_T
pb2_z0 = pcb_top + SOCK_H
log = open(OUT + '.log', 'w')

# ---------------- PocketBeagle 2: face-down, USB-C to +Y (rear) ----------------
env = FreeCAD.openDocument(ROOT + '/mech/pb2_envelope.FCStd')
m = FreeCAD.Matrix(); m.rotateY(math.pi)                  # face-down: (x, y, z) -> (-x, y, -z), USB-C now -X
m2 = FreeCAD.Matrix(); m2.rotateZ(-math.pi / 2)           # -X -> +Y
pb = {o.Name: o.Shape.copy().transformGeometry(m).transformGeometry(m2) for o in env.Objects}
FreeCAD.closeDocument(env.Name)
pbb = pb['PCB'].BoundBox
shift = V(PB2_X0 - pbb.XMin, (W - WALL - PB2_REAR) - pbb.YMax, pb2_z0)
for k in pb: pb[k].translate(shift)
pcols = {'PCB': (0.72, 0.08, 0.10), 'Parts': (0.22, 0.22, 0.24), 'Headers': (0.05, 0.05, 0.05), 'USB_C': (0.80, 0.80, 0.83)}
mb = pb['USB_C_mouth'].BoundBox
log.write(f"PocketBeagle board x {pb['PCB'].BoundBox.XMin:.2f}..{pb['PCB'].BoundBox.XMax:.2f} y {pb['PCB'].BoundBox.YMin:.2f}.."
          f"{pb['PCB'].BoundBox.YMax:.2f}; USB-C mouth y {mb.YMin:.2f}, centre x {(mb.XMin+mb.XMax)/2:.2f} z {(mb.ZMin+mb.ZMax)/2:.2f}\n")

# ---------------- case ----------------
# the printed parts are their own scripts: mech/tray.py and mech/display_chassis.py (run those first)
def part_shape(name):                     # shape from a part's FCStd (STEP-read shapes lose their colours in the viewer)
    d = FreeCAD.openDocument(ROOT + f'/mech/{name}.FCStd'); shp = d.Objects[0].Shape.copy(); FreeCAD.closeDocument(d.Name)
    return shp
add('Case', part_shape('tray'), CASE_COL, open_view=False)

# ---------------- boards, display, chassis, battery ----------------
add('Main_PCB', rrect(2.6, 2.6, L - 2.6, W - 2.6, 1.0, PCB_Z0, pcb_top), (0.10, 0.45, 0.20))
for k in ('PCB', 'Parts', 'Headers', 'USB_C'):
    add('PB2_' + k, pb[k], pcols[k])
px0, px1, py0, py1 = PANEL
add('Panel', box(px0, py0, Z_DECK - PANEL_T, px1, py1, Z_DECK), (0.06, 0.06, 0.08), open_view=False)
shelf_z = Z_DECK - PANEL_T - CHASSIS_T
add('Display_chassis', part_shape('display_chassis'), (0.95, 0.75, 0.20), open_view=False)
add('J3_FPC_conn', box(J3[0], J3[2], pcb_top, J3[1], J3[3], pcb_top + J3[4]), (0.85, 0.80, 0.70))
add('FPC_fold', box(FPC_FOLD[0], FPC_FOLD[2], pcb_top + J3[4], FPC_FOLD[1], FPC_FOLD[3], Z_DECK - PANEL_T), (0.95, 0.60, 0.15))
bt, bw, bl, bp = BATT
bz = pcb_top + BATT_GAP
add('Battery', box(BATT_X0, BATT_Y0, bz, BATT_X0 + bl, BATT_Y0 + bw, bz + bt), (0.20, 0.35, 0.85))
add('Battery_PCM', box(BATT_X0 + bl, BATT_Y0, bz, BATT_X0 + bl + bp, BATT_Y0 + bw, bz + bt), (0.15, 0.20, 0.55))
for n, x0, w, d, h, c in IO:
    add(n, box(x0, W - WALL - d + 1.0, pcb_top, x0 + w, W - WALL + 1.0, pcb_top + h), c)

# ---------------- keys and legends ----------------
def cap_shape(cx, cy):
    b = Part.makeBox(CAP, CAP, CAP_Z1 - CAP_Z0, V(cx - CAP / 2, cy - CAP / 2, CAP_Z0))
    return b.makeFillet(0.8, b.Edges)
nleg = 0
for r, cy in enumerate(KEY_Y):
    for c, cx in enumerate(KEY_X):
        add(f'Switch_r{r}c{c}', box(cx - 7.5, cy - 7.5, pcb_top, cx + 7.5, cy + 7.5, CAP_Z0 - 0.5), (0.25, 0.25, 0.27))
        add(f'Cap_r{r}c{c}', cap_shape(cx, cy), (0.94, 0.93, 0.88))
        base = L0[r][c]
        legs = []
        if base:
            size = 4.5 if len(base) == 1 else (3.2 if len(base) == 2 else 2.4)
            col = C_L1 if base == 'L1' else C_BASE
            legs.append((base, size, 'DejaVuSans-Bold.ttf', cx, cy, 'c', 'c', col))
        h = HOLD.get((r, c))
        if h: legs.append((h, 1.7, 'DejaVuSans.ttf', cx - 6.2, cy - 6.2, 'l', 'b', C_L2 if h == 'L2' else C_BASE))
        l1, l2, l3 = L1[r][c], L2[r][c], L3[r][c]
        if l2 == l1: l2 = ''
        sz = lambda s: 2.2 if len(s) <= 2 else 1.7
        if l2: legs.append((l2, sz(l2), 'DejaVuSans.ttf', cx - 6.2, cy + 6.2, 'l', 't', C_L2))
        if l1: legs.append((l1, sz(l1), 'DejaVuSans.ttf', cx + 6.2, cy + 6.2, 'r', 't', C_L1))
        if l3: legs.append((l3, sz(l3), 'DejaVuSans.ttf', cx + 6.2, cy - 6.2, 'r', 'b', C_L3))
        for j, (s, size, font, ax, ay, ha, va, col) in enumerate(legs):
            sols = text(s, size, font, ax, ay, ha, va, CAP_Z1)
            if sols:
                add(f'Legend_r{r}c{c}_{j}', Part.makeCompound(sols), col); nleg += 1
for i, (cy, col) in enumerate(zip(MODE_Y, MODE_COL)):
    add(f'Mode_switch{i+1}', box(MODE_X - 7.5, cy - 7.5, pcb_top, MODE_X + 7.5, cy + 7.5, CAP_Z0 - 0.5), (0.25, 0.25, 0.27))
    add(f'Mode_key{i+1}', cap_shape(MODE_X, cy), col)

# ---------------- checks ----------------
named = {}
for n, s, c, ov in objs:
    named.setdefault(n.rsplit('_', 1)[0] if n.split('_')[-1].isdigit() and n.startswith(('PB2_Parts', 'PB2_Headers', 'PB2_USB_C')) else n, []).append(s)
grp = {k: Part.makeCompound(v) for k, v in named.items()}
inside = ['PB2_PCB', 'PB2_Parts', 'PB2_Headers', 'PB2_USB_C', 'Battery', 'Battery_PCM', 'J3_FPC_conn', 'FPC_fold',
          'Display_chassis', 'Panel'] + [n for n, *_ in IO] + \
         [f'Mode_switch{i+1}' for i in range(3)] + [f'Mode_key{i+1}' for i in range(3)]
for i in range(len(inside)):
    for j in range(i + 1, len(inside)):
        a, b = inside[i], inside[j]
        if {a, b} <= {'PB2_PCB', 'PB2_Parts', 'PB2_Headers', 'PB2_USB_C'} or {a, b} in ({'Battery', 'Battery_PCM'},
                {'Panel', 'Display_chassis'}, {'J3_FPC_conn', 'FPC_fold'}, {'Panel', 'FPC_fold'}, {'Display_chassis', 'FPC_fold'}):
            continue
        d = grp[a].distToShape(grp[b])[0]
        if d < 0.5: log.write(f"{'CLASH' if d < 1e-6 else 'close'} {a} - {b}: {d:.2f} mm\n")
for k in inside + ['Main_PCB']:
    v = grp[k].common(grp['Case']).Volume
    if v > 0.05: log.write(f"in case wall: {k} {v:.1f} mm3\n")
top = max(grp[k].BoundBox.ZMax for k in ('PB2_Parts', 'PB2_USB_C'))
log.write(f"PocketBeagle top z {top:.2f}; battery top {bz + bt:.2f} under chassis {shelf_z:.2f}\n"
          f"legends {nleg}; objects {len(objs)}; tray {L} x {W} x {H_KB} mm, device {Z_DECK:.1f} mm tall\n")

# ---------------- export ----------------
doc = FreeCAD.newDocument('zine_concept')
fobjs = []
for n, s, c, ov in objs:
    o = doc.addObject('Part::Feature', n); o.Shape = s; fobjs.append((o, c, ov))
doc.recompute()
if FreeCAD.GuiUp:
    for o, c, ov in fobjs:
        o.ViewObject.ShapeColor = c
        if o.Name == 'Case': o.ViewObject.Transparency = CASE_TRANSPARENCY
doc.saveAs(OUT + '.FCStd')
if FreeCAD.GuiUp:
    import ImportGui
    ImportGui.export([o for o, c, ov in fobjs], OUT + '.step')
    ImportGui.export([o for o, c, ov in fobjs if ov], OUT + '_open.step')
    ImportGui.export([o for o, c, ov in fobjs], OUT + '.glb')          # GLB keeps the case's transparency
    # exploded view: each layer lifted straight up by its offset (mm)
    EXPLODE = [('Case', 0), ('Main_PCB', 30), ('USB_A', 30), ('USB_C_charge', 30), ('Power_switch', 30), ('Jack', 30),
               ('J3', 30), ('Switch_', 45), ('Mode_switch', 45), ('PB2_', 50), ('Battery', 55), ('Cap_', 65),
               ('Legend_', 65), ('Mode_key', 65), ('Chassis_post', 75), ('FPC_fold', 85), ('Display_chassis', 95),
               ('Panel', 110)]
    xobjs = []
    for o, c, ov in fobjs:
        dz = next(v for k, v in EXPLODE if o.Name.startswith(k))
        s = o.Shape.copy(); s.translate(V(0, 0, dz))
        x = doc.addObject('Part::Feature', 'X_' + o.Name); x.Shape = s
        x.ViewObject.ShapeColor = c
        if o.Name == 'Case': x.ViewObject.Transparency = CASE_TRANSPARENCY
        x.ViewObject.Visibility = False; xobjs.append(x)
    ImportGui.export(xobjs, OUT + '_exploded.glb')
    ImportGui.export(xobjs, OUT + '_exploded.step')
log.close()
if FreeCAD.GuiUp:
    os._exit(0)
