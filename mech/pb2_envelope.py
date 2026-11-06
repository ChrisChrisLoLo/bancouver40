# PocketBeagle 2 Industrial (Rev A layout) -- light model for interference checks and port cut-outs.
# Built from BeagleBoard's v07 model:
#   PCB            the real outline (with holes) as a slab                                   red
#   Parts          every other part's bounding box on a GRID mm height map, merged into boxes dark grey
#                  (always >= the real parts: conservative)
#   Headers        the two 2x18 SMT female sockets as blocks, HDR_H tall, + their end pins    black
#   USB_C          the receptacle's real geometry (shell, tongue, contacts, legs)              silver
#   USB_C_mouth    the receptacle's mouth outline extruded MOUTH_L outward: the minimum hole  orange
#   USB_C_plug     a plug overmold keep-out PLUG_W x PLUG_H (USB-IF max) PLUG_L long          orange
# Stays in the source model's coordinates (same as pocketbeagle2_v03_21_EVT.stp), so it drops into the
# fit-check with the same placement. The USB-C points +X; its axis is printed in pb2_envelope.log.
# Run with the GUI offscreen so the STEP keeps colours (the AppImage launcher forces xcb, so call the binary):
#   H=/home/bp/opt/freecad-1.1.4; env PREFIX=$H/usr PYTHONHOME=$H/usr PATH_TO_FREECAD_LIBDIR=$H/usr/lib \
#     FONTCONFIG_FILE=/etc/fonts/fonts.conf QT_QPA_PLATFORM=offscreen $H/usr/bin/freecad mech/pb2_envelope.py
import os, math, FreeCAD, Part

ROOT = '/home/bp/projects/zinemachine0/.backplane/worktrees/backplane-871755f1'
SRC = ROOT + '/case/pocketbeagle2/models/industrial/pocketbeagle2_v07.step'
OUT = ROOT + '/mech/pb2_envelope'
GRID = 0.25          # mm, XY cell of the parts height map
ZQ = 0.05            # mm, heights rounded outward to this
PCB_TOP, PCB_BOT = 0.0, -1.50368
COPPER_TOL = 0.06    # shells within this of the PCB faces are copper/mask/silk, ignored
HDR_H = 3.55         # mm above PCB top: Industrial's low-profile SMT 2x18 female sockets (EVT board had 8.5)
USB_BOX = ((-284.6, -276.4), (282.3, 291.5), (-4.8, -0.4))   # region holding the USB-C receptacle's solids
MOUTH_L = 10.0       # mm, mouth-profile cutter length out of the receptacle
PLUG_W, PLUG_H, PLUG_R, PLUG_L = 12.35, 6.5, 1.0, 20.0       # plug overmold keep-out (USB-IF max overmold)
COLOURS = {'PCB': (0.72, 0.08, 0.10), 'Parts': (0.22, 0.22, 0.24), 'Headers': (0.05, 0.05, 0.05),
           'USB_C': (0.80, 0.80, 0.83), 'USB_C_mouth': (1.0, 0.55, 0.0), 'USB_C_plug': (1.0, 0.70, 0.30)}
log = open(OUT + '.log', 'w')

src = Part.read(SRC)

def in_usb(b):
    (x0, x1), (y0, y1), (z0, z1) = USB_BOX
    return b.XMin >= x0 and b.XMax <= x1 and b.YMin >= y0 and b.YMax <= y1 and b.ZMin >= z0 and b.ZMax <= z1 \
        and b.ZMin < PCB_BOT - COPPER_TOL

# PCB slab from the top face (outline + holes)
pcb_face = max((f for f in src.Faces if abs(f.BoundBox.ZMin - PCB_TOP) < 1e-3 and abs(f.BoundBox.ZMax - PCB_TOP) < 1e-3),
               key=lambda f: f.Area)
pcb = pcb_face.extrude(FreeCAD.Vector(0, 0, PCB_BOT - PCB_TOP))
bb = pcb.BoundBox
X0, Y0 = bb.XMin - 10, bb.YMin - 10          # grid margin for overhanging parts
NX, NY = int((bb.XLength + 20) / GRID) + 1, int((bb.YLength + 20) / GRID) + 1
top = [[None] * NY for _ in range(NX)]
bot = [[None] * NY for _ in range(NX)]

def cells(b):
    i0, i1 = int(math.floor((b.XMin - X0) / GRID)), int(math.ceil((b.XMax - X0) / GRID))
    j0, j1 = int(math.floor((b.YMin - Y0) / GRID)), int(math.ceil((b.YMax - Y0) / GRID))
    for i in range(max(i0, 0), min(i1, NX)):
        for j in range(max(j0, 0), min(j1, NY)):
            yield i, j

hdr, used = {}, 0
for sh in src.Shells:
    b = sh.BoundBox
    if b.XLength * b.YLength > 1500 or in_usb(b):          # PCB layers / USB-C (kept exact below)
        continue
    if b.XLength > 40 and b.ZMax > 3:                      # the two 2x18 headers
        hdr[(round(b.XMin, 1), round(b.YMin, 1))] = b; continue
    up, down = b.ZMax > PCB_TOP + COPPER_TOL, b.ZMin < PCB_BOT - COPPER_TOL
    if not (up or down):
        continue
    used += 1
    zt, zb = math.ceil(b.ZMax / ZQ) * ZQ, math.floor(b.ZMin / ZQ) * ZQ
    for i, j in cells(b):
        if up and (top[i][j] is None or zt > top[i][j]): top[i][j] = zt
        if down and (bot[i][j] is None or zb < bot[i][j]): bot[i][j] = zb

def rects(grid):
    """greedy merge of equal-height cells into rectangles"""
    done = [[False] * NY for _ in range(NX)]
    out = []
    for i in range(NX):
        for j in range(NY):
            h = grid[i][j]
            if h is None or done[i][j]: continue
            j1 = j
            while j1 + 1 < NY and grid[i][j1 + 1] == h and not done[i][j1 + 1]: j1 += 1
            i1 = i
            while i1 + 1 < NX and all(grid[i1 + 1][k] == h and not done[i1 + 1][k] for k in range(j, j1 + 1)): i1 += 1
            for a in range(i, i1 + 1):
                for k in range(j, j1 + 1): done[a][k] = True
            out.append((X0 + i * GRID, Y0 + j * GRID, (i1 - i + 1) * GRID, (j1 - j + 1) * GRID, h))
    return out

V = FreeCAD.Vector
boxes = [Part.makeBox(w, d, h - PCB_TOP, V(x, y, PCB_TOP)) for x, y, w, d, h in rects(top)] + \
        [Part.makeBox(w, d, PCB_BOT - h, V(x, y, h)) for x, y, w, d, h in rects(bot)]
parts = Part.makeCompound(boxes)

hboxes = []
for b in hdr.values():
    hboxes.append(Part.makeBox(b.XLength, b.YLength, HDR_H, V(b.XMin, b.YMin, PCB_TOP)))
    if b.ZMin < PCB_BOT - COPPER_TOL:                      # through-hole end pins below the PCB
        hboxes.append(Part.makeBox(b.XLength, b.YLength, PCB_BOT - b.ZMin, V(b.XMin, b.YMin, b.ZMin)))
headers = Part.makeCompound(hboxes)

# USB-C: real solids; mouth = the shell's +X end face
usb_solids = [s for s in src.Solids if in_usb(s.BoundBox)]
usb = Part.makeCompound(usb_solids)
ub = usb.BoundBox
mouth_face = max((f for s in usb_solids for f in s.Faces
                  if abs(f.BoundBox.XMin - ub.XMax) < 1e-3 and abs(f.BoundBox.XMax - ub.XMax) < 1e-3),
                 key=lambda f: f.BoundBox.YLength * f.BoundBox.ZLength)
outer = max(mouth_face.Wires, key=lambda w: w.BoundBox.DiagonalLength)
mb = outer.BoundBox
yc, zc, xm = (mb.YMin + mb.YMax) / 2, (mb.ZMin + mb.ZMax) / 2, ub.XMax
mouth = Part.Face(outer).extrude(V(MOUTH_L, 0, 0))
plug_sk = Part.makeBox(PLUG_L, PLUG_W, PLUG_H, V(xm, yc - PLUG_W / 2, zc - PLUG_H / 2))
plug = plug_sk.makeFillet(PLUG_R, [e for e in plug_sk.Edges
                                   if abs(e.Vertexes[0].Point.x - e.Vertexes[1].Point.x) > PLUG_L - 1e-6])

doc = FreeCAD.newDocument('pb2_envelope')
objs = []
for name, shp in (('PCB', pcb), ('Parts', parts), ('Headers', headers), ('USB_C', usb),
                  ('USB_C_mouth', mouth), ('USB_C_plug', plug)):
    o = doc.addObject('Part::Feature', name); o.Shape = shp; objs.append(o)
doc.recompute()
if FreeCAD.GuiUp:
    for o in objs:
        o.ViewObject.ShapeColor = COLOURS[o.Name]
ok = all(o.Shape.isValid() for o in objs)
doc.saveAs(OUT + '.FCStd')
if FreeCAD.GuiUp:
    import ImportGui; ImportGui.export(objs, OUT + '.step')
else:
    import Import; Import.export(objs, OUT + '.step')
log.write(f"gui {FreeCAD.GuiUp}; valid {ok}; shells used {used}; headers {len(hdr)} at {HDR_H} mm; part boxes {len(boxes)}; "
          f"usb solids {len(usb_solids)}; faces {sum(len(o.Shape.Faces) for o in objs)} (source {len(src.Faces)})\n"
          f"USB-C mouth at x={xm:.3f}, axis +X through y={yc:.3f} z={zc:.3f}; mouth {mb.YLength:.2f} x {mb.ZLength:.2f} mm\n"
          f"bbox without keep-outs {Part.makeCompound([pcb, parts, headers, usb]).BoundBox}\n")
log.close()
if FreeCAD.GuiUp:
    os._exit(0)
