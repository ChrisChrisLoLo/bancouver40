"""Connect isolated GND pour fragments to the main ground with short routed tracks (+ vias) on a local grid.
Reads the saved (filled) board, edits the open board over IPC, refills, repeats.
Run with the kistack layout-placement python (kicad-python, shapely, numpy).
"""
import sys, os, math, glob, heapq
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sexp import parse, find, findall
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
import shapely
from kipy import KiCad
from kipy.board_types import Via, Track, BoardLayer
from kipy.geometry import Vector2

BOARD = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'pcb', 'bancouver40_pb2', 'bancouver40_pb2.kicad_pcb'))
W, CLR, VIA_D, VIA_DR = 0.25, 0.16, 0.6, 0.3
STEP = 0.1
BX0, BY0, BX1, BY1 = 74.375, -43.125, 244.375, 82.875

def rot(x, y, a):
    r = math.radians(a); return (x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r))

def netof(e):
    n = find(e, 'net')
    if n is None:
        return None
    return str(n[-1])

def load(path):
    b = parse(open(path).read())
    cu = {'F.Cu': [], 'B.Cu': []}     # other-net copper
    holes = []
    gnd_frags, links = [], []
    for fpt in findall(b, 'footprint'):
        t = find(fpt, 'transform'); tr = find(t, 'translate'); ro = find(t, 'rotate')
        fx, fy, fa = float(tr[1]), float(tr[2]), (float(ro[1]) if ro is not None else 0)
        for p in findall(fpt, 'pad'):
            kind, shape = str(p[2]), str(p[3])
            pat = find(p, 'at'); pa = float(pat[3]) if len(pat) > 3 else fa
            dx, dy = rot(float(pat[1]), float(pat[2]), fa); cx, cy = fx + dx, fy + dy
            sz = find(p, 'size'); w, h = float(sz[1]), float(sz[2])
            if shape == 'circle':
                g = Point(cx, cy).buffer(w / 2)
            else:
                g = shapely.affinity.rotate(box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), -pa, origin=(cx, cy))
                if shape == 'custom':
                    g = g.buffer(0.6)
            lays = [str(l) for l in find(p, 'layers')[1:]]
            onlay = ['F.Cu', 'B.Cu'] if kind in ('thru_hole', 'np_thru_hole') or '*.Cu' in lays else \
                [l for l in ('F.Cu', 'B.Cu') if l in lays]
            dr = find(p, 'drill')
            if kind in ('thru_hole', 'np_thru_hole') and dr is not None:
                holes.append(Point(cx, cy).buffer(max(w, h) / 2 + 0.25))
            n = netof(p)
            if n == 'GND' and kind == 'thru_hole':
                links.append(Point(cx, cy).buffer(min(w, h) / 2 + 0.4))
            if n != 'GND' or kind == 'np_thru_hole':
                for L in onlay:
                    cu[L].append(g)
    for s in findall(b, 'segment'):
        st, en = find(s, 'start'), find(s, 'end'); L = str(find(s, 'layer')[1])
        g = LineString([(float(st[1]), float(st[2])), (float(en[1]), float(en[2]))]).buffer(float(find(s, 'width')[1]) / 2)
        if netof(s) != 'GND':
            cu[L].append(g)
        else:
            links.append(('seg', L, g))
    for v in findall(b, 'via'):
        at = find(v, 'at'); d = float(find(v, 'size')[1])
        g = Point(float(at[1]), float(at[2])).buffer(d / 2)
        holes.append(Point(float(at[1]), float(at[2])).buffer(d / 2 + 0.05))
        if netof(v) != 'GND':
            cu['F.Cu'].append(g); cu['B.Cu'].append(g)
        else:
            links.append(Point(float(at[1]), float(at[2])).buffer(d / 2 + 0.4))
    for z in findall(b, 'zone'):
        if netof(z) != 'GND':
            continue
        for fp in findall(z, 'filled_polygon'):
            L = str(find(fp, 'layer')[1])
            pts = [(float(xy[1]), float(xy[2])) for xy in findall(find(fp, 'pts'), 'xy')]
            if len(pts) >= 3:
                gnd_frags.append((L, Polygon(pts).buffer(0)))
    return cu, holes, gnd_frags, links

def groups(frags, links):
    par = list(range(len(frags)))
    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    for g in links:
        if isinstance(g, tuple):
            _, L, geom = g
            hit = [i for i, (LL, P) in enumerate(frags) if LL == L and P.intersects(geom)]
        else:
            hit = [i for i, (L, P) in enumerate(frags) if P.intersects(g)]
        for i in hit[1:]:
            par[f(i)] = f(hit[0])
    gr = {}
    for i in range(len(frags)):
        gr.setdefault(f(i), []).append(i)
    main = max(gr.values(), key=lambda g: sum(frags[i][1].area for i in g))
    return main, [g for g in gr.values() if g is not main]

def route_one(cu, holes, frags, main, grp, win=15.0):
    P = unary_union([frags[i][1] for i in grp])
    x0, y0, x1, y1 = P.bounds
    x0, y0, x1, y1 = max(x0 - win, BX0 + 0.5), max(y0 - win, BY0 + 0.5), min(x1 + win, BX1 - 0.5), min(y1 + win, BY1 - 0.5)
    nx, ny = int((x1 - x0) / STEP) + 1, int((y1 - y0) / STEP) + 1
    xs = x0 + np.arange(nx) * STEP; ys = y0 + np.arange(ny) * STEP
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    win_box = box(x0 - 1, y0 - 1, x1 + 1, y1 + 1)
    free, start, goal = {}, {}, {}
    for L in ('F.Cu', 'B.Cu'):
        obs = [g for g in cu[L] if g.intersects(win_box)]
        ob = unary_union(obs).buffer(CLR + W / 2) if obs else Polygon()
        free[L] = ~shapely.contains_xy(ob, X, Y) & shapely.contains_xy(box(BX0 + 0.45, BY0 + 0.45, BX1 - 0.45, BY1 - 0.45), X, Y)
        mine = unary_union([frags[i][1] for i in grp if frags[i][0] == L])
        start[L] = shapely.contains_xy(mine.buffer(-0.05), X, Y) if not mine.is_empty else np.zeros_like(X, bool)
        mainL = unary_union([frags[i][1] for i in main if frags[i][0] == L and frags[i][1].intersects(win_box)])
        goal[L] = shapely.contains_xy(mainL.buffer(-0.15), X, Y) if not mainL.is_empty else np.zeros_like(X, bool)
    vobs = unary_union([g for L in cu for g in cu[L] if g.intersects(win_box)] + [h for h in holes if h.intersects(win_box)])
    via_ok = ~shapely.contains_xy(vobs.buffer(CLR + VIA_D / 2), X, Y) & free['F.Cu'] & free['B.Cu']
    Ls = ('F.Cu', 'B.Cu')
    dist = {}
    pq = []
    for li, L in enumerate(Ls):
        for i, j in zip(*np.nonzero(start[L])):
            dist[(li, i, j)] = 0
            heapq.heappush(pq, (0, li, i, j))
    prev = {}
    nb = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    found = None
    while pq:
        d, li, i, j = heapq.heappop(pq)
        if dist.get((li, i, j), 1e9) < d:
            continue
        if goal[Ls[li]][i, j] and d > 0:
            found = (li, i, j); break
        if d > 600:
            break
        for di, dj, c in nb:
            a, bb = i + di, j + dj
            if 0 <= a < nx and 0 <= bb < ny and (free[Ls[li]][a, bb] or start[Ls[li]][a, bb]):
                nd = d + c
                if nd < dist.get((li, a, bb), 1e9):
                    dist[(li, a, bb)] = nd; prev[(li, a, bb)] = (li, i, j); heapq.heappush(pq, (nd, li, a, bb))
        if via_ok[i, j]:
            o = 1 - li; nd = d + 25
            if nd < dist.get((o, i, j), 1e9):
                dist[(o, i, j)] = nd; prev[(o, i, j)] = (li, i, j); heapq.heappush(pq, (nd, o, i, j))
    if not found:
        return None
    path = [found]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    # to tracks/vias: compress straight runs
    items = []
    pts = [(Ls[li], xs[i], ys[j]) for li, i, j in path]
    seg_start = pts[0]
    for k in range(1, len(pts)):
        L, x, y = pts[k]
        pL, px, py = pts[k - 1]
        if L != pL:
            if (px, py) != (seg_start[1], seg_start[2]):
                items.append(('track', pL, seg_start[1], seg_start[2], px, py))
            items.append(('via', x, y)); seg_start = pts[k]; continue
        if k + 1 < len(pts) and pts[k + 1][0] == L:
            nx_, ny_ = pts[k + 1][1] - x, pts[k + 1][2] - y
            dx_, dy_ = x - px, y - py
            if abs(nx_ - dx_) < 1e-9 and abs(ny_ - dy_) < 1e-9:
                continue
        items.append(('track', L, seg_start[1], seg_start[2], x, y)); seg_start = pts[k]
    return items

def main():
    sock = 'ipc://' + max(glob.glob('/run/user/1000/backplane/kicad/*/api.sock'), key=os.path.getmtime)
    kc = KiCad(socket_path=sock, client_name='zm_gnd_fix', timeout_ms=300000)
    board = kc.get_board()
    gnd = [n for n in board.get_nets() if n.name == 'GND'][0]
    for it in range(8):
        cu, holes, frags, links = load(BOARD)
        main_g, iso = groups(frags, links)
        print('iteration %d: isolated groups %d' % (it, len(iso)))
        if not iso:
            break
        # route the biggest isolated group first, a few per iteration (fills change after each)
        iso.sort(key=lambda g: -sum(frags[i][1].area for i in g))
        new, ok = [], 0
        used = []
        for g in iso:
            P = unary_union([frags[i][1] for i in g])
            if any(P.distance(u) < 3 for u in used):
                continue
            items = route_one(cu, holes, frags, main_g, g)
            c = P.centroid
            if not items:
                print('  no path for group at (%.2f, %.2f)' % (c.x, c.y)); continue
            used.append(P)
            for itm in items:
                if itm[0] == 'track':
                    t = Track(); t.start = Vector2.from_xy_mm(itm[2], itm[3]); t.end = Vector2.from_xy_mm(itm[4], itm[5])
                    t.width = int(W * 1e6); t.layer = BoardLayer.BL_F_Cu if itm[1] == 'F.Cu' else BoardLayer.BL_B_Cu; t.net = gnd
                    new.append(t)
                else:
                    v = Via(); v.position = Vector2.from_xy_mm(itm[1], itm[2]); v.net = gnd
                    v.diameter = int(VIA_D * 1e6); v.drill_diameter = int(VIA_DR * 1e6)
                    new.append(v)
            ok += 1
            # block this route's copper for the next groups in the same iteration
            for itm in items:
                if itm[0] == 'track':
                    g2 = LineString([(itm[2], itm[3]), (itm[4], itm[5])]).buffer(W / 2)
                    cu['F.Cu' if itm[1] == 'F.Cu' else 'B.Cu'].append(g2)
                else:
                    g2 = Point(itm[1], itm[2]).buffer(VIA_D / 2); cu['F.Cu'].append(g2); cu['B.Cu'].append(g2)
        print('  routed %d groups, %d items' % (ok, len(new)))
        if not new:
            break
        c = board.begin_commit(); board.create_items(new); board.push_commit(c, 'GND island links')
        board.refill_zones(block=True, max_poll_seconds=180); board.save()

if __name__ == '__main__':
    main()
