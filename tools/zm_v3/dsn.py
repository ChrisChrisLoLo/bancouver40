"""Specctra bridge for Freerouting.
  python3 dsn.py export <board.kicad_pcb> <out.dsn> [--skip-nets GND]
  python3 dsn.py import <board.kicad_pcb> <in.ses> <out.kicad_pcb>
Export: every footprint becomes its own image with absolute pin positions (pad rotation baked into the padstack
shape), NPTH holes become unconnected pins, net classes from the .kicad_pro carry width/clearance/via, existing
segments are written as protected wiring. Y is negated (Specctra y up). Units: um.
Import: wires and vias from the session are appended to the board as segments/vias (existing copper kept).
"""
import sys, os, math, json, fnmatch, uuid
sys.path.insert(0, os.path.dirname(__file__))
from sexp import parse, dump, Sym, find, findall

MARGIN = 0.03
ALL = ['F.Cu', 'In2.Cu', 'B.Cu']     # In1 = GND plane, not routed (not in the DSN)
ROUTE_EXISTING = False
PROTECT_NETS = {'USB_UP_P', 'USB_UP_N', 'GND'}

def um(v):
    return '%.1f' % (v * 1000)

def rot(x, y, a):
    r = math.radians(a)
    return (x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r))

def load_classes(pro):
    d = json.load(open(pro))
    ns = d['net_settings']
    cls = {c['name']: c for c in ns['classes']}
    pats = ns.get('netclass_patterns', [])
    return cls, pats

def net_class(name, pats):
    for p in pats:
        if fnmatch.fnmatch(name, p['pattern']) or fnmatch.fnmatch(name.split('/')[-1], p['pattern']):
            return p['netclass']
    return 'Default'

def export(board, out, skip=()):
    b = parse(open(board).read())
    pro = os.path.splitext(board)[0] + '.kicad_pro'
    if not os.path.exists(pro):
        pro = os.path.join(os.path.dirname(os.path.abspath(board)), '..', 'bancouver40_pb2.kicad_pro')
    cls, pats = load_classes(pro)
    netnames = {int(n[1]): n[2] for n in findall(b, 'net')}
    # boundary: Edge.Cuts bbox, pulled in 0.2 mm, corners chamfered
    xs, ys = [], []
    for g in findall(b, 'gr_line') + findall(b, 'gr_arc'):
        if find(g, 'layer')[1] == 'Edge.Cuts':
            for k in ('start', 'end'):
                e = find(g, k); xs.append(float(e[1])); ys.append(float(e[2]))
    x0, y0, x1, y1 = min(xs) + 0.2, min(ys) + 0.2, max(xs) - 0.2, max(ys) - 0.2
    c = 0.8
    bpts = [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c), (x0 + c, y0)]
    padstacks = {}
    images = []
    places = []
    netpins = {}
    def padstack(shape, w, h, a, layers, drill):
        a = round(a) % 180 if shape in ('rect', 'roundrect', 'oval') else 0
        key = (shape, round(w, 3), round(h, 3), a, layers)
        if key in padstacks:
            return padstacks[key][0]
        name = 'PS%d' % len(padstacks)
        lay = ALL if layers == 'tht' else [layers]
        shapes = []
        for L in lay:
            if shape == 'circle':
                shapes.append('(shape (circle %s %s))' % (L, um(w)))
            elif shape == 'oval':
                # stadium: path along the long axis
                if w >= h:
                    p, q, wd = (-(w - h) / 2, 0), ((w - h) / 2, 0), h
                else:
                    p, q, wd = (0, -(h - w) / 2), (0, (h - w) / 2), w
                p, q = rot(*p, a), rot(*q, a)
                shapes.append('(shape (path %s %s %s %s %s %s))' % (L, um(wd), um(p[0]), um(-p[1]), um(q[0]), um(-q[1])))
            else:
                pts = [rot(px, py, a) for px, py in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
                shapes.append('(shape (polygon %s 0 %s))' % (L, ' '.join('%s %s' % (um(px), um(-py)) for px, py in pts)))
        padstacks[key] = (name, '(padstack %s %s (attach off))' % (name, ' '.join(shapes)))
        return name
    def padstack_poly(poly, a, layers):
        key = ('poly', tuple(poly), round(a), layers)
        if key in padstacks:
            return padstacks[key][0]
        name = 'PS%d' % len(padstacks)
        pts = [rot(px, py, a) for px, py in poly]
        lay = ALL if layers == 'tht' else [layers]
        shapes = ['(shape (polygon %s 0 %s))' % (L, ' '.join('%s %s' % (um(px), um(-py)) for px, py in pts)) for L in lay]
        padstacks[key] = (name, '(padstack %s %s (attach off))' % (name, ' '.join(shapes)))
        return name
    for fp in findall(b, 'footprint'):
        ref = [p[2] for p in findall(fp, 'property') if p[1] == 'Reference'][0]
        at = find(fp, 'at'); fx, fy = float(at[1]), float(at[2]); fa = float(at[3]) if len(at) > 3 else 0
        pins = []
        seen = {}
        for p in findall(fp, 'pad'):
            num, kind, shape = str(p[1]), str(p[2]), str(p[3])
            pat = find(p, 'at'); px, py = float(pat[1]), float(pat[2])
            pa = float(pat[3]) if len(pat) > 3 else fa      # pad angle in file is absolute
            sz = find(p, 'size'); w, h = float(sz[1]), float(sz[2])
            dx, dy = rot(px, py, fa)
            ax, ay = fx + dx, fy + dy
            lays = [str(l) for l in find(p, 'layers')[1:]]
            if kind in ('thru_hole', 'np_thru_hole'):
                layers = 'tht'
                if kind == 'np_thru_hole':
                    dr = find(p, 'drill')
                    d = float(dr[1]) if str(dr[1]) != 'oval' else float(dr[2])
                    shape, w, h = 'circle', max(w, d) + 0.12, max(w, d) + 0.12
            else:
                layers = 'F.Cu' if 'F.Cu' in lays else 'B.Cu'
            poly = None
            if shape == 'custom':
                prim = find(p, 'primitives')
                gp = find(prim, 'gr_poly') if prim else None
                if gp:
                    poly = [(float(xy[1]), float(xy[2])) for xy in findall(find(gp, 'pts'), 'xy')]
            if shape == 'roundrect' or shape == 'trapezoid' or shape == 'custom':
                shape = 'rect'
            if shape == 'circle':
                w = h = max(w, h)
            if poly:
                ps = padstack_poly(poly, pa, layers)
            else:
                ps = padstack(shape, w, h, pa, layers, None)
            pid = num if num else 'NP'
            seen[pid] = seen.get(pid, 0) + 1
            if seen[pid] > 1 or not num:
                pid = '%s@%d' % (pid, seen[pid])
            pins.append('(pin %s "%s" %s %s)' % (ps, pid, um(ax), um(-ay)))
            net = find(p, 'net')
            if net is not None and kind != 'np_thru_hole':
                nn = net[2] if len(net) > 2 else netnames.get(int(net[1]))
                if nn and not nn.startswith('unconnected-'):
                    netpins.setdefault(nn, []).append('"%s"-"%s"' % (ref, pid))
        img = 'IMG_' + ref
        images.append('(image %s %s)' % (img, ' '.join(pins)))
        places.append('(component %s (place "%s" 0 0 front 0))' % (img, ref))
    # vias per class
    vias = {}
    for cn, c in cls.items():
        vn = 'Via_%d_%d' % (round(c['via_diameter'] * 1000), round(c['via_drill'] * 1000))
        vias[cn] = vn
        if vn not in [v for v in padstacks]:
            padstacks[('via', vn)] = (vn, '(padstack %s %s (attach off))'
                                      % (vn, ' '.join('(shape (circle %s %s))' % (L, um(c['via_diameter'])) for L in ALL)))
    byclass = {}
    for n in netpins:
        if n in skip:
            continue
        byclass.setdefault(net_class(n, pats), []).append(n)
    d = cls['Default']
    out_s = ['(pcb "%s"' % os.path.basename(board),
             '(parser (string_quote ") (space_in_quoted_tokens on) (host_cad "KiCad\'s Pcbnew") (host_version "10"))',
             '(resolution um 10)', '(unit um)',
             '(structure (layer F.Cu (type signal) (property (index 0)))'
             ' (layer In2.Cu (type signal) (property (index 1))) (layer B.Cu (type signal) (property (index 2)))',
             '(boundary (path pcb 0 %s))' % ' '.join('%s %s' % (um(x), um(-y)) for x, y in bpts),
             '(via %s)' % ' '.join(sorted(set(vias.values()))),
             '(rule (width %s) (clearance %s) (clearance %s (type default_smd)) (clearance 50 (type smd_smd)))'
             % (um(d['track_width']), um(d['clearance'] + MARGIN), um(d['clearance'] + MARGIN)),
             '%%KO%%)',
             '(placement %s)' % ' '.join(places),
             '(library %s %s)' % (' '.join(images), ' '.join(v[1] for v in padstacks.values())),
             '(network']
    for n, pins in netpins.items():
        if n in skip:
            continue
        out_s.append('(net "%s" (pins %s))' % (n, ' '.join(pins)))
    for cn, nets in byclass.items():
        c = cls[cn]
        out_s.append('(class "%s" %s (circuit (use_via %s)) (rule (width %s) (clearance %s)))'
                     % (cn, ' '.join('"%s"' % n for n in nets), vias[cn], um(c['track_width']), um(c['clearance'] + MARGIN)))
    out_s.append(')')
    # existing copper as protected wiring
    wires = []
    extra_ps = []
    for s in findall(b, 'segment'):
        st, en = find(s, 'start'), find(s, 'end')
        net = find(s, 'net'); nn = netnames.get(int(net[1])) if len(net) == 2 else net[2]
        wtype = 'protect' if (nn in PROTECT_NETS or not ROUTE_EXISTING) else 'route'
        wires.append(('(wire (path %s %s %s %s %s %s) (net "%s") (type ' + wtype + '))')
                     % (find(s, 'layer')[1], um(float(find(s, 'width')[1])), um(float(st[1])), um(-float(st[2])),
                        um(float(en[1])), um(-float(en[2])), nn))
    for v in findall(b, 'via'):
        at = find(v, 'at'); net = find(v, 'net'); nn = netnames.get(int(net[1])) if len(net) == 2 else net[2]
        vn = 'Via_%d_%d' % (round(float(find(v, 'size')[1]) * 1000), round(float(find(v, 'drill')[1]) * 1000))
        if ('via', vn) not in padstacks:
            padstacks[('via', vn)] = (vn, '')
            extra_ps.append('(padstack %s %s (attach off))'
                            % (vn, ' '.join('(shape (circle %s %s))' % (L, um(float(find(v, 'size')[1]))) for L in ALL)))
        wires.append('(via %s %s %s (net "%s") (type protect))' % (vn, um(float(at[1])), um(-float(at[2])), nn))
    if skip:
        kept, kos = [], []
        for w_ in wires:
            if any('(net "%s")' % n in w_ for n in skip):
                if w_.startswith('(wire (path'):
                    parts = w_.split()
                    lay, wd = parts[2], float(parts[3]) / 1000
                    xy = [t.strip(')') for t in parts[4:8]]
                    kos.append('(keepout "" (path %s %s %s))' % (lay, um(wd + 0.05), ' '.join(xy)))
                else:
                    parts = w_.split()
                    x, y = parts[2], parts[3]
                    for L_ in ('F.Cu', 'In2.Cu', 'B.Cu'):
                        kos.append('(keepout "" (circle %s %s %s %s))' % (L_, um(0.5 + 0.35), x, y))
            else:
                kept.append(w_)
        wires = kept
        out_s = [l.replace('%%KO%%', ' '.join(kos)) for l in out_s]
    out_s = [l.replace('%%KO%%', '') for l in out_s]
    out_s.append('(wiring %s)' % ' '.join(wires))
    out_s = [l.replace('(library ', '(library %s ' % ' '.join(extra_ps), 1) if l.startswith('(library') else l for l in out_s]
    out_s.append(')')
    open(out, 'w').write('\n'.join(out_s) + '\n')
    print('dsn: %d components, %d nets, %d padstacks, %d protected wires' % (len(places), len(netpins), len(padstacks), len(wires)))

def import_ses(board, ses, out):
    b = parse(open(board).read())
    s = parse(open(ses).read())
    netnum = {n[2]: int(n[1]) for n in findall(b, 'net')}
    routes = find(s, 'routes')
    res = find(routes, 'resolution')
    scale = float(res[2]) if res else 10.0   # units per um
    k = 1.0 / (scale * 1000.0)               # -> mm
    no = find(routes, 'network_out')
    vias_ps = {}
    lib = find(routes, 'library_out')
    if lib:
        for ps in findall(lib, 'padstack'):
            sh = find(find(ps, 'shape'), 'circle')
            vias_ps[ps[1]] = float(sh[2]) * k
    added = [0, 0]
    newitems = []
    existing = set()
    for sg in findall(b, 'segment'):
        st, en = find(sg, 'start'), find(sg, 'end')
        existing.add((round(float(st[1]), 3), round(float(st[2]), 3), round(float(en[1]), 3), round(float(en[2]), 3)))
    exvias = set()
    for v in findall(b, 'via'):
        at = find(v, 'at'); exvias.add((round(float(at[1]), 2), round(float(at[2]), 2)))
    for net in findall(no, 'net'):
        name = net[1]
        nid = netnum[name]
        for w in findall(net, 'wire'):
            path = find(w, 'path')
            lay, width = str(path[1]), max(float(path[2]) * k, 0.127)
            pts = [(float(path[i]) * k, -float(path[i + 1]) * k) for i in range(3, len(path) - 1, 2)]
            for p, q in zip(pts, pts[1:]):
                key = (round(p[0], 3), round(p[1], 3), round(q[0], 3), round(q[1], 3))
                if key in existing or p == q:
                    continue
                newitems.append([Sym('segment'), [Sym('start'), round(p[0], 4), round(p[1], 4)],
                                 [Sym('end'), round(q[0], 4), round(q[1], 4)], [Sym('width'), round(width, 4)],
                                 [Sym('layer'), lay], [Sym('net'), nid], [Sym('uuid'), str(uuid.uuid4())]])
                added[0] += 1
        for v in findall(net, 'via'):
            ps = v[1]
            x, y = float(v[2]) * k, -float(v[3]) * k
            if (round(x, 2), round(y, 2)) in exvias:
                continue
            exvias.add((round(x, 2), round(y, 2)))
            dia = vias_ps.get(ps) or float(ps.split('_')[1]) / 1000
            drill = float(ps.split('_')[2]) / 1000 if ps.startswith('Via_') else 0.3
            newitems.append([Sym('via'), [Sym('at'), round(x, 4), round(y, 4)], [Sym('size'), round(dia, 3)],
                             [Sym('drill'), drill], [Sym('layers'), 'F.Cu', 'B.Cu'], [Sym('net'), nid],
                             [Sym('uuid'), str(uuid.uuid4())]])
            added[1] += 1
    # insert before the first zone / gr item at the end: just append before closing
    b += newitems
    open(out, 'w').write(dump(b) + '\n')
    print('imported %d segments, %d vias' % tuple(added))

if __name__ == '__main__':
    if sys.argv[1] == 'export':
        skip = sys.argv[sys.argv.index('--skip-nets') + 1].split(',') if '--skip-nets' in sys.argv else ()
        ROUTE_EXISTING = '--route-existing' in sys.argv
        export(sys.argv[2], sys.argv[3], skip)
    else:
        import_ses(sys.argv[2], sys.argv[3], sys.argv[4])
