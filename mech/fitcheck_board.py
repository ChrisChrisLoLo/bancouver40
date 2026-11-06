# Fit check of the real main board (KiCad STEP export) against the tray, display chassis, battery, panel, panel tail
# and the PocketBeagle envelope from mech/zine_concept.FCStd (run zine_concept.py first).
# Board STEP frame: x = KiCad x, y = -KiCad y, z = 0 at the board bottom -> case: (x - 71.775, y + 85.475, z + 4.5).
# Run with the GUI offscreen:
#   H=/home/bp/opt/freecad-1.1.4; env PREFIX=$H/usr PYTHONHOME=$H/usr PATH_TO_FREECAD_LIBDIR=$H/usr/lib \
#     FONTCONFIG_FILE=/etc/fonts/fonts.conf QT_QPA_PLATFORM=offscreen $H/usr/bin/freecad mech/fitcheck_board.py
import os, FreeCAD, Part
V = FreeCAD.Vector
ROOT = '/home/bp/projects/zinemachine0/.backplane/worktrees/backplane-871755f1'
BOARD_STEP = '/home/bp/projects/zinemachine0/.backplane/worktrees/backplane-07566bdf/pcb/bancouver40_pb2/build/board.step'
OUT = ROOT + '/mech/fitcheck_board'
SHIFT = V(-71.775, 85.475, 4.5)
NEAR = 0.3                      # report anything closer than this
MECH = ['Case', 'Display_chassis', 'Battery', 'Battery_PCM', 'Panel', 'FPC_fold', 'PB2_PCB', 'PB2_Parts', 'PB2_USB_C']

log = open(OUT + '.log', 'w')
cdoc = FreeCAD.openDocument(ROOT + '/mech/zine_concept.FCStd')
mech = {}
for o in cdoc.Objects:
    if o.Name.startswith('X_'): continue
    base = next((m for m in MECH if o.Name == m or o.Name.startswith(m + '_')), None)
    if base: mech.setdefault(base, []).append(o.Shape)
mech = {k: Part.makeCompound(v) for k, v in mech.items()}
cols = {o.Name: o.ViewObject.ShapeColor for o in cdoc.Objects} if FreeCAD.GuiUp else {}

import ImportGui
bdoc = FreeCAD.newDocument('board')
ImportGui.insert(BOARD_STEP, bdoc.Name)
parts = []
for o in bdoc.Objects:
    if o.TypeId == 'Part::Feature' and not o.Shape.isNull() and o.Shape.Solids:
        s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); s.translate(SHIFT)   # parts sit in App::Part containers
        parts.append((o.Label, s, o))
log.write(f"board objects with solids: {len(parts)}\n")

pcb_like = [p for p in parts if p[1].BoundBox.XLength > 150]
for label, s, o in parts:
    for k, m in mech.items():
        if not s.BoundBox.intersect(m.BoundBox):
            continue
        if k == 'Battery' and s.BoundBox.XLength > 150: continue          # the bare board under the foam pad
        d = s.distToShape(m)[0]
        if d < NEAR:
            v = s.common(m).Volume if d < 1e-6 else 0.0
            if d < 1e-6 and v < 1e-3 and (s.BoundBox.XLength > 150 or k in ('Case',)):
                continue                                                 # face contact: board on its bosses
            bb = s.BoundBox
            log.write(f"{'CLASH' if v > 1e-3 else ('touch' if d < 1e-6 else 'close')} {label} - {k}: "
                      f"{('%.2f mm3' % v) if v > 1e-3 else ('%.2f mm' % d)}  at KiCad x {bb.XMin+71.775:.1f}..{bb.XMax+71.775:.1f}, "
                      f"y {85.475-bb.YMax:.1f}..{85.475-bb.YMin:.1f}, z {bb.ZMin:.1f}..{bb.ZMax:.1f}\n")
log.write("done\n")

# assembly for viewing: board parts + mechanics
adoc = FreeCAD.newDocument('fit')
objs = []
for label, s, o in parts:
    for i, sol in enumerate(s.Solids):
        a = adoc.addObject('Part::Feature', 'B_' + ''.join(ch if ch.isalnum() else '_' for ch in label)[:40]); a.Shape = sol
        objs.append((a, o.ViewObject.ShapeColor if FreeCAD.GuiUp else (0.5, 0.5, 0.5)))
for k in ('Case', 'Display_chassis', 'Battery', 'Panel', 'PB2_PCB', 'PB2_USB_C'):
    for i, sol in enumerate(mech[k].Solids):
        a = adoc.addObject('Part::Feature', f'{k}_{i}'); a.Shape = sol
        objs.append((a, cols.get(k, cols.get(f'{k}_0', (0.6, 0.6, 0.6)))))
# finished look: the real board plus keycaps, legends, mode keys and the PocketBeagle from the concept model
dressed = []
for o in cdoc.Objects:
    if o.Name.startswith(('Cap_', 'Legend_', 'Mode_key', 'PB2_Parts', 'PB2_Headers')) and not o.Name.startswith('X_'):
        a = adoc.addObject('Part::Feature', 'K_' + o.Name); a.Shape = o.Shape.copy()
        dressed.append((a, o.ViewObject.ShapeColor if FreeCAD.GuiUp else (0.5, 0.5, 0.5)))
adoc.recompute()
if FreeCAD.GuiUp:
    for a, c in objs + dressed: a.ViewObject.ShapeColor = c[:3]
    ImportGui.export([a for a, c in objs + dressed], OUT + '_full.glb')
    ImportGui.export([a for a, c in objs + dressed], OUT + '_full.step')
    for a, c in objs: a.ViewObject.ShapeColor = c[:3]
    ImportGui.export([a for a, c in objs], OUT + '.glb')
    ImportGui.export([a for a, c in objs if not a.Name.startswith(('Panel', 'Display_chassis'))], OUT + '_open.step')
log.close()
if FreeCAD.GuiUp:
    os._exit(0)
