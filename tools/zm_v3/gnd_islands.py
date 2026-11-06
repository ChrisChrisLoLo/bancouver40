"""List GND pour fragments not connected to the main ground (via vias / THT pads / GND tracks).
python gnd_islands.py <filled board.kicad_pcb>"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from sexp import parse, find, findall
from shapely.geometry import Polygon, Point, LineString
b = parse(open(sys.argv[1]).read())
def netname(e):
    n = find(e, 'net')
    if n is None: return None
    return n[-1] if isinstance(n[-1], str) and not str(n[-1]).lstrip('-').isdigit() else n[1]
nets = {str(n[1]): n[2] for n in findall(b, 'net') if len(n) > 2}
def isgnd(e):
    n = find(e, 'net')
    if n is None: return False
    vals = [str(x) for x in n[1:]]
    return 'GND' in vals or any(nets.get(v) == 'GND' for v in vals)
frags = []
for z in findall(b, 'zone'):
    if not isgnd(z): continue
    for fp in findall(z, 'filled_polygon'):
        lay = str(find(fp, 'layer')[1])
        pts = [(float(xy[1]), float(xy[2])) for xy in findall(find(fp, 'pts'), 'xy')]
        if len(pts) >= 3:
            frags.append((lay, Polygon(pts).buffer(0)))
print('fragments', len(frags))
links = []   # (point, both layers) items: vias, THT GND pads
def rot(x, y, a):
    r = math.radians(a); return (x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r))
for v in findall(b, 'via'):
    if isgnd(v):
        at = find(v, 'at'); links.append(Point(float(at[1]), float(at[2])).buffer(0.2))
pads = {'F.Cu': [], 'B.Cu': []}
for fpt in findall(b, 'footprint'):
    at = find(fpt, 'at')
    if at is not None:
        fx, fy = float(at[1]), float(at[2]); fa = float(at[3]) if len(at) > 3 else 0
    else:
        t = find(fpt, 'transform'); tr = find(t, 'translate'); ro = find(t, 'rotate')
        fx, fy = float(tr[1]), float(tr[2]); fa = float(ro[1]) if ro is not None else 0
    for p in findall(fpt, 'pad'):
        if not isgnd(p): continue
        pat = find(p, 'at'); dx, dy = rot(float(pat[1]), float(pat[2]), fa)
        g = Point(fx + dx, fy + dy).buffer(0.3)
        if str(p[2]) == 'thru_hole': links.append(g)
        else: pads['F.Cu'].append(g)
# union-find over fragments
par = list(range(len(frags)))
def f(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
for g in links:
    hit = [i for i, (L, P) in enumerate(frags) if P.intersects(g)]
    for i in hit[1:]: par[f(i)] = f(hit[0])
# GND tracks join fragments on their layer
for s in findall(b, 'segment'):
    if not isgnd(s): continue
    st, en = find(s, 'start'), find(s, 'end'); L = str(find(s, 'layer')[1])
    ln = LineString([(float(st[1]), float(st[2])), (float(en[1]), float(en[2]))]).buffer(0.1)
    hit = [i for i, (LL, P) in enumerate(frags) if LL == L and P.intersects(ln)]
    for i in hit[1:]: par[f(i)] = f(hit[0])
groups = {}
for i in range(len(frags)): groups.setdefault(f(i), []).append(i)
main = max(groups.values(), key=lambda g: sum(frags[i][1].area for i in g))
for g in groups.values():
    if g is main: continue
    for i in g:
        L, P = frags[i]; c = P.centroid
        npad = sum(1 for q in pads.get(L, []) if P.intersects(q))
        print('isolated %s area %.2f mm2 at (%.2f, %.2f) smd-gnd-pads %d' % (L, P.area, c.x, c.y, npad))
