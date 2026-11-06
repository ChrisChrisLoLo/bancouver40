# Display chassis: 3D-printed carrier the 4.58" bar panel sits in (taped into a flush frame), which also boxes and
# clamps the LiPo pouch under the display. Stands on four posts on the main board; M2 screws come up from under the
# tray, through the board, into the posts.  Case coordinates (x right, y to the rear, z up from the tray floor's
# underside), same as mech/zine_concept.py.  Front faces -Y.
# Run (GUI offscreen for colours):
#   H=/home/bp/opt/freecad-1.1.4; env PREFIX=$H/usr PYTHONHOME=$H/usr PATH_TO_FREECAD_LIBDIR=$H/usr/lib \
#     FONTCONFIG_FILE=/etc/fonts/fonts.conf QT_QPA_PLATFORM=offscreen $H/usr/bin/freecad mech/display_chassis.py
import os, FreeCAD, Part
V = FreeCAD.Vector
OUT = '/home/bp/projects/zinemachine0/.backplane/worktrees/backplane-871755f1/mech/display_chassis'

# ---------------- parameters (mm) ----------------
PCB_TOP = 6.1                          # main board top
PANEL = (24.2, 143.0, 75.415, 116.985) # panel x0, x1, y0, y1 (118.8 x 41.57)
PANEL_Z0, PANEL_T = 18.6, 2.5          # panel bottom, thickness
FIT = 0.25                             # panel-to-frame clearance per side
SHELF_T = 1.4                          # shelf under the panel
FRAME_W = 1.6                          # frame wall around the panel (flush with the panel top)
SHELF_X0, SHELF_X1, SHELF_Y0, SHELF_Y1 = 22.5, 149.5, 74.0, 120.5
FPC_Y0, FPC_Y1 = 82.0, 106.4           # panel tail band: frame and shelf open east of the panel here
POSTS = [(40.8, 76.0), (40.8, 118.5), (147.5, 76.0), (147.5, 118.5)]
POST_D, PILOT_D, PILOT_DEPTH = 4.4, 1.6, 8.0   # M2 self-tapping from below
BATT = (43.4, 117.4, 74.9, 114.9)      # battery + protection board footprint x0, x1, y0, y1
BATT_TOP = 15.6                        # 0.5 mm foam + 9 mm cell on the board
BATT_FIT, FENCE_T, FENCE_Z0 = 0.5, 1.2, 8.5    # fence around the cell, its bottom edge (2.4 mm above the board)
RIB_W, RIB_PRELOAD = 2.0, 0.1          # ribs pressing on the cell (into the foam)
LEAD_SLOT = (2.0, 12.0)                # battery-lead slot in the east fence wall: z height from the bottom, width
# rear USB-A receptacles (x0, x1, y0, z1): the chassis keeps KEEPOUT_GAP clear of them
USB_A = [(115.8, 130.3, 115.2, 13.1), (130.9, 145.4, 115.2, 13.1),   # rear I/O to keep clear of: GCT USB1046 USB-A (body + flange, from the board STEP)
         (59.0, 65.0, 116.2, 11.1), (68.0, 74.0, 116.2, 11.1)]           # 3.5 mm jacks, 14 mm long
KEEPOUT_GAP = 0.5
COLOUR = (0.95, 0.75, 0.20)

def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))

shelf_z0 = PANEL_Z0 - SHELF_T
ztop = PANEL_Z0 + PANEL_T
px0, px1, py0, py1 = PANEL
# shelf + flush frame, open at the panel tail
body = box(SHELF_X0, SHELF_Y0, shelf_z0, SHELF_X1, SHELF_Y1, PANEL_Z0)
body = body.fuse(box(px0 - FIT - FRAME_W, py0 - FIT - FRAME_W, PANEL_Z0, px1 + FIT + FRAME_W, py1 + FIT + FRAME_W, ztop))
body = body.cut(box(px0 - FIT, py0 - FIT, PANEL_Z0, px1 + FIT, py1 + FIT, ztop + 1))           # panel pocket
body = body.cut(box(px1 - 1.0, FPC_Y0, shelf_z0 - 1, SHELF_X1 + 1, FPC_Y1, ztop + 1))          # tail exit
# posts
for x, y in POSTS:
    body = body.fuse(Part.makeCylinder(POST_D / 2, shelf_z0 - PCB_TOP + 0.01, V(x, y, PCB_TOP)))
# battery fence and ribs
bx0, bx1, by0, by1 = BATT
fx0, fx1, fy0, fy1 = bx0 - BATT_FIT, bx1 + BATT_FIT, by0 - BATT_FIT, by1 + BATT_FIT
fence = box(fx0 - FENCE_T, fy0 - FENCE_T, FENCE_Z0, fx1 + FENCE_T, fy1 + FENCE_T, shelf_z0 + 0.01).cut(
    box(fx0, fy0, FENCE_Z0 - 1, fx1, fy1, shelf_z0 + 1))
fence = fence.cut(box(fx1 - 1, (fy0 + fy1) / 2 - LEAD_SLOT[1] / 2, FENCE_Z0 - 1, fx1 + FENCE_T + 1,
                      (fy0 + fy1) / 2 + LEAD_SLOT[1] / 2, FENCE_Z0 + LEAD_SLOT[0]))
body = body.fuse(fence)
rib_z0 = BATT_TOP - RIB_PRELOAD
for f in (0.25, 0.5, 0.75):
    x = bx0 + f * (bx1 - bx0)
    body = body.fuse(box(x - RIB_W / 2, by0 + 3, rib_z0, x + RIB_W / 2, by1 - 3, shelf_z0 + 0.01))
# pilot holes from below
for x, y in POSTS:
    body = body.cut(Part.makeCylinder(PILOT_D / 2, PILOT_DEPTH, V(x, y, PCB_TOP - 0.01)))
for x0, x1, y0, z1 in USB_A:
    g = KEEPOUT_GAP
    body = body.cut(box(x0 - g, y0 - g, PCB_TOP - 1, x1 + g, SHELF_Y1 + 5, z1 + g))
body = body.removeSplitter()

log = open(OUT + '.log', 'w')
log.write(f"valid {body.isValid()} solids {len(body.Solids)} volume {body.Volume/1000:.2f} cm3 area {body.Area/100:.1f} cm2 "
          f"bbox {body.BoundBox}\n")
doc = FreeCAD.newDocument('display_chassis')
o = doc.addObject('Part::Feature', 'Display_chassis'); o.Shape = body
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
