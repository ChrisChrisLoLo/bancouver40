"""Generate the v3 board (bancouver40_pb2.kicad_pcb) from design.py: outline, keep-outs, every footprint with its
nets, fixed parts at the spec positions, ICs where planned, passives auto-placed next to the pin they serve.
Usage: python3 gen_pcb.py <out.kicad_pcb>
"""
import sys, os, math, uuid, re, json
sys.path.insert(0, os.path.dirname(__file__))
from sexp import parse, dump, Sym, find, findall, fmt
import design as D

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PROJ = os.path.join(ROOT, 'pcb', 'bancouver40_pb2')
FPLIB = '/home/bp/opt/backplane-kicad-10.99.0-bp.6/share/kicad/footprints'
NS = uuid.UUID('6b1f2c1e-3c4d-4e5f-8a9b-0c1d2e3f4a5b')
UREF = lambda s: str(uuid.uuid5(NS, s))
U = lambda: str(uuid.uuid4())

# ------------------------------------------------------------------ geometry constants (KiCad mm, y down)
BX0, BY0, BX1, BY1, BR = 74.375, -43.125, 244.375, 82.875, 1.0
BATT = (115.175, -29.425, 189.175, 10.575)         # battery keep-out (no parts on F.Cu); moved 0.6 mm forward for USB-A1
PB2_OUTLINE = (74.9, -43.225, 109.9, 11.775)      # parts under it must be <= 1.5 mm
REAR = -43.1
# battery keep-out with the rear-right corner notched 1.0 x 0.6 mm for USB-A1's back corner (spec overlap)

FIXED = {
    'U2': (78.455, -37.315, 0),
    'J3': (206.5, -8.7, 90),
    'SW44': (121.8, REAR + 2.4, 0),        # body 115.8..127.8 (10.8 wide centred), front face at the rear edge
    'J9': (133.8, REAR + 6.55, 0),
    'J10': (142.8, REAR + 5.8, 0),
    'J6': (154.3, REAR + 4.75, 0),
    'J7': (194.85, REAR + 6.73, 180),     # GCT USB1046: mouth/flange face at the rear edge
    'J8': (209.95, REAR + 6.73, 180),
}
for p in D.PARTS:
    if 'pos' in p:
        FIXED[p['ref']] = (p['pos'][0], p['pos'][1], 0)
# ICs and other planned parts
PLAN = {
    # audio core under the PocketBeagle (all <= 1.5 mm)
    'U17': (92.5, -33.5, 0), 'X1': (86.4, -40.6, 0), 'U16': (99.2, -40.6, 0),
    # left key chain under the PocketBeagle
    'U10': (92.5, -14.5, 0), 'U11': (92.5, -5.0, 0), 'U12': (92.5, 0.9, 0),
    # right key chain between J3 and the mode keys
    'U13': (217.5, -19.0, 0), 'U14': (217.5, -9.5, 0), 'U15': (217.5, 0.0, 0),
    # hub + port 1 power/ESD (zone right of the battery), port 2 behind J8
    'U4': (195.8, -14.0, 180), 'Y1': (199.6, -6.6, 90),
    'U5': (192.2, -25.0, 0), 'U7': (197.6, -25.0, 0),
    'U6': (210.6, -25.0, 0), 'U8': (215.2, -25.0, 0),
    # backlight boost, by J3's LED pins (south end)
    'U3': (195.4, 0.0, 0), 'L1': (195.4, 5.6, 0), 'D1': (191.0, 1.6, 90),
    # charger in the rear strip right of the charge USB-C
    'U9': (166.0, -38.6, 0), 'L2': (176.6, -36.6, 0), 'J5': (184.7, -38.2, 270),
    'Q1': (162.0, -33.6, 0), 'Q2': (169.4, -32.4, 0),
    # status LEDs right of the mode keys
    'D2': (242.6, -29.0, 90), 'R24': (242.6, -26.4, 90), 'D3': (242.6, -23.0, 90), 'R25': (242.6, -20.4, 90),
    'D4': (242.6, -17.0, 90), 'R33': (242.6, -14.4, 90),
    'TP1': (110.6, -22.2, 0),
}
# fixed routes: the upstream USB pair (P1.09 D- / P1.11 D+ -> hub DMU 15 / DPU 16), 0.3 mm / 0.15 mm gap on F.Cu.
# Fans out east through the gaps of P1's inner row, crosses P2 through its gaps (2.54 mm apart there), runs east
# under the battery at y -27.05 and drops at 45 deg into the hub (turned 180 deg so D- arrives on the north side).
PREROUTES = [
    ('USB_UP_N', 'F.Cu', 0.3, [(78.455, -27.155), (79.725, -28.425), (81.85, -28.425), (83.0, -27.275), (102.2, -27.275),
                               (103.35, -28.425), (106.9, -28.425), (108.05, -27.275), (182.3, -27.275),
                               (191.445, -18.13), (193.2, -18.13)]),
    ('USB_UP_P', 'F.Cu', 0.3, [(78.455, -24.615), (79.725, -25.885), (81.85, -25.885), (82.79, -26.825), (102.26, -26.825),
                               (103.2, -25.885), (106.9, -25.885), (107.84, -26.825), (182.114, -26.825),
                               (191.449, -17.49), (193.2, -17.49)]),
]
# ES8388 (U17 at 92.5, -33.5): ground pins 4, 13, 18, 26 tied straight into the exposed pad, 4 vias in the pad
PREROUTES += [('GND', 'F.Cu', 0.2, [(90.5625, -33.5), (91.5, -33.5)]), ('GND', 'F.Cu', 0.2, [(94.4375, -33.5), (93.5, -33.5)]),
              ('GND', 'F.Cu', 0.2, [(92.1, -35.4375), (92.1, -34.4)]), ('GND', 'F.Cu', 0.2, [(93.3, -31.5625), (93.3, -32.6)])]
PREVIAS = [('GND', 92.0, -33.0, 0.5, 0.3), ('GND', 93.0, -33.0, 0.5, 0.3), ('GND', 92.0, -34.0, 0.5, 0.3),
           ('GND', 93.0, -34.0, 0.5, 0.3)]

def seg_box_dist(p, q, bb):
    """distance from segment pq to axis-aligned box bb (0 if they touch)"""
    import itertools
    x0, y0, x1, y1 = bb
    def pt_seg(px, py, a, b):
        ax, ay = a; bx, by = b
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy or 1)))
        return math.hypot(ax + t * dx - px, ay + t * dy - py)
    # sample the segment densely (boxes are small, segments straight)
    n = max(2, int(math.hypot(q[0] - p[0], q[1] - p[1]) / 0.2))
    best = 1e9
    for i in range(n + 1):
        x = p[0] + (q[0] - p[0]) * i / n; y = p[1] + (q[1] - p[1]) * i / n
        dx = max(x0 - x, 0, x - x1); dy = max(y0 - y, 0, y - y1)
        best = min(best, math.hypot(dx, dy))
    return best
def clear_of_routes(bb, m=0.45):
    for net, lay, w, pts in PREROUTES:
        for p, q in zip(pts, pts[1:]):
            # quick reject
            if max(p[0], q[0]) + 2 < bb[0] or min(p[0], q[0]) - 2 > bb[2] or max(p[1], q[1]) + 2 < bb[1] or min(p[1], q[1]) - 2 > bb[3]:
                continue
            if seg_box_dist(p, q, bb) < w / 2 + m:
                return False
    return True

# passives: anchor part (placed near that part's pad on the shared net)
ANCHOR = {
    'C41': 'U17', 'C42': 'U17', 'C43': 'U17', 'C44': 'U17', 'C45': 'U17', 'C46': 'U17', 'C47': 'U17', 'C48': 'U17',
    'C49': 'U17', 'C50': 'U17', 'C51': 'U17', 'C52': 'U17', 'R41': 'U17', 'R42': 'U17', 'R43': 'U17', 'R40': 'U17',
    'R45': 'U17', 'R46': 'U17', 'R51': 'U17', 'C66': 'U17', 'R52': 'U17', 'C67': 'U17', 'C40': 'X1', 'R44': 'U17',
    'C53': 'U16', 'C54': 'U16', 'C55': 'U16',
    'C56': 'J9', 'C57': 'J9', 'R47': 'J9', 'R48': 'J9', 'R53': 'J9', 'C58': 'J10', 'C59': 'J10', 'R49': 'J10', 'R50': 'J10',
    'R60': 'U2', 'R61': 'U2', 'R31': 'U2', 'R32': 'U2', 'C31': 'U2',
    'R10': 'U4', 'R11': 'U4', 'C10': 'U4', 'R12': 'U4', 'R13': 'U4', 'C11': 'U4', 'C12': 'U4', 'C13': 'U4', 'C14': 'U4',
    'C15': 'U5', 'C16': 'U5', 'C17': 'U6', 'C18': 'U6',
    'C1': 'U3', 'C2': 'D1', 'C3': 'U3', 'R1': 'U3', 'R2': 'U3',
    'R20': 'J6', 'R21': 'J6', 'C20': 'U9', 'R22': 'U9', 'C21': 'U9', 'C22': 'U9', 'R23': 'U9', 'C23': 'U9',
    'C24': 'U9', 'C25': 'U9', 'C26': 'U9', 'R26': 'Q1', 'C27': 'Q1', 'R27': 'Q1', 'C28': 'Q1', 'C29': 'Q1',
    'C30': 'Q2', 'R28': 'Q2', 'R29': 'Q2', 'R30': 'Q2',
}
for i, u in enumerate(D.CHAIN):
    ANCHOR['C%d' % (60 + i)] = u
for k in range(12):
    ANCHOR['RN%d' % (k + 1)] = D.CHAIN[k // 2]
# order: tightest first
PRIORITY = ['C24', 'C20', 'C22', 'C41', 'C42', 'C44', 'C46', 'C48', 'C50', 'C52', 'C40', 'C53', 'C54', 'C55', 'C12', 'C14', 'C10',
            'R10', 'C1', 'C3', 'R1', 'C2', 'C20', 'C22', 'C24', 'C25', 'C16', 'C18', 'C60', 'C61', 'C62', 'C63', 'C64', 'C65']
# part heights (mm above the board top, datasheet max or conservative) for the PocketBeagle underside map
HEIGHTS = [('R_0402', 0.40), ('C_0402', 0.60), ('R_0603', 0.55), ('C_0603', 0.95), ('C_0805', 1.35), ('C_1206', 1.8),
           ('LED_0603', 0.80), ('TSSOP', 1.20), ('QFN', 0.90), ('SOT-23-5', 1.45), ('SOT-23-6', 1.45), ('SOT-23', 1.12),
           ('R_Array', 0.60), ('Crystal_SMD_3225', 0.85), ('Oscillator_SMD', 1.00), ('TestPoint', 0.10)]
def height(fp):
    for k, h in HEIGHTS:
        if k in fp:
            return h
    return 99.0
PB2_MAP = [tuple(map(float, l.split(','))) for l in open(os.path.join(os.path.dirname(__file__), 'pb2_underside_keepout.csv'))
           if l[:1].isdigit()]
def under_pb2_ok(bb, h, margin=0.3):
    for x0, y0, x1, y1, hmax in PB2_MAP:
        if hmax > 0 and overlap(bb, (x0, y0, x1, y1)) and h > hmax - margin:
            return False
    return True
LOW_OK = ('R_0402', 'C_0402', 'R_0603', 'C_0603', 'C_0805', 'TSSOP', 'QFN', 'SOT-23', 'R_Array', 'Crystal_SMD_3225',
          'Oscillator_SMD', 'LED_0603', 'TestPoint')

# ------------------------------------------------------------------ footprint loading
FPCACHE = {}
def load_fp(name):
    if name in FPCACHE:
        return FPCACHE[name]
    lib, fpn = name.split(':')
    path = os.path.join(PROJ, 'zm_v3.pretty', fpn + '.kicad_mod') if lib == 'zm_v3' else \
        os.path.join(FPLIB, lib + '.pretty', fpn + '.kicad_mod')
    t = parse(open(path).read())
    FPCACHE[name] = t
    return t

def fp_geom(name):
    """pads [(num, x, y, w, h)], courtyard bbox (x0,y0,x1,y1) in footprint coords"""
    t = load_fp(name)
    pads = []
    for p in findall(t, 'pad'):
        at = find(p, 'at'); sz = find(p, 'size')
        a = float(at[3]) if len(at) > 3 else 0
        w, h = float(sz[1]), float(sz[2])
        if round(a) % 180 == 90:
            w, h = h, w
        pads.append((str(p[1]), float(at[1]), float(at[2]), w, h))
    xs, ys = [], []
    for g in t:
        if isinstance(g, list) and g and g[0] in ('fp_line', 'fp_rect', 'fp_arc', 'fp_circle', 'fp_poly'):
            L = find(g, 'layer')
            if L and L[1] == 'F.CrtYd':
                for k in ('start', 'end', 'mid', 'center'):
                    e = find(g, k)
                    if e:
                        xs.append(float(e[1])); ys.append(float(e[2]))
                pts = find(g, 'pts')
                if pts:
                    for xy in findall(pts, 'xy'):
                        xs.append(float(xy[1])); ys.append(float(xy[2]))
                if g[0] == 'fp_circle':
                    c, e = find(g, 'center'), find(g, 'end')
                    r = math.hypot(float(e[1]) - float(c[1]), float(e[2]) - float(c[2]))
                    xs += [float(c[1]) - r, float(c[1]) + r]; ys += [float(c[2]) - r, float(c[2]) + r]
    if not xs:
        for _, x, y, w, h in pads:
            xs += [x - w / 2, x + w / 2]; ys += [y - h / 2, y + h / 2]
    return pads, (min(xs), min(ys), max(xs), max(ys))

def rot(x, y, a):
    """footprint local -> board offset, KiCad: a CCW on screen (y down)"""
    r = math.radians(a)
    return (x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r))

def crt_boxes(name):
    t = load_fp(name)
    rects = []
    for g in findall(t, 'fp_rect'):
        L = find(g, 'layer')
        if L and L[1] == 'F.CrtYd':
            s_, e_ = find(g, 'start'), find(g, 'end')
            rects.append((min(float(s_[1]), float(e_[1])), min(float(s_[2]), float(e_[2])),
                          max(float(s_[1]), float(e_[1])), max(float(s_[2]), float(e_[2]))))
    others = any(isinstance(g, list) and g and g[0] in ('fp_line', 'fp_arc', 'fp_circle', 'fp_poly') and find(g, 'layer')
                 and find(g, 'layer')[1] == 'F.CrtYd' for g in t)
    if rects and not others:
        return rects
    return [fp_geom(name)[1]]

def _xf(box, x, y, a):
    x0, y0, x1, y1 = box
    pts = [rot(px, py, a) for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    return (x + min(p[0] for p in pts), y + min(p[1] for p in pts), x + max(p[0] for p in pts), y + max(p[1] for p in pts))

def placed_bbox(name, x, y, a):
    return _xf(fp_geom(name)[1], x, y, a)

def placed_boxes(name, x, y, a):
    return [_xf(b, x, y, a) for b in crt_boxes(name)]

def pad_pos(name, x, y, a, num):
    for n, px, py, w, h in fp_geom(name)[0]:
        if n == num:
            dx, dy = rot(px, py, a)
            return (x + dx, y + dy)
    return None

def overlap(a, b, m=0.0):
    return not (a[2] + m <= b[0] or b[2] + m <= a[0] or a[3] + m <= b[1] or b[3] + m <= a[1])

# ------------------------------------------------------------------ placement
def place_all():
    parts = {p['ref']: p for p in D.PARTS}
    pos = {}
    boxes = {}
    for ref, v in list(FIXED.items()) + list(PLAN.items()):
        pos[ref] = v
        boxes[ref] = placed_boxes(parts[ref]['fp'], *v)
    todo = [r for r in parts if r not in pos]
    todo.sort(key=lambda r: (PRIORITY.index(r) if r in PRIORITY else 99, r))
    for ref in todo:
        p = parts[ref]
        anc = ANCHOR.get(ref)
        if not anc:
            raise SystemExit('no anchor for %s' % ref)
        ap = parts[anc]
        # target: the anchor pad sharing a non-GND net with this part (prefer signal nets)
        mynets = [(n, pn) for pn, n in p['pins'].items() if n]
        best_t = None
        for n, mypin in sorted(mynets, key=lambda t: (t[0] in ('GND',), t[0].startswith('+'))):
            for apin, an in ap['pins'].items():
                if an == n:
                    q = pad_pos(ap['fp'], *pos[anc], apin)
                    if q:
                        best_t = (q, mypin, n); break
            if best_t:
                break
        if not best_t:
            best_t = ((pos[anc][0], pos[anc][1]), list(p['pins'])[0], None)
        (tx, ty), mypin, net = best_t
        low = any(k in p['fp'] for k in LOW_OK)
        hgt = height(p['fp'])
        best = None
        R = 0.0
        while R < 25 and best is None:
            cands = []
            steps = max(1, int(2 * math.pi * R / 0.25))
            for s in range(steps):
                ang = 2 * math.pi * s / steps
                cx, cy = round((tx + R * math.cos(ang)) / 0.05) * 0.05, round((ty + R * math.sin(ang)) / 0.05) * 0.05
                for a in (0, 90, 180, 270):
                    # put my pad (not the part centre) at the candidate point
                    q = pad_pos(p['fp'], 0, 0, a, mypin) or (0, 0)
                    x, y = cx - q[0], cy - q[1]
                    bb = placed_bbox(p['fp'], x, y, a)
                    if not ok(bb, low, boxes, 0.5 if p['block'] in ('audio', 'keys_left', 'pb2') else 0.2) \
                            or not under_pb2_ok(bb, hgt) or not clear_of_routes(bb):
                        continue
                    d = math.hypot(x + q[0] - tx, y + q[1] - ty)
                    cands.append((d, x, y, a, bb))
            if cands:
                best = min(cands)
            R += 0.25
        if not best:
            raise SystemExit('could not place %s' % ref)
        _, x, y, a, bb = best
        pos[ref] = (round(x, 3), round(y, 3), a)
        boxes[ref] = [bb]
    return pos, boxes

# routing corridors beside the PocketBeagle header rows (signals leaving the inner rows run along them)
CORRIDORS = [(82.3, -42.6, 84.5, 9.0), (100.3, -42.6, 102.5, 9.0)]

def ok(bb, low, boxes, gap=0.2):
    for c in CORRIDORS:
        if overlap(bb, c):
            return False
    m = 0.5
    if bb[0] < BX0 + m or bb[1] < BY0 + m or bb[2] > BX1 - m or bb[3] > BY1 - m:
        return False
    if overlap(bb, BATT):
        return False
    if bb[3] > 15.0:          # keyboard area: switches only
        return False
    if not low and overlap(bb, PB2_OUTLINE):
        return False
    for bl in boxes.values():
        for b in bl:
            if overlap(bb, b, gap):
                return False
    return True

# ------------------------------------------------------------------ board writing
NAMES = {}
UNCONN = {}
PADSEQ = {}
PADIDS = []
def board_fp(p, x, y, a, netnum):
    t = parse(dump(load_fp(p['fp'])))
    t[1] = p['fp']
    out = [Sym('footprint'), p['fp'], [Sym('layer'), 'F.Cu'], [Sym('uuid'), UREF('fp:' + p['ref'])],
           [Sym('at'), x, y] + ([a] if a else [])]
    sheet = {'pb2': 'pb2_display', 'display': 'pb2_display', 'mech': 'pb2_display', 'keys_left': 'keys',
             'keys_right': 'keys', 'keys': 'keys', 'hub': 'usb_power', 'power': 'usb_power', 'audio': 'audio'}[p['block']]
    titles = {'pb2_display': 'PocketBeagle 2 + display', 'keys': 'Keys and scan chain', 'usb_power': 'USB hub and power',
              'audio': 'Audio'}
    for e in t[2:]:
        if not isinstance(e, list) or not e:
            continue
        k = e[0]
        if k in ('version', 'generator', 'generator_version', 'layer', 'uuid', 'tedit'):
            continue
        if k == 'property':
            if e[1] == 'Reference':
                e[2] = p['ref']
                if p['kind'] in ('R', 'C', 'L', 'RN4', 'Crystal4', 'D_Schottky', 'PMOS', 'NMOS', 'Osc', 'LDO_NR',
                                 'TPS2051B', 'USBLC6-2SC6', 'TestPoint', 'MountingHole', 'LED') or p['block'] == 'audio':
                    lay = find(e, 'layer')
                    if lay is not None:
                        lay[1] = 'F.Fab'
            elif e[1] == 'Value':
                e[2] = p['value']
            at = find(e, 'at')
            if at is not None:
                base = float(at[3]) if len(at) > 3 else 0
                at[3:] = [(base + a) % 360] if (base + a) % 360 else []
        if k == 'fp_text':
            at = find(e, 'at')
            base = float(at[3]) if len(at) > 3 else 0
            at[3:] = [(base + a) % 360] if (base + a) % 360 else []
        if k == 'pad':
            at = find(e, 'at')
            base = float(at[3]) if len(at) > 3 else 0
            at[3:] = [(base + a) % 360] if (base + a) % 360 else []
            n = p['pins'].get(str(e[1]))
            for i in range(len(e) - 1, -1, -1):
                if isinstance(e[i], list) and e[i] and e[i][0] == 'net':
                    del e[i]
            if n:
                e.append([Sym('net'), netnum[NAMES[n]], NAMES[n]])
            elif (p['ref'], str(e[1])) in UNCONN:
                un = UNCONN[(p['ref'], str(e[1]))]
                e.append([Sym('net'), netnum[un], un])
            if str(e[1]) and p['kind'] not in ('MountingHole',):
                pin_name = str(e[1])
                e.append([Sym('pinfunction'), pin_name])
            for i in range(len(e) - 1, -1, -1):
                if isinstance(e[i], list) and e[i] and e[i][0] == 'uuid':
                    del e[i]
            PADSEQ[p['ref']] = PADSEQ.get(p['ref'], 0) + 1
            e.append([Sym('uuid'), UREF('pad:%s:%s:%d' % (p['ref'], e[1], PADSEQ[p['ref']]))])
            PADIDS.append((p['ref'], str(e[1]), UREF('pad:%s:%s:%d' % (p['ref'], e[1], PADSEQ[p['ref']])),
                           NAMES.get(n) if n else None))
        out.append(e)
    for k in ('MPN', 'LCSC'):
        out.append([Sym('property'), k, p.get(k.lower()) or '', [Sym('at'), 0, 0, 0], [Sym('layer'), 'F.Fab'],
                    [Sym('hide'), Sym('yes')], [Sym('uuid'), UREF('prop:%s:%s' % (k, p['ref']))],
                    [Sym('effects'), [Sym('font'), [Sym('size'), 1, 1], [Sym('thickness'), 0.15]]]])
    out.insert(5, [Sym('path'), '/%s/%s' % (UREF('sheet:' + sheet), UREF('sym:' + p['ref']))])
    out.insert(6, [Sym('sheetname'), '/%s/' % titles[sheet]])
    out.insert(7, [Sym('sheetfile'), sheet + '.kicad_sch'])
    # drop pinfunction we added (names unknown here) to keep files clean
    for e in out:
        if isinstance(e, list) and e and e[0] == 'pad':
            for i in range(len(e) - 1, -1, -1):
                if isinstance(e[i], list) and e[i] and e[i][0] == 'pinfunction':
                    del e[i]
    over = {'J3': 'J3_F32Q', 'X1': 'OSC_3225'}.get(p['ref'])
    if over:
        out = [e for e in out if not (isinstance(e, list) and e and e[0] == 'model')]
        out.append([Sym('model'), '${KIPRJMOD}/3d/%s.step' % over, [Sym('offset'), [Sym('xyz'), 0, 0, 0]],
                    [Sym('scale'), [Sym('xyz'), 1, 1, 1]], [Sym('rotate'), [Sym('xyz'), 0, 0, 0]]])
    if p.get('dnp_bom'):
        attr = find(out, 'attr')
        if attr is not None:
            if Sym('exclude_from_pos_files') not in attr:
                attr.append(Sym('exclude_from_pos_files'))
        else:
            out.append([Sym('attr'), Sym('through_hole'), Sym('exclude_from_pos_files')])
    return out

def gr(kind, *pts, layer='Edge.Cuts', w=0.1):
    if kind == 'line':
        (x1, y1), (x2, y2) = pts
        return [Sym('gr_line'), [Sym('start'), x1, y1], [Sym('end'), x2, y2],
                [Sym('stroke'), [Sym('width'), w], [Sym('type'), Sym('default')]], [Sym('layer'), layer], [Sym('uuid'), U()]]
    (x1, y1), (xm, ym), (x2, y2) = pts
    return [Sym('gr_arc'), [Sym('start'), x1, y1], [Sym('mid'), xm, ym], [Sym('end'), x2, y2],
            [Sym('stroke'), [Sym('width'), w], [Sym('type'), Sym('default')]], [Sym('layer'), layer], [Sym('uuid'), U()]]

def outline():
    r, c = BR, BR * (1 - math.sqrt(0.5))
    x0, y0, x1, y1 = BX0, BY0, BX1, BY1
    return [gr('line', (x0 + r, y0), (x1 - r, y0)), gr('line', (x1, y0 + r), (x1, y1 - r)),
            gr('line', (x1 - r, y1), (x0 + r, y1)), gr('line', (x0, y1 - r), (x0, y0 + r)),
            gr('arc', (x0, y0 + r), (x0 + c, y0 + c), (x0 + r, y0)), gr('arc', (x1 - r, y0), (x1 - c, y0 + c), (x1, y0 + r)),
            gr('arc', (x1, y1 - r), (x1 - c, y1 - c), (x1 - r, y1)), gr('arc', (x0 + r, y1), (x0 + c, y1 - c), (x0, y1 - r))]

def keepout_zone(name, box, layers=('F.Cu',)):
    x0, y0, x1, y1 = box
    return [Sym('zone'), [Sym('net'), 0], [Sym('net_name'), ''], [Sym('layers')] + list(layers), [Sym('uuid'), U()],
            [Sym('name'), name], [Sym('hatch'), Sym('edge'), 0.5],
            [Sym('connect_pads'), [Sym('clearance'), 0]], [Sym('min_thickness'), 0.25], [Sym('filled_areas_thickness'), Sym('no')],
            [Sym('keepout'), [Sym('tracks'), Sym('allowed')], [Sym('vias'), Sym('allowed')], [Sym('pads'), Sym('allowed')],
             [Sym('copperpour'), Sym('allowed')], [Sym('footprints'), Sym('not_allowed')]],
            [Sym('placement'), [Sym('enabled'), Sym('no')], [Sym('sheetname'), '']],
            [Sym('fill'), [Sym('thermal_gap'), 0.5], [Sym('thermal_bridge_width'), 0.5]],
            [Sym('polygon'), [Sym('pts')] + [[Sym('xy'), px, py] for px, py in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]]]]

def gnd_zone(layer, gnd):
    i = 0.3
    x0, y0, x1, y1 = BX0 + i, BY0 + i, BX1 - i, BY1 - i
    return [Sym('zone'), [Sym('net'), gnd], [Sym('net_name'), 'GND'], [Sym('layer'), layer], [Sym('uuid'), U()],
            [Sym('name'), 'GND ' + layer], [Sym('hatch'), Sym('edge'), 0.5], [Sym('priority'), 0],
            [Sym('connect_pads'), [Sym('clearance'), 0.2]], [Sym('min_thickness'), 0.2],
            [Sym('filled_areas_thickness'), Sym('no')],
            [Sym('fill'), [Sym('thermal_gap'), 0.3], [Sym('thermal_bridge_width'), 0.35]],
            [Sym('polygon'), [Sym('pts'), [Sym('xy'), x0, y0], [Sym('xy'), x1, y0], [Sym('xy'), x1, y1], [Sym('xy'), x0, y1]]]]

def text(s, x, y, layer, size=1.0, a=0):
    return [Sym('gr_text'), s, [Sym('at'), x, y, a], [Sym('layer'), layer], [Sym('uuid'), U()],
            [Sym('effects'), [Sym('font'), [Sym('size'), size, size], [Sym('thickness'), size * 0.15]]]]

def schematic_netnames():
    """design net -> the name KiCad gives it (sheet-local nets carry a /sheet/ prefix)"""
    import subprocess
    netf = os.path.join(PROJ, 'build', 'bancouver40_pb2.net')
    subprocess.run(['/home/bp/opt/backplane-kicad-10.99.0-bp.6/bin/kicad-cli', 'sch', 'export', 'netlist', '--format',
                    'kicadsexpr', '-o', netf, os.path.join(PROJ, 'bancouver40_pb2.kicad_sch')], check=True,
                   capture_output=True)
    n = parse(open(netf).read())
    bynode = {}
    for net in findall(find(n, 'nets'), 'net'):
        for nd in findall(net, 'node'):
            bynode[(find(nd, 'ref')[1], find(nd, 'pin')[1])] = find(net, 'name')[1]
    out = {}
    for (ref, pin), nm in bynode.items():
        if nm.startswith('unconnected-('):
            UNCONN[(ref, pin)] = nm
    for name, nodes in D.nets().items():
        names = {bynode.get(nd) for nd in nodes}
        assert len(names) == 1 and None not in names, (name, names)
        out[name] = names.pop()
    return out

def main(out):
    pos, boxes = place_all()
    NAMES.update(schematic_netnames())
    nets = sorted(set(NAMES.values()) | set(UNCONN.values()))
    netnum = {n: i + 1 for i, n in enumerate(nets)}
    v2 = parse(open(os.path.join(PROJ, 'build', 'backup_v2', 'bancouver40_pb2.kicad_pcb')).read())
    layers, setup = find(v2, 'layers'), find(v2, 'setup')
    # 4 layers: In1 = solid GND plane, In2 = signal + GND fill (fab standard 1.6 mm, 7628 prepreg)
    if not any(isinstance(l, list) and len(l) > 1 and l[1] == 'In1.Cu' for l in layers):
        layers.insert(2, [4, 'In1.Cu', Sym('signal')])
        layers.insert(3, [6, 'In2.Cu', Sym('signal')])
    def lay(name, typ, **kw):
        e = [Sym('layer'), name, [Sym('type'), typ]]
        for k, v in kw.items():
            e.append([Sym(k), v])
        return e
    st = [Sym('stackup'),
          lay('F.SilkS', 'Top Silk Screen'), lay('F.Paste', 'Top Solder Paste'), lay('F.Mask', 'Top Solder Mask', thickness=0.01),
          lay('F.Cu', 'copper', thickness=0.035), [Sym('layer'), 'dielectric 1', [Sym('type'), 'prepreg'], [Sym('thickness'), 0.2104],
                                                   [Sym('material'), '7628'], [Sym('epsilon_r'), 4.4], [Sym('loss_tangent'), 0.02]],
          lay('In1.Cu', 'copper', thickness=0.0152), [Sym('layer'), 'dielectric 2', [Sym('type'), 'core'], [Sym('thickness'), 1.065],
                                                      [Sym('material'), 'FR4'], [Sym('epsilon_r'), 4.5], [Sym('loss_tangent'), 0.02]],
          lay('In2.Cu', 'copper', thickness=0.0152), [Sym('layer'), 'dielectric 3', [Sym('type'), 'prepreg'], [Sym('thickness'), 0.2104],
                                                      [Sym('material'), '7628'], [Sym('epsilon_r'), 4.4], [Sym('loss_tangent'), 0.02]],
          lay('B.Cu', 'copper', thickness=0.035), lay('B.Mask', 'Bottom Solder Mask', thickness=0.01),
          lay('B.Paste', 'Bottom Solder Paste'), lay('B.SilkS', 'Bottom Silk Screen'),
          [Sym('copper_finish'), 'HAL lead-free'], [Sym('dielectric_constraints'), Sym('no')]]
    for i, e in enumerate(setup):
        if isinstance(e, list) and e and e[0] == 'stackup':
            setup[i] = st
    board = [Sym('kicad_pcb'), [Sym('version'), 20241229], [Sym('generator'), 'pcbnew'], [Sym('generator_version'), '9.0'],
             [Sym('general'), [Sym('thickness'), 1.6], [Sym('legacy_teardrops'), Sym('no')]], [Sym('paper'), 'A3'],
             [Sym('title_block'), [Sym('title'), 'Zine Machine main board v3'], [Sym('date'), '2026-11-06'], [Sym('rev'), '3']],
             layers, setup, [Sym('net'), 0, '']]
    board += [[Sym('net'), netnum[n], n] for n in nets]
    parts = {p['ref']: p for p in D.PARTS}
    for ref in sorted(parts, key=lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r) or 0))):
        p = parts[ref]
        x, y, a = pos[ref]
        board.append(board_fp(p, x, y, a, netnum))
    for net, lay, w, pts in PREROUTES:
        nm = NAMES[net]
        for i, (p, q) in enumerate(zip(pts, pts[1:])):
            board.append([Sym('segment'), [Sym('start'), p[0], p[1]], [Sym('end'), q[0], q[1]], [Sym('width'), w],
                          [Sym('layer'), lay], [Sym('net'), netnum[nm]], [Sym('uuid'), UREF('pre:%s:%d' % (net, i))]])
    for i, (net, x, y, d, dr) in enumerate(PREVIAS):
        board.append([Sym('via'), [Sym('at'), x, y], [Sym('size'), d], [Sym('drill'), dr], [Sym('layers'), 'F.Cu', 'B.Cu'],
                      [Sym('net'), netnum[NAMES[net]]], [Sym('uuid'), UREF('previa:%d' % i)]])
    board += outline()
    board.append(keepout_zone('battery keep-out (9x40x70 LiPo + PCM on foam)', BATT))
    for lay_ in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'):
        board.append(gnd_zone(lay_, netnum[NAMES['GND']]))
    # documentation: battery and PocketBeagle outlines on User.1
    bx0, by0, bx1, by1 = BATT
    for (xa, ya), (xb, yb) in (((bx0, by0), (bx1, by0)), ((bx1, by0), (bx1, by1)), ((bx1, by1), (bx0, by1)), ((bx0, by1), (bx0, by0))):
        board.append(gr('line', (xa, ya), (xb, yb), layer='User.1', w=0.15))
    board.append(text('BATTERY 1S LiPo (under the display)', (bx0 + bx1) / 2, (by0 + by1) / 2, 'User.1', 2.0))
    board.append(text('ON', 115.6, -35.6, 'F.SilkS', 1.0))
    board.append(text('Zine Machine v3', 160.0, 13.0, 'F.SilkS', 1.2))
    open(out, 'w').write(dump(board) + '\n')
    json.dump({k: list(v) for k, v in pos.items()}, open(os.path.join(PROJ, 'build', 'placement.json'), 'w'), indent=0)
    json.dump(PADIDS, open(os.path.join(PROJ, 'build', 'pads.json'), 'w'))
    print('placed', len(pos), 'parts')

if __name__ == '__main__':
    main(sys.argv[1])
