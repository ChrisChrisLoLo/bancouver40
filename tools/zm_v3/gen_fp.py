"""Custom footprints for the Zine Machine v3 board -> <outdir>/zm_v3.pretty (+ simple STEP bodies via body list).
Pads from the parts' drawings (see comments). Every connector's mouth / actuator faces -y (rear) at rotation 0.
Usage: python3 gen_fp.py <outdir>
"""
import sys, os, uuid, json

def U():
    return str(uuid.uuid4())

def n(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s

def line(x1, y1, x2, y2, layer, w=0.12):
    return '\t(fp_line (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (layer "%s") (uuid "%s"))\n' % (
        n(x1), n(y1), n(x2), n(y2), n(w), layer, U())

def rect(x1, y1, x2, y2, layer, w=0.12):
    return '\t(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))\n' % (
        n(x1), n(y1), n(x2), n(y2), n(w), layer, U())

def text(kind, val, x, y, layer, hide=False):
    return ('\t(property "%s" "%s" (at %s %s 0) (layer "%s")%s (uuid "%s") (effects (font (size 1 1) (thickness 0.15))))\n'
            % (kind, val, n(x), n(y), layer, ' (hide yes)' if hide else '', U()))

def tht(num, x, y, drill, size, shape='circle', slot=None):
    if slot:   # oval slot (w, h) drill
        return ('\t(pad "%s" thru_hole oval (at %s %s) (size %s %s) (drill oval %s %s) (layers "*.Cu" "*.Mask") (uuid "%s"))\n'
                % (num, n(x), n(y), n(size[0]), n(size[1]), n(slot[0]), n(slot[1]), U()))
    return ('\t(pad "%s" thru_hole %s (at %s %s) (size %s %s) (drill %s) (layers "*.Cu" "*.Mask") (uuid "%s"))\n'
            % (num, shape, n(x), n(y), n(size), n(size), n(drill), U()))

def npth(x, y, d):
    return ('\t(pad "" np_thru_hole circle (at %s %s) (size %s %s) (drill %s) (layers "*.Cu" "*.Mask") (uuid "%s"))\n'
            % (n(x), n(y), n(d), n(d), n(d), U()))

def smd(num, x, y, w, h):
    return ('\t(pad "%s" smd roundrect (at %s %s) (size %s %s) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.15) (uuid "%s"))\n'
            % (num, n(x), n(y), n(w), n(h), U()))

BODIES = {}    # footprint -> list of boxes (x0, y0, z0, x1, y1, z1) in footprint coords, z up from board top

def fp(name, descr, attr, body, pads, extra='', model=True, crt=None):
    x0, y0, x1, y1 = body
    s = '(footprint "%s"\n\t(version 20241229)\n\t(generator "zm_v3")\n\t(layer "F.Cu")\n\t(descr "%s")\n' % (name, descr)
    s += text('Reference', 'REF**', 0, y1 + 1.2 if y0 < -4 else y0 - 1.5, 'F.SilkS')
    s += text('Value', name, 0, y1 + 1.5, 'F.Fab')
    s += text('Footprint', '', 0, 0, 'F.Fab', hide=True)
    s += '\t(attr %s)\n' % attr
    s += rect(x0, y0, x1, y1, 'F.Fab', 0.1)
    import re
    cx0, cy0, cx1, cy1 = x0, y0, x1, y1
    for pd in pads:
        m = re.search(r'\(at (\S+) (\S+)\) \(size (\S+) (\S+)\)', pd)
        if m:
            px, py, w, h = map(float, m.groups())
            cx0, cy0 = min(cx0, px - w / 2), min(cy0, py - h / 2)
            cx1, cy1 = max(cx1, px + w / 2), max(cy1, py + h / 2)
    if crt:
        s += '\t(fp_poly (pts %s) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd") (uuid "%s"))\n' % (
            ' '.join('(xy %s %s)' % (n(x), n(y)) for x, y in crt), U())
    else:
        s += rect(cx0 - 0.25, cy0 - 0.25, cx1 + 0.25, cy1 + 0.25, 'F.CrtYd', 0.05)
    s += extra
    s += ''.join(pads)
    if model:
        s += '\t(model "${KIPRJMOD}/3d/%s.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n' % name
    s += ')\n'
    return s

def main(outdir):
    lib = os.path.join(outdir, 'zm_v3.pretty')
    os.makedirs(lib, exist_ok=True)
    out = {}
    # ---- Kailh Choc v1, plain (no hot-swap), pins as on the v2 board (switch turned 180 deg)
    pads = [tht('1', 0, 5.95, 1.2, 2.2), tht('2', -5, 3.75, 1.2, 2.2), npth(0, 0, 3.429), npth(-5.5, 0, 1.7018),
            npth(5.5, 0, 1.7018)]
    silk = rect(-7.35, -7.35, 7.35, 7.35, 'F.SilkS')
    ch = [(-7.5, -5.5), (-5.5, -7.5), (5.5, -7.5), (7.5, -5.5), (7.5, 5.5), (5.5, 7.5), (-5.5, 7.5), (-7.5, 5.5)]
    out['SW_Kailh_Choc_V1_Plain'] = fp('SW_Kailh_Choc_V1_Plain', 'Kailh Choc v1 (PG1350), soldered, 1u 17 mm grid; courtyard corners chamfered (tray screws sit under the top-housing corners)',
                                       'through_hole', (-7.5, -7.5, 7.5, 7.5), pads, silk, crt=ch)
    BODIES['SW_Kailh_Choc_V1_Plain'] = [(-6.9, -6.9, 0, 6.9, 6.9, 2.2), (-7.5, -7.5, 2.2, 7.5, 7.5, 5.0),
                                         (-2.5, -1.5, 5.0, 2.5, 1.5, 5.9)]
    # ---- USB-A receptacle GCT USB1046 (top mount SMT, shell stakes in 0.6x2.3 slots). Pads as KiCad's
    #      Connector_USB:USB_A_Receptacle_GCT_USB1046 (mouth +y, PCB edge line at y 5.45, flange 14.5 wide at the
    #      front); the HX AF90's 2.3 mm leg holes collide side by side at the spec's 15.1 mm pitch.
    pads = [smd('1', -3.5, -7.25, 1.3, 3.0), smd('2', -1.0, -7.25, 1.3, 3.0), smd('3', 1.0, -7.25, 1.3, 3.0),
            smd('4', 3.5, -7.25, 1.3, 3.0),
            '\t(pad "SH" thru_hole oval (at -6.4 -3.55) (size 1.2 2.9) (drill oval 0.6 2.3) (layers "*.Cu" "*.Mask") (uuid "%s"))\n' % U(),
            '\t(pad "SH" thru_hole oval (at 6.4 -3.55) (size 1.2 2.9) (drill oval 0.6 2.3) (layers "*.Cu" "*.Mask") (uuid "%s"))\n' % U()]
    crt = [(-4.15, -9.0), (4.15, -9.0), (4.15, -6.85), (6.6, -6.85), (6.6, 5.43), (7.5, 5.43), (7.5, 7.0), (-7.5, 7.0), (-7.5, 5.43), (-6.6, 5.43), (-6.6, -6.85), (-4.15, -6.85)]
    silk = line(-6.6, -1.8, -6.6, 5.0, 'F.SilkS') + line(6.6, -1.8, 6.6, 5.0, 'F.SilkS')
    out['USB_A_GCT_USB1046'] = fp('USB_A_GCT_USB1046', 'USB-A receptacle GCT USB1046-GF-0190-L-B-A, top mount SMT, shell stakes; mouth +y (place at 180)',
                                  'through_hole', (-6.4, -6.67, 6.4, 6.73), pads, silk, crt=crt)
    BODIES['USB_A_GCT_USB1046'] = [(-6.4, -6.67, 0, 6.4, 5.93, 7.0), (-7.25, 5.93, 0, 7.25, 6.73, 7.0)]
    # ---- USB-C 6P (SHOU HAN TYPE-C 6P, C456012), pads from the fab's footprint, turned so the mouth faces -y
    raw = [('7', 4.32, 2.025), ('7', -4.32, 2.025), ('7', 4.32, -1.775), ('7', -4.32, -1.775)]
    pads = [tht(num, -x, -y, 0, (1.1, 1.9), slot=(0.6, 1.3)) for num, x, y in raw]
    for num, x, w in (('A5', -0.5, 0.7), ('A9', 1.5, 0.7), ('A12', 2.7, 0.8), ('B5', 0.5, 0.7), ('B9', -1.5, 0.7),
                      ('B12', -2.7, 0.8)):
        pads.append(smd(num, -x, 2.025, w, 1.2))
    out['USB_C_Receptacle_6P_ShouHan'] = fp('USB_C_Receptacle_6P_ShouHan', 'USB-C 6-pin power-only receptacle, SHOU HAN TYPE-C 6P; mouth -y',
                                            'through_hole', (-4.47, -4.75, 4.47, 2.6), pads, '')
    BODIES['USB_C_Receptacle_6P_ShouHan'] = [(-4.47, -4.75, 0, 4.47, 2.6, 3.26)]
    # ---- slide switch DPDT SK22D02G4 (HanElectricity): pins 2 mm, rows 2.4 apart, tabs 10.4; knob 3x3 mm, 4 mm out
    pads = [tht('1', -2, 1.2, 0.9, 1.5), tht('2', 0, 1.2, 0.9, 1.5), tht('3', 2, 1.2, 0.9, 1.5),
            tht('4', 2, -1.2, 0.9, 1.5), tht('5', 0, -1.2, 0.9, 1.5), tht('6', -2, -1.2, 0.9, 1.5),
            tht('7', -5.2, 0, 0, (1.5, 2.3), slot=(0.7, 1.5)), tht('8', 5.2, 0, 0, (1.5, 2.3), slot=(0.7, 1.5))]
    silk = line(-3.2, 3.0, 3.2, 3.0, 'F.SilkS') + \
        ('\t(fp_text user "ON" (at -3.6 -3.4 0) (layer "F.SilkS") (uuid "%s") (effects (font (size 0.8 0.8) (thickness 0.15))))\n' % U())
    out['SW_Slide_DPDT_SK22D02G4_Angled'] = fp('SW_Slide_DPDT_SK22D02G4_Angled',
                                               'DPDT slide switch SK22D02G4, right angle, knob 3x3 mm 4 mm out -y; ON = knob toward -x (pins 1-2, 5-6)',
                                               'through_hole', (-5.4, -6.4, 5.4, 3.9), pads, silk)
    BODIES['SW_Slide_DPDT_SK22D02G4_Angled'] = [(-5.4, -2.4, 0, 5.4, 3.9, 5.1), (-1.5, -6.4, 1.5, 1.5, -2.4, 4.5)]
    # ---- 3.5 mm headset jack PJ-327A 5JJ (SHOU HAN), mouth -y; pads from the fab's footprint, pegs from the drawing
    pads = [smd('1', 3.8, -4.85, 3.2, 2.0), smd('2', -3.8, -3.85, 3.2, 2.0), smd('3', 3.8, -1.15, 3.2, 2.0),
            smd('4', -3.8, 3.15, 3.2, 2.0), smd('5', 3.8, 4.85, 3.2, 2.0), npth(0, -3.5, 1.0), npth(0, 3.0, 1.0)]
    out['Jack_3.5mm_PJ-327A_5JJ'] = fp('Jack_3.5mm_PJ-327A_5JJ', 'TRRS jack with switch, PJ-327A 5JJ; mouth -y',
                                       'smd', (-3.0, -8.55, 3.0, 5.65), pads, '')
    BODIES['Jack_3.5mm_PJ-327A_5JJ'] = [(-3.0, -6.55, 0, 3.0, 5.65, 4.6), (-1.8, -8.55, 0.7, 1.8, -6.55, 4.3)]
    # ---- 3.5 mm TRS jack PJ-320A-3P DIP (SHOU HAN, C17701689), THT so its pins stay under the body (the
    #      SMD jacks' side pads would collide with the headset jack 9 mm away). Drawing: front face 2.3 mm before
    #      pin 3 (sleeve), pin 2 ring +2.0, pin 4 tip +7.0, body 11.1 + 3.0 nose, pegs on the axis 1.7 / 6.0 from the face.
    pads = [tht('2', 2.4, -1.5, 0, (1.2, 2.0), slot=(0.6, 1.4)), tht('3', -2.4, -3.5, 0, (1.2, 2.0), slot=(0.6, 1.4)),
            tht('4', -2.4, 3.5, 0, (1.2, 2.0), slot=(0.6, 1.4)), npth(0, -4.1, 1.1), npth(0, 0.2, 1.1)]
    out['Jack_3.5mm_PJ-320A-3P_DIP'] = fp('Jack_3.5mm_PJ-320A-3P_DIP', 'TRS jack PJ-320A-3P DIP (3 sleeve, 2 ring, 4 tip); mouth -y',
                                          'through_hole', (-3.0, -8.8, 3.0, 5.3), pads, '')
    BODIES['Jack_3.5mm_PJ-320A-3P_DIP'] = [(-3.0, -5.8, 0, 3.0, 5.3, 5.0), (-2.5, -8.8, 0.0, 2.5, -5.8, 5.0)]
    # ---- PocketBeagle 2 Industrial, face-down on its own 3.55 mm SMT sockets; carrier side = 2x(2x18) male pins
    #      inserted from below. Pad numbering as Module:BeagleBoard_PocketBeagle (P1.n = n, P2.n = 36 + n), P1.01 at
    #      the origin, P2.01 at +25.4 mm, rows run +y. Courtyard only around the header rows: parts may sit under
    #      the module if <= 1.5 mm tall. Module outline (35 x 55, USB-C end at -y) on F.Fab / User.1.
    pads = []
    for k in range(36):
        x, y = (k % 2) * 2.54, (k // 2) * 2.54
        pads.append(tht(str(k + 1), x, y, 1.0, 1.7, shape='rect' if k == 0 else 'circle'))
        pads.append(tht(str(37 + k), 25.4 + x, y, 1.0, 1.7, shape='rect' if k == 0 else 'circle'))
    extra = rect(-1.4, -1.4, 3.94, 44.58, 'F.CrtYd', 0.05) + rect(24.0, -1.4, 29.34, 44.58, 'F.CrtYd', 0.05)
    extra += rect(-1.27, -1.27, 3.81, 44.45, 'F.SilkS') + rect(24.13, -1.27, 29.21, 44.45, 'F.SilkS')
    extra += rect(-3.555, -5.91, 31.445, 49.09, 'F.Fab', 0.1) + rect(-3.555, -5.91, 31.445, 49.09, 'User.1', 0.1)
    extra += ('\t(fp_text user "PocketBeagle 2 (face-down), USB-C this end; parts under it <= 1.5 mm" (at 13.9 -4.6 0) (layer "F.Fab") (uuid "%s") (effects (font (size 1 1) (thickness 0.15))))\n' % U())
    extra += ('\t(fp_text user "P1" (at 1.27 46.2 0) (layer "F.SilkS") (uuid "%s") (effects (font (size 1 1) (thickness 0.15))))\n' % U())
    extra += ('\t(fp_text user "P2" (at 26.67 46.2 0) (layer "F.SilkS") (uuid "%s") (effects (font (size 1 1) (thickness 0.15))))\n' % U())
    body_fp = fp('PocketBeagle2_FaceDown', 'PocketBeagle 2 Industrial carrier footprint, module face-down, 2x 2x18 2.54 mm',
                 'through_hole', (-1.27, -1.27, 29.21, 44.45), pads, extra, model=False)
    # keep only our header courtyards (drop the auto body courtyard)
    import re as _re
    body_fp = _re.sub(r'\t\(fp_rect \(start -1\.52 -1\.52\) \(end 29\.46 44\.7\)[^\n]*F\.CrtYd[^\n]*\n', '', body_fp)
    out['PocketBeagle2_FaceDown'] = body_fp
    # bodies for library footprints whose 3D model this KiCad install lacks (used via model override in gen_pcb)
    BODIES['J3_F32Q'] = [(-14.15, -3.95, 0, 14.15, 2.75, 2.0)]       # spec body box, 2.0 mm above the board
    BODIES['OSC_3225'] = [(-1.6, -1.25, 0, 1.6, 1.25, 1.0)]
    for k, v in out.items():
        open(os.path.join(lib, k + '.kicad_mod'), 'w').write(v)
    json.dump(BODIES, open(os.path.join(outdir, 'zm_v3_bodies.json'), 'w'), indent=1)
    print('wrote', len(out), 'footprints to', lib)

if __name__ == '__main__':
    main(sys.argv[1])
