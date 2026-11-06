"""Add GND vias: one beside every SMD GND pad (short stub track) and a stitching grid, each only where it keeps
clearance to every other-net copper item on both layers. Needs shapely (run with /tmp/zmvenv/bin/python).
python gnd_vias.py <in.kicad_pcb> <out.kicad_pcb>
"""
import sys, os, math, uuid
sys.path.insert(0, os.path.dirname(__file__))
from sexp import parse, dump, Sym, find, findall
from shapely.geometry import Point, LineString, box, Polygon
from shapely.ops import unary_union
from shapely import affinity
from shapely.strtree import STRtree

VIA_D, VIA_DRILL, CLR, HOLE_CLR, STUB_W = 0.6, 0.3, 0.17, 0.25, 0.3
BX0, BY0, BX1, BY1 = 74.375, -43.125, 244.375, 82.875
EDGE = 0.6

def rot(x, y, a):
    r = math.radians(a)
    return (x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r))

def main(src, dst):
    b = parse(open(src).read())
    netname = {int(n[1]): n[2] for n in findall(b, 'net')}
    gnd = [k for k, v in netname.items() if v == 'GND'][0]
    other = {'F.Cu': [], 'B.Cu': []}
    holes = []
    gpads = []
    def netof(e):
        n = find(e, 'net')
        return int(n[1]) if n is not None else 0
    for fp in findall(b, 'footprint'):
        at = find(fp, 'at'); fx, fy = float(at[1]), float(at[2]); fa = float(at[3]) if len(at) > 3 else 0
        for p in findall(fp, 'pad'):
            kind, shape = str(p[2]), str(p[3])
            pat = find(p, 'at'); px, py = float(pat[1]), float(pat[2]); pa = float(pat[3]) if len(pat) > 3 else fa
            sz = find(p, 'size'); w, h = float(sz[1]), float(sz[2])
            dx, dy = rot(px, py, fa); cx, cy = fx + dx, fy + dy
            if shape == 'circle':
                g = Point(cx, cy).buffer(w / 2)
            else:
                g = affinity.rotate(box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), -pa, origin=(cx, cy))
                if shape == 'custom':
                    g = g.buffer(0.5)        # conservative
            lays = [str(l) for l in find(p, 'layers')[1:]]
            onlay = ['F.Cu', 'B.Cu'] if (kind in ('thru_hole', 'np_thru_hole') or '*.Cu' in lays) else \
                [l for l in ('F.Cu', 'B.Cu') if l in lays]
            dr = find(p, 'drill')
            if dr is not None and kind in ('thru_hole', 'np_thru_hole'):
                d = float(dr[1]) if str(dr[1]) != 'oval' else max(float(dr[2]), float(dr[3]) if len(dr) > 3 else 0)
                holes.append(Point(cx, cy).buffer(d / 2 + 0.3))
            n = netof(p)
            if n == gnd and kind == 'smd':
                gpads.append((cx, cy, g, onlay[0]))
            if n != gnd or kind == 'np_thru_hole':
                for L in onlay:
                    other[L].append(g)
    for s in findall(b, 'segment'):
        st, en = find(s, 'start'), find(s, 'end')
        g = LineString([(float(st[1]), float(st[2])), (float(en[1]), float(en[2]))]).buffer(float(find(s, 'width')[1]) / 2)
        if netof(s) != gnd:
            other[str(find(s, 'layer')[1])].append(g)
    vias = []
    for v in findall(b, 'via'):
        at = find(v, 'at'); g = Point(float(at[1]), float(at[2])).buffer(float(find(v, 'size')[1]) / 2)
        if netof(v) != gnd:
            other['F.Cu'].append(g); other['B.Cu'].append(g)
        vias.append(g)
    trees = {L: STRtree(other[L]) for L in other}
    htree = STRtree(holes) if holes else None
    inner = box(BX0 + EDGE, BY0 + EDGE, BX1 - EDGE, BY1 - EDGE)
    placed = []
    def free(geom, layers, clr=CLR):
        gb = geom.buffer(clr)
        for L in layers:
            for i in trees[L].query(gb):
                if other[L][i].intersects(gb):
                    return False
        return True
    def via_ok(x, y):
        c = Point(x, y).buffer(VIA_D / 2)
        if not inner.contains(c):
            return False
        if not free(c, ('F.Cu', 'B.Cu')):
            return False
        if htree is not None:
            for i in htree.query(c):
                if holes[i].intersects(c):
                    return False
        for g in placed + vias:
            if g.distance(c) < 0.25:
                return False
        return True
    new = []
    for cx, cy, g, L in gpads:
        best = None
        for r in (0.9, 1.1, 1.3, 1.6, 2.0):
            for k in range(16):
                a = 2 * math.pi * k / 16
                x, y = cx + r * math.cos(a), cy + r * math.sin(a)
                if not via_ok(x, y):
                    continue
                stub = LineString([(cx, cy), (x, y)]).buffer(STUB_W / 2)
                if not free(stub, (L,)):
                    continue
                best = (x, y); break
            if best:
                break
        if not best:
            continue
        x, y = best
        placed.append(Point(x, y).buffer(VIA_D / 2))
        new.append([Sym('segment'), [Sym('start'), round(cx, 4), round(cy, 4)], [Sym('end'), round(x, 4), round(y, 4)],
                    [Sym('width'), STUB_W], [Sym('layer'), L], [Sym('net'), gnd], [Sym('uuid'), str(uuid.uuid4())]])
        new.append([Sym('via'), [Sym('at'), round(x, 4), round(y, 4)], [Sym('size'), VIA_D], [Sym('drill'), VIA_DRILL],
                    [Sym('layers'), 'F.Cu', 'B.Cu'], [Sym('net'), gnd], [Sym('uuid'), str(uuid.uuid4())]])
    npad = len(new) // 2
    # stitching grid (wider clearance so it never crowds a track)
    ngrid = 0
    y = BY0 + 2.0
    while y < BY1 - 1.5:
        x = BX0 + 2.0
        while x < BX1 - 1.5:
            c = Point(x, y).buffer(VIA_D / 2)
            if via_ok(x, y) and free(c, ('F.Cu', 'B.Cu'), 0.35):
                placed.append(c)
                new.append([Sym('via'), [Sym('at'), round(x, 3), round(y, 3)], [Sym('size'), VIA_D], [Sym('drill'), VIA_DRILL],
                            [Sym('layers'), 'F.Cu', 'B.Cu'], [Sym('net'), gnd], [Sym('uuid'), str(uuid.uuid4())]])
                ngrid += 1
            x += 5.0
        y += 5.0
    # zones: solid for SMD, thermal for THT
    for z in findall(b, 'zone'):
        cp = find(z, 'connect_pads')
        if cp is not None and find(z, 'net') is not None and int(find(z, 'net')[1]) == gnd:
            z[z.index(cp)] = [Sym('connect_pads'), Sym('thru_hole_only'), [Sym('clearance'), 0.2]]
    b += new
    open(dst, 'w').write(dump(b) + '\n')
    print('GND pads %d, pad vias %d, stitching vias %d' % (len(gpads), npad, ngrid))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
