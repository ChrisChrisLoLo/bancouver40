# Tray: open 3D-printed tray the whole Zine Machine assembly sits in. Main board on bosses (bottom at z 4.5),
# rear wall with openings for the PocketBeagle's USB-C and the rear I/O.
# Case coordinates: x 0..L, y 0..W from the front-left outer corner, z up from the underside. Front faces -Y.
# Run (GUI offscreen for colours):
#   H=/home/bp/opt/freecad-1.1.4; env PREFIX=$H/usr PYTHONHOME=$H/usr PATH_TO_FREECAD_LIBDIR=$H/usr/lib \
#     FONTCONFIG_FILE=/etc/fonts/fonts.conf QT_QPA_PLATFORM=offscreen $H/usr/bin/freecad mech/tray.py
import os, FreeCAD, Part
V = FreeCAD.Vector
OUT = '/home/bp/projects/zinemachine0/.backplane/worktrees/backplane-871755f1/mech/tray'

# ---------------- parameters (mm) ----------------
L, W, H, R, WALL, FLOOR = 175.2, 131.2, 12.5, 3.0, 2.0, 1.0
PCB_Z0 = 4.5                          # main board underside
PCB_TOP = 6.1
# keyboard-area bosses: M2 self-tapping from the top, through the board (unchanged bancouver40 positions)
KB_BOSSES = [(19.6, 36.6), (53.6, 19.6), (53.6, 53.6), (121.6, 19.6), (121.6, 53.6), (155.6, 36.6)]
KB_BOSS_D, KB_PILOT_D = 3.6, 1.75
# display-chassis posts: M2 screws from below, through tray and board, into the chassis posts
CH_BOSSES = [(40.8, 76.0), (40.8, 118.5), (147.5, 76.0), (147.5, 118.5)]
CH_BOSS_D, CH_CLEAR_D, CH_HEAD_D, CH_HEAD_H = 5.0, 2.4, 4.2, 1.2   # through hole + head counterbore in the floor
# rear openings: (x0, x1, z0, z1); PocketBeagle USB-C centred at x 20.65, z 12.75 (a notch in the wall top)
PB2_USBC = (20.65 - 5.5, 20.65 + 5.5, 12.75 - 2.4, H + 1)
IO = [('Power_switch', 44.0, 12.0, 6.0), ('Jack_headset_TRRS', 59.0, 6.0, 5.0), ('Jack_lineout_TRS', 68.0, 6.0, 5.0),
      ('USB_C_charge', 78.0, 9.0, 3.3), ('USB_A1', 115.8, 14.5, 7.0), ('USB_A2', 130.9, 14.5, 7.0)]   # GCT USB1046: 14.5 mm flange, 7.0 mm tall
IO_FIT = 0.3
COLOUR = (0.0, 0.85, 0.95)

def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))

def rrect(x0, y0, x1, y1, r, z0, z1):
    b = box(x0, y0, z0, x1, y1, z1)
    return b.makeFillet(r, [e for e in b.Edges if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1e-6])

tray = rrect(0, 0, L, W, R, 0, H).cut(rrect(WALL, WALL, L - WALL, W - WALL, R - WALL + 0.5, FLOOR, H + 1))
for x, y in KB_BOSSES:
    tray = tray.fuse(Part.makeCylinder(KB_BOSS_D / 2, PCB_Z0 - FLOOR + 0.01, V(x, y, FLOOR - 0.01)))
for x, y in CH_BOSSES:
    tray = tray.fuse(Part.makeCylinder(CH_BOSS_D / 2, PCB_Z0 - FLOOR + 0.01, V(x, y, FLOOR - 0.01)))
for x, y in KB_BOSSES:
    tray = tray.cut(Part.makeCylinder(KB_PILOT_D / 2, PCB_Z0 - FLOOR, V(x, y, FLOOR + 0.3)))
for x, y in CH_BOSSES:
    tray = tray.cut(Part.makeCylinder(CH_CLEAR_D / 2, PCB_Z0 + 1, V(x, y, -0.5)))
    tray = tray.cut(Part.makeCylinder(CH_HEAD_D / 2, CH_HEAD_H + 0.5, V(x, y, -0.5)))
x0, x1, z0, z1 = PB2_USBC
tray = tray.cut(box(x0, W - WALL - 1, z0, x1, W + 1, z1))
for n, xo, w, h in IO:
    zb = PCB_TOP - IO_FIT
    tray = tray.cut(box(xo - IO_FIT, W - WALL - 1, zb, xo + w + IO_FIT, W + 1, PCB_TOP + h + IO_FIT))
tray = tray.removeSplitter()

bb = tray.BoundBox
log = open(OUT + '.log', 'w')
log.write(f"valid {tray.isValid()} solids {len(tray.Solids)} volume {tray.Volume/1000:.2f} cm3 area {tray.Area/100:.1f} cm2 "
          f"size {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f}\n")
doc = FreeCAD.newDocument('tray')
o = doc.addObject('Part::Feature', 'Tray'); o.Shape = tray
doc.recompute()
doc.saveAs(OUT + '.FCStd')
if FreeCAD.GuiUp:
    o.ViewObject.ShapeColor = COLOUR
    import ImportGui; ImportGui.export([o], OUT + '.step')
else:
    import Import; Import.export([o], OUT + '.step')
log.close()
if FreeCAD.GuiUp:
    os._exit(0)
