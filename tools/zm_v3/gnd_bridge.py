"""Bridge isolated GND pour fragments to the main ground with vias placed where an isolated fragment overlaps the
main ground on the other layer (inside both fills by the via radius + margin, so clear of every other net).
Runs with the kistack layout-placement python (kicad-python + shapely); edits the open board over IPC.
"""
import sys, os, math, subprocess, glob
sys.path.insert(0, os.path.dirname(__file__))
from sexp import parse, find, findall
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from kipy import KiCad
from kipy.board_types import Via
from kipy.geometry import Vector2

BOARD = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'pcb', 'bancouver40_pb2', 'bancouver40_pb2.kicad_pcb'))

def rot(x, y, a):
    r = math.radians(a); return (x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r))

def groups_from_file(path):
    b = parse(open(path).read())
    def isgnd(e):
        n = find(e, 'net')
        return n is not None and 'GND' in [str(x) for x in n[1:]]
    frags = []
    for z in findall(b, 'zone'):
        if not isgnd(z): continue
        for fp in findall(z, 'filled_polygon'):
            lay = str(find(fp, 'layer')[1])
            pts = [(float(xy[1]), float(xy[2])) for xy in findall(find(fp, 'pts'), 'xy')]
            if len(pts) >= 3:
                frags.append((lay, Polygon(pts).buffer(0)))
    links = []
    for v in findall(b, 'via'):
        if isgnd(v):
            at = find(v, 'at'); links.append(Point(float(at[1]), float(at[2])).buffer(float(find(v, 'size')[1]) / 2 + 0.4))
    for fpt in findall(b, 'footprint'):
        t = find(fpt, 'transform')
        if t is not None:
            tr = find(t, 'translate'); ro = find(t, 'rotate')
            fx, fy, fa = float(tr[1]), float(tr[2]), (float(ro[1]) if ro is not None else 0)
        else:
            at = find(fpt, 'at'); fx, fy, fa = float(at[1]), float(at[2]), (float(at[3]) if len(at) > 3 else 0)
        for p in findall(fpt, 'pad'):
            if isgnd(p) and str(p[2]) == 'thru_hole':
                pat = find(p, 'at'); dx, dy = rot(float(pat[1]), float(pat[2]), fa)
                sz = find(p, 'size')
                links.append(Point(fx + dx, fy + dy).buffer(min(float(sz[1]), float(sz[2])) / 2 + 0.4))
    par = list(range(len(frags)))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for g in links:
        hit = [i for i, (L, P) in enumerate(frags) if P.intersects(g)]
        for i in hit[1:]: par[f(i)] = f(hit[0])
    for s in findall(b, 'segment'):
        if not isgnd(s): continue
        st, en = find(s, 'start'), find(s, 'end'); L = str(find(s, 'layer')[1])
        ln = LineString([(float(st[1]), float(st[2])), (float(en[1]), float(en[2]))]).buffer(0.1)
        hit = [i for i, (LL, P) in enumerate(frags) if LL == L and P.intersects(ln)]
        for i in hit[1:]: par[f(i)] = f(hit[0])
    gr = {}
    for i in range(len(frags)): gr.setdefault(f(i), []).append(i)
    main = max(gr.values(), key=lambda g: sum(frags[i][1].area for i in g))
    return frags, main, [g for g in gr.values() if g is not main]

def main():
    sock = 'ipc://' + max(glob.glob('/run/user/1000/backplane/kicad/*/api.sock'), key=os.path.getmtime)
    kc = KiCad(socket_path=sock, client_name='zm_gnd_bridge', timeout_ms=300000)
    board = kc.get_board()
    gnd = [n for n in board.get_nets() if n.name == 'GND'][0]
    # remove duplicate vias (same position)
    seen, dup = set(), []
    for v in board.get_vias():
        k = (round(v.position.x / 1000), round(v.position.y / 1000))
        if k in seen:
            dup.append(v)
        seen.add(k)
    if dup:
        c = board.begin_commit(); board.remove_items(dup); board.push_commit(c, 'remove duplicate vias')
        board.refill_zones(block=True, max_poll_seconds=180); board.save()
        print('removed %d duplicate vias' % len(dup))
    for it in range(6):
        frags, mg, iso = groups_from_file(BOARD)
        mainL = {L: unary_union([frags[i][1] for i in mg if frags[i][0] == L]) for L in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')}
        anyL = {L: unary_union([P for (LL, P) in frags if LL == L]) for L in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')}
        newv = []
        for g in iso:
            done = False
            # 4 layers: drop a via from the island to the In1 plane where every layer is ground fill
            for i in sorted(g, key=lambda i: -frags[i][1].area):
                L, P = frags[i]
                reg = P.buffer(-0.36)
                for L2 in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'):
                    if L2 == L:
                        continue
                    reg = reg.intersection((mainL[L2] if L2 == 'In1.Cu' else anyL[L2]).buffer(-0.36))
                    if reg.is_empty:
                        break
                if not reg.is_empty and not mainL['In1.Cu'].is_empty:
                    pt = reg.representative_point(); newv.append((pt.x, pt.y)); done = True
                    break
            if done:
                continue
            for i in sorted(g, key=lambda i: -frags[i][1].area):
                L, P = frags[i]
                other = 'B.Cu' if L == 'F.Cu' else 'F.Cu'
                inter = P.buffer(-0.36).intersection(mainL[other].buffer(-0.36))
                if inter.is_empty:
                    continue
                pt = inter.representative_point()
                newv.append((pt.x, pt.y)); done = True
                break
            if not done:
                # bridge to any fragment of another group on the other layer (chains reach the main ground over iterations)
                for i in sorted(g, key=lambda i: -frags[i][1].area):
                    L, P = frags[i]
                    other = 'B.Cu' if L == 'F.Cu' else 'F.Cu'
                    for j, (L2, Q) in enumerate(frags):
                        if L2 != other or j in g:
                            continue
                        inter = P.buffer(-0.36).intersection(Q.buffer(-0.36))
                        if not inter.is_empty:
                            pt = inter.representative_point(); newv.append((pt.x, pt.y)); done = True
                            break
                    if done:
                        break
        print('iteration %d: isolated groups %d, new vias %d' % (it, len(iso), len(newv)))
        if not newv:
            break
        items = []
        for x, y in newv:
            v = Via()
            v.position = Vector2.from_xy_mm(x, y)
            v.net = gnd
            v.diameter = 600000
            v.drill_diameter = 300000
            items.append(v)
        c = board.begin_commit()
        board.create_items(items)
        board.push_commit(c, 'GND bridge vias')
        board.refill_zones(block=True, max_poll_seconds=180)
        board.save()
    frags, mg, iso = groups_from_file(BOARD)
    for g in iso:
        for i in g:
            L, P = frags[i]; c = P.centroid
            print('still isolated %s %.2f mm2 at (%.2f, %.2f)' % (L, P.area, c.x, c.y))

if __name__ == '__main__':
    main()
