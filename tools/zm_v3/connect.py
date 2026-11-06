"""Finish open connections KiCad's DRC reports: A* on a 0.1 mm grid over F.Cu / In2.Cu / B.Cu between the two
reported items of each pair, around all other-net copper (clearance + half width), vias allowed. Appends the tracks
and vias to the board. Board in the generator's format (footprint (at ...)). Needs shapely + numpy.
python connect.py <in.kicad_pcb> <drc.rpt> <out.kicad_pcb>
"""
import sys, os, re, math, heapq, uuid
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import shapely
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from sexp import parse, dump, Sym, find, findall

CLR, VIA_D, VIA_DR, STEP = 0.135, 0.6, 0.3, 0.1
LAYERS = ('F.Cu', 'In2.Cu', 'B.Cu')
WIDTH = {'VBAT': 0.4, '+3V3': 0.3}
BX0, BY0, BX1, BY1 = 74.375, -43.125, 244.375, 82.875

def rot(x, y, a):
    r = math.radians(a); return (x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r))

SEGS = {}
RIPPED = set()
RIP = os.environ.get('RIP') == '1'

def load(b):
    netname = {int(n[1]): str(n[2]) for n in findall(b, 'net') if len(n) > 2}
    def nn(e):
        n = find(e, 'net')
        if n is None: return ''
        return str(n[2]) if len(n) > 2 else netname.get(int(n[1]), '')
    items = []   # (net, layer set, geometry)
    for fp in findall(b, 'footprint'):
        at = find(fp, 'at'); fx, fy = float(at[1]), float(at[2]); fa = float(at[3]) if len(at) > 3 else 0
        for p in findall(fp, 'pad'):
            kind, shape = str(p[2]), str(p[3])
            pat = find(p, 'at'); pa = float(pat[3]) if len(pat) > 3 else fa
            dx, dy = rot(float(pat[1]), float(pat[2]), fa); cx, cy = fx + dx, fy + dy
            sz = find(p, 'size'); w, h = float(sz[1]), float(sz[2])
            g = Point(cx, cy).buffer(w / 2) if shape == 'circle' else \
                shapely.affinity.rotate(box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), -pa, origin=(cx, cy))
            if shape == 'custom':
                g = g.buffer(0.6)
            lays = [str(l) for l in find(p, 'layers')[1:]]
            on = set(LAYERS) if kind in ('thru_hole', 'np_thru_hole') or '*.Cu' in lays else {l for l in LAYERS if l in lays}
            if kind in ('thru_hole', 'np_thru_hole'):
                dr = find(p, 'drill')
                d = float(dr[1]) if str(dr[1]) != 'oval' else float(dr[2])
                g = g.union(Point(cx, cy).buffer(d / 2 + 0.07))      # hole clearance
            items.append((nn(p), on, g))
    for s in findall(b, 'segment'):
        st, en = find(s, 'start'), find(s, 'end')
        items.append((nn(s), {str(find(s, 'layer')[1])},
                      LineString([(float(st[1]), float(st[2])), (float(en[1]), float(en[2]))]).buffer(float(find(s, 'width')[1]) / 2)))
        if find(s, 'locked') is None:
            SEGS[id(items[-1][2])] = s
    for v in findall(b, 'via'):
        at = find(v, 'at')
        items.append((nn(v), set(LAYERS), Point(float(at[1]), float(at[2])).buffer(float(find(v, 'size')[1]) / 2)))
    return items

def pairs_from_report(rpt):
    txt = open(rpt).read()
    out = []
    for blk in re.findall(r'\[unconnected_items\][^\n]*\n(?:[^\n]*\n){3}', txt):
        pts = re.findall(r'@\(([-0-9.]+) mm, ([-0-9.]+) mm\): ([^\n]*)', blk)
        if len(pts) != 2:
            continue
        net = re.search(r'\[([^\]]+)\]', pts[0][2]).group(1)
        if 'Zone' in pts[0][2] or 'Zone' in pts[1][2]:
            continue
        out.append((net, [(float(x), float(y), d) for x, y, d in pts]))
    return out

def item_layers(desc):
    m = re.search(r' on (F\.Cu|In2\.Cu|B\.Cu|In1\.Cu)', desc)
    if desc.startswith('PTH pad') or desc.startswith('Via'):
        return set(LAYERS)
    return {m.group(1)} if m else set(LAYERS)

def route(items, net, a, b, w, la=None, lb=None):
    xs_ = [a[0], b[0]]; ys_ = [a[1], b[1]]
    m = 8.0
    x0, x1 = max(min(xs_) - m, BX0 + 0.4), min(max(xs_) + m, BX1 - 0.4)
    y0, y1 = max(min(ys_) - m, BY0 + 0.4), min(max(ys_) + m, BY1 - 0.4)
    nx, ny = int((x1 - x0) / STEP) + 1, int((y1 - y0) / STEP) + 1
    X, Y = np.meshgrid(x0 + np.arange(nx) * STEP, y0 + np.arange(ny) * STEP, indexing='ij')
    win = box(x0 - 1, y0 - 1, x1 + 1, y1 + 1)
    free, own = {}, {}
    allobs = []
    soft = {}
    for L in LAYERS:
        obs = [g for (n, on, g) in items if L in on and n != net and g.intersects(win)]
        allobs += obs
        hard = [g for g in obs if not (RIP and id(g) in SEGS and SEGS[id(g)][0] == 'segment')]
        o = unary_union(obs).buffer(CLR + w / 2) if obs else shapely.geometry.Polygon()
        oh = unary_union(hard).buffer(CLR + w / 2) if hard else shapely.geometry.Polygon()
        free[L] = ~shapely.contains_xy(o, X, Y)
        soft[L] = ~shapely.contains_xy(oh, X, Y) & ~free[L]
        mine = [g for (n, on, g) in items if L in on and n == net and g.intersects(win)]
        own[L] = shapely.contains_xy(unary_union(mine).buffer(0.02), X, Y) if mine else np.zeros_like(X, bool)
    vo = unary_union(allobs).buffer(CLR + VIA_D / 2)
    via_ok = ~shapely.contains_xy(vo, X, Y) & free['F.Cu'] & free['In2.Cu'] & free['B.Cu']
    def cells_near(p, r=0.35):
        d = np.hypot(X - p[0], Y - p[1]) <= r
        return d
    # start: copper of item A's region; goal: item B's region (own-net copper near the reported points)
    sA, sB = cells_near(a), cells_near(b)
    la = la or set(LAYERS); lb = lb or set(LAYERS)
    start = {L: (sA & (own[L] | free[L])) if L in la else np.zeros_like(X, bool) for L in LAYERS}
    goal = {L: (sB & (own[L] | free[L])) if L in lb else np.zeros_like(X, bool) for L in LAYERS}
    dist, prev, pq = {}, {}, []
    for li, L in enumerate(LAYERS):
        for i, j in zip(*np.nonzero(start[L])):
            dist[(li, i, j)] = 0; heapq.heappush(pq, (0, li, i, j))
    tgt = np.array([b[0], b[1]])
    nb = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    found = None
    while pq:
        d, li, i, j = heapq.heappop(pq)
        if dist.get((li, i, j), 1e18) < d - 1e-9:
            continue
        if goal[LAYERS[li]][i, j]:
            found = (li, i, j); break
        g0 = d
        for di, dj, c in nb:
            a2, b2 = i + di, j + dj
            if 0 <= a2 < nx and 0 <= b2 < ny:
                L = LAYERS[li]
                if free[L][a2, b2] or own[L][a2, b2] or soft[L][a2, b2]:
                    nd = g0 + c * (1.0 if L != 'In2.Cu' else 1.05) + (60 if soft[L][a2, b2] and not own[L][a2, b2] else 0)
                    if nd < dist.get((li, a2, b2), 1e18):
                        dist[(li, a2, b2)] = nd; prev[(li, a2, b2)] = (li, i, j)
                        h = math.hypot(X[a2, b2] - tgt[0], Y[a2, b2] - tgt[1]) / STEP
                        heapq.heappush(pq, (nd + 0 * h, li, a2, b2))
        if via_ok[i, j]:
            for lo in range(3):
                if lo != li:
                    nd = g0 + 15
                    if nd < dist.get((lo, i, j), 1e18):
                        dist[(lo, i, j)] = nd; prev[(lo, i, j)] = (li, i, j); heapq.heappush(pq, (nd, lo, i, j))
    if not found:
        return None
    path = [found]
    crossed = set()
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    pts = [(LAYERS[li], float(X[i, j]), float(Y[i, j])) for li, i, j in path]
    if RIP:
        for L in LAYERS:
            pl = [(x, y) for (LL, x, y) in pts if LL == L]
            if len(pl) < 1:
                continue
            g = shapely.geometry.MultiPoint(pl).buffer(CLR + w / 2)
            for (n, on, gg) in items:
                if L in on and n != net and id(gg) in SEGS and gg.intersects(g):
                    crossed.add(id(gg))
        RIPPED.update(crossed)
    out = []
    s0 = pts[0]
    for k in range(1, len(pts)):
        L, x, y = pts[k]; pL, px, py = pts[k - 1]
        if L != pL:
            if (px, py) != (s0[1], s0[2]):
                out.append(('seg', pL, s0[1], s0[2], px, py))
            out.append(('via', x, y)); s0 = pts[k]; continue
        if k + 1 < len(pts) and pts[k + 1][0] == L:
            if abs((pts[k + 1][1] - x) - (x - px)) < 1e-9 and abs((pts[k + 1][2] - y) - (y - py)) < 1e-9:
                continue
        out.append(('seg', L, s0[1], s0[2], x, y)); s0 = pts[k]
    if (s0[1], s0[2]) != (pts[-1][1], pts[-1][2]) and s0[0] == pts[-1][0]:
        out.append(('seg', s0[0], s0[1], s0[2], pts[-1][1], pts[-1][2]))
    # connect the path ends to the reported points so the copper actually touches the items
    out.insert(0, ('seg', pts[0][0], a[0], a[1], pts[0][1], pts[0][2]))
    out.append(('seg', pts[-1][0], pts[-1][1], pts[-1][2], b[0], b[1]))
    return out

def main(src, rpt, dst):
    b = parse(open(src).read())
    netnum = {str(n[2]): int(n[1]) for n in findall(b, 'net') if len(n) > 2}
    items = load(b)
    todo = pairs_from_report(rpt)
    for net, ((ax, ay, ad), (bx, by, bd)) in todo:
        w = WIDTH.get(net, 0.15)
        res = route(items, net, (ax, ay), (bx, by), w, item_layers(ad), item_layers(bd))
        print('%-45s %s' % (net, 'routed, %d items' % len(res) if res else 'NO PATH'))
        if not res:
            continue
        for it in res:
            if it[0] == 'seg':
                if (it[2], it[3]) == (it[4], it[5]):
                    continue
                e = [Sym('segment'), [Sym('locked'), Sym('yes')], [Sym('start'), round(it[2], 4), round(it[3], 4)], [Sym('end'), round(it[4], 4), round(it[5], 4)],
                     [Sym('width'), w], [Sym('layer'), it[1]], [Sym('net'), netnum[net]], [Sym('uuid'), str(uuid.uuid4())]]
                items.append((net, {it[1]}, LineString([(it[2], it[3]), (it[4], it[5])]).buffer(w / 2)))
            else:
                e = [Sym('via'), [Sym('locked'), Sym('yes')], [Sym('at'), round(it[1], 4), round(it[2], 4)], [Sym('size'), VIA_D], [Sym('drill'), VIA_DR],
                     [Sym('layers'), 'F.Cu', 'B.Cu'], [Sym('net'), netnum[net]], [Sym('uuid'), str(uuid.uuid4())]]
                items.append((net, set(LAYERS), Point(it[1], it[2]).buffer(VIA_D / 2)))
            b.append(e)
    if RIPPED:
        rip = [SEGS[k] for k in RIPPED]
        nets = set()
        netname = {int(n[1]): str(n[2]) for n in findall(b, 'net') if len(n) > 2}
        for sg in rip:
            nets.add(netname.get(int(find(sg, 'net')[1]), ''))
        b = [e for e in b if not any(e is r for r in rip)]
        print('ripped %d segments of nets: %s' % (len(rip), ', '.join(sorted(nets))))
        open(dst + '.ripped', 'w').write('\n'.join(sorted(nets)) + '\n')
    open(dst, 'w').write(dump(b) + '\n')

if __name__ == '__main__':
    main(*sys.argv[1:4])
