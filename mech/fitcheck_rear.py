# Rear-section fit check for the Zine Machine redesign: battery under the display, held by the display chassis.
# Case coordinates (as tools/pocketbeagle2/case_v2.py): x 0..175.2, y 0..121.2 from the front-left outer corner, z up.
# KiCad (kx, ky) -> case (kx - 71.775, 85.475 - ky).  Blocks are envelopes, not final parts.
# Run (GUI offscreen for colours):
#   H=/home/bp/opt/freecad-1.1.4; env PREFIX=$H/usr PYTHONHOME=$H/usr PATH_TO_FREECAD_LIBDIR=$H/usr/lib \
#     FONTCONFIG_FILE=/etc/fonts/fonts.conf QT_QPA_PLATFORM=offscreen $H/usr/bin/freecad mech/fitcheck_rear.py
import os, FreeCAD, Part
V = FreeCAD.Vector
ROOT = '/home/bp/projects/zinemachine0/.backplane/worktrees/backplane-871755f1'
OUT = ROOT + '/mech/fitcheck_rear'

# --- parameters (mm) ---
L, W, WALL = 175.2, 121.2, 2.0
REAR_Y0 = 71.6                    # raised rear section starts here (divider wall 71.6..73.2)
PCB_Z0, PCB_T = 4.5, 1.6          # main board
PCB_X0, PCB_Y0, PCB_W, PCB_H = 2.6, 2.6, 170.0, 116.0
SOCK_H = 3.55                     # PocketBeagle 2 Industrial SMT sockets
PB2_X0, PB2_Y0 = 3.125, 75.275    # PocketBeagle board corner (55 x 35), rotated so its USB-C faces the left wall
PANEL = (28.2, 147.0, 75.415, 116.985)   # x0, x1, y0, y1 of the 118.8 x 41.57 panel
PANEL_T, Z_DECK = 2.5, 21.1       # panel glued under the bezel; bezel top 22.6
CHASSIS_T = 1.4                   # display chassis shelf under the panel
J3 = (134.755, 141.505, 80.005, 108.355, 2.0)   # FPC connector x0, x1, y0, y1, height
FPC_FOLD = (141.0, 153.5, 82.175, 106.175)      # x0, x1, y0, y1 of the folded panel tail (z PCB top..panel)
BATT = (9.0, 40.0, 70.0, 4.0)     # thickness, width, length, + protection board on one end
BATT_X0, BATT_Y0, BATT_GAP = 60.0, 76.0, 0.5    # battery corner, gap above the board (foam pad)
USBA = (13.1, 14.0, 5.7, 2)       # right-angle USB-A receptacle W, depth, height, count (rear wall)
USBA_X0, USBA_GAP = 144.0, 2.0
STANDOFFS = [(88 - 71.775, 85.475 + 29.5), (236 - 71.775, 85.475 + 29.5), (236 - 71.775, 85.475 - 9.0)]  # current H11-H13

pcb_top = PCB_Z0 + PCB_T
pb2_z0 = pcb_top + SOCK_H                      # PocketBeagle PCB socket-side face
objs = []
def add(name, shp, col):
    objs.append((name, shp, col))

case = Part.read(ROOT + '/case/pocketbeagle2/bancouver40_pb2_case.step')
add('Case', case, (0.93, 0.93, 0.90))
add('Main_PCB', Part.makeBox(PCB_W, PCB_H, PCB_T, V(PCB_X0, PCB_Y0, PCB_Z0)), (0.10, 0.45, 0.20))

# PocketBeagle envelope: model (x, y, z) -> (-x + tx, y + ty, pb2_z0 - z): face-down, USB-C to -X
env = FreeCAD.openDocument(ROOT + '/mech/pb2_envelope.FCStd')
tx, ty = PB2_X0 - 277.368, PB2_Y0 - 269.394
m = FreeCAD.Matrix(); m.rotateY(3.141592653589793)          # (x,y,z) -> (-x, y, -z)
pcols = {'PCB': (0.72, 0.08, 0.10), 'Parts': (0.22, 0.22, 0.24), 'Headers': (0.05, 0.05, 0.05),
         'USB_C': (0.80, 0.80, 0.83), 'USB_C_mouth': (1.0, 0.55, 0.0), 'USB_C_plug': (1.0, 0.70, 0.30)}
for o in env.Objects:
    s = o.Shape.copy(); s = s.transformGeometry(m); s.translate(V(tx, ty, pb2_z0))
    add('PB2_' + o.Name, s, pcols[o.Name])
FreeCAD.closeDocument(env.Name)

px0, px1, py0, py1 = PANEL
add('Panel', Part.makeBox(px1 - px0, py1 - py0, PANEL_T, V(px0, py0, Z_DECK - PANEL_T)), (0.08, 0.08, 0.10))
add('Chassis_shelf', Part.makeBox(px1 - px0 + 4, py1 - py0 + 2, CHASSIS_T, V(px0 - 2, py0 - 1, Z_DECK - PANEL_T - CHASSIS_T)),
    (0.95, 0.75, 0.20))
add('J3_FPC_conn', Part.makeBox(J3[1] - J3[0], J3[3] - J3[2], J3[4], V(J3[0], J3[2], pcb_top)), (0.85, 0.80, 0.70))
add('FPC_fold', Part.makeBox(FPC_FOLD[1] - FPC_FOLD[0], FPC_FOLD[3] - FPC_FOLD[2], Z_DECK - PANEL_T - pcb_top,
                             V(FPC_FOLD[0], FPC_FOLD[2], pcb_top)), (0.95, 0.60, 0.15))
bt, bw, bl, bp = BATT
add('Battery', Part.makeBox(bl, bw, bt, V(BATT_X0, BATT_Y0, pcb_top + BATT_GAP)), (0.20, 0.35, 0.85))
add('Battery_PCM', Part.makeBox(bp, bw, bt, V(BATT_X0 + bl, BATT_Y0, pcb_top + BATT_GAP)), (0.15, 0.20, 0.55))
uw, ud, uh, un = USBA
for i in range(un):
    x = USBA_X0 + i * (uw + USBA_GAP)
    add(f'USB_A{i+1}', Part.makeBox(uw, ud, uh, V(x, W - WALL - ud + 1.0, pcb_top)), (0.75, 0.75, 0.78))
for i, (x, y) in enumerate(STANDOFFS):
    add(f'Standoff{i+1}', Part.makeCylinder(2.0, Z_DECK - pcb_top, V(x, y, pcb_top)), (0.80, 0.70, 0.30))

doc = FreeCAD.newDocument('fitcheck_rear')
fobjs = []
for name, shp, col in objs:
    o = doc.addObject('Part::Feature', name); o.Shape = shp; fobjs.append(o)
doc.recompute()
if FreeCAD.GuiUp:
    for (name, shp, col), o in zip(objs, fobjs):
        o.ViewObject.ShapeColor = col

# clearance report: every pair of interior objects (case excluded), plus the battery vs case
log = open(OUT + '.log', 'w')
inner = [(n, s) for n, s, c in objs if n not in ('Case', 'PB2_USB_C_mouth', 'PB2_USB_C_plug')]
for i in range(len(inner)):
    for j in range(i + 1, len(inner)):
        a, b = inner[i], inner[j]
        if {a[0], b[0]} & {'Main_PCB'} and ('Standoff' in a[0] + b[0] or 'PB2' in a[0] + b[0]): continue
        if a[0].startswith('PB2') and b[0].startswith('PB2'): continue
        d = a[1].distToShape(b[1])[0]
        if d < 1.0:
            log.write(f"{'CLASH' if d < 1e-6 else 'close'} {a[0]} - {b[0]}: {d:.2f} mm\n")
for n, s, c in objs:
    if n in ('Battery', 'Battery_PCM', 'USB_A1', 'USB_A2', 'Chassis_shelf', 'FPC_fold'):
        v = s.common(case).Volume
        if v > 1e-3: log.write(f"CLASH {n} - Case: {v:.1f} mm3\n")
# battery free space: distances from the battery to its neighbours
bb = [s for n, s, c in objs if n == 'Battery'][0]
for n, s, c in objs:
    if n in ('PB2_Parts', 'PB2_PCB', 'J3_FPC_conn', 'Chassis_shelf', 'USB_A1', 'USB_A2', 'Standoff1', 'PB2_USB_C', 'PB2_Headers'):
        log.write(f"battery to {n}: {bb.distToShape(s)[0]:.2f} mm\n")
pz = [s for n, s, c in objs if n in ('PB2_Parts', 'PB2_USB_C')]
log.write(f"PocketBeagle top (z): {max(s.BoundBox.ZMax for s in pz):.2f}; panel bottom {Z_DECK - PANEL_T:.2f}; "
          f"chassis bottom {Z_DECK - PANEL_T - CHASSIS_T:.2f}; battery top {pcb_top + BATT_GAP + bt:.2f}\n")
doc.saveAs(OUT + '.FCStd')
if FreeCAD.GuiUp:
    import ImportGui; ImportGui.export(fobjs, OUT + '.step')
    # open view: no case, panel or chassis, to see what sits under the display
    ImportGui.export([o for o in fobjs if o.Name not in ('Case', 'Panel', 'Chassis_shelf')], OUT + '_open.step')
else:
    import Import; Import.export(fobjs, OUT + '.step')
log.close()
if FreeCAD.GuiUp:
    os._exit(0)
