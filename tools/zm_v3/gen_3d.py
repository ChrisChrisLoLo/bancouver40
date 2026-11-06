# Simple dimensioned STEP bodies for the zm_v3 custom footprints (from zm_v3_bodies.json written by gen_fp.py).
# Run with FreeCAD's GUI offscreen so the STEP keeps colours:
#   H=/home/bp/opt/freecad-1.1.4; env PREFIX=$H/usr PYTHONHOME=$H/usr PATH_TO_FREECAD_LIBDIR=$H/usr/lib \
#     FONTCONFIG_FILE=/etc/fonts/fonts.conf QT_QPA_PLATFORM=offscreen $H/usr/bin/freecad tools/zm_v3/gen_3d.py
import os, json, FreeCAD, Part, ImportGui
ROOT = '/home/bp/projects/zinemachine0/.backplane/worktrees/backplane-07566bdf/pcb/bancouver40_pb2'
OUT = ROOT + '/3d'
os.makedirs(OUT, exist_ok=True)
log = open(OUT + '/gen_3d.log', 'w')
bodies = json.load(open(ROOT + '/zm_v3_bodies.json'))
COL = {'SW_Kailh_Choc_V1_Plain': (0.15, 0.15, 0.17), 'USB_A_GCT_USB1046': (0.78, 0.78, 0.80),
       'USB_C_Receptacle_6P_ShouHan': (0.78, 0.78, 0.80), 'SW_Slide_DPDT_SK22D02G4_Angled': (0.10, 0.10, 0.10),
       'Jack_3.5mm_PJ-327A_5JJ': (0.08, 0.08, 0.08), 'Jack_3.5mm_PJ-320A-3P_DIP': (0.08, 0.08, 0.08)}
for name, boxes in bodies.items():
    doc = FreeCAD.newDocument(name.replace('.', '_').replace('-', '_'))
    objs = []
    for i, (x0, y0, z0, x1, y1, z1) in enumerate(boxes):
        # KiCad footprint y is down; STEP/VRML model space has y up -> mirror y
        b = Part.makeBox(x1 - x0, y1 - y0, z1 - z0, FreeCAD.Vector(x0, -y1, z0))
        o = doc.addObject('Part::Feature', 'b%d' % i); o.Shape = b
        objs.append(o)
    doc.recompute()
    c = COL.get(name, (0.3, 0.3, 0.3))
    for i, o in enumerate(objs):
        o.ViewObject.ShapeColor = (0.85, 0.1, 0.1) if (name.startswith('SW_Kailh') and i == len(objs) - 1) else c
    ImportGui.export(objs, OUT + '/' + name + '.step')
    log.write('%s %d boxes valid %s\n' % (name, len(objs), all(o.Shape.isValid() for o in objs)))
log.close()
os._exit(0)
