"""Generate bancouver40_pb2.kicad_sch (v3) from design.py.

Single A1 sheet; one coloured box per block; ICs with short stubs + net labels, passives horizontal with a
label on the left and a label / power symbol on the right. Also writes zm_v3.kicad_sym (the custom symbols).
Usage: python3 gen_sch.py <out.kicad_sch>
"""
import sys, os, uuid, math, re
sys.path.insert(0, os.path.dirname(__file__))
from sexp import parse, dump, Sym, find, findall, fmt, q
import design as D

SYMDIR = '/home/bp/opt/backplane-kicad-10.99.0-bp.6/share/kicad/symbols'
G = 2.54
U = lambda: str(uuid.uuid4())
NS = uuid.UUID('6b1f2c1e-3c4d-4e5f-8a9b-0c1d2e3f4a5b')
UREF = lambda s: str(uuid.uuid5(NS, s))
ROOT_UUID = 'e63e39d7-6ac0-4ffd-8aa3-1841a4541b55'
PROJECT = 'bancouver40_pb2'

POWER_NETS = {'GND', '+3V3', '+5V_SYS', '+5V_BOOST', 'AVDD_3V3', 'HUB_3V3', 'VBAT', 'VIN_CHG'}
def is_power(n):
    return n in POWER_NETS

# label colours per bus (r, g, b)
COLOURS = [
    (r'^(I2S_|MCLK)', (180, 0, 180)), (r'^I2C_', (0, 140, 0)), (r'^USB', (0, 90, 200)),
    (r'^(VOUT_D|LCD_)', (200, 100, 0)), (r'^BL_', (150, 80, 0)), (r'^K', (0, 120, 120)),
    (r'^(HP_|LO_|MIC|CODEC_|LDO_)', (200, 0, 60)), (r'^(PWR_|CHG_|LED_|VBAT_)', (180, 30, 30)),
    (r'^HUB_', (0, 60, 160)),
]
def colour(n):
    for pat, c in COLOURS:
        if re.match(pat, n):
            return c
    return (0, 0, 0)

# ---------------------------------------------------------------- library symbols
def load_lib(lib, name):
    t = parse(open('%s/%s.kicad_symdir/%s.kicad_sym' % (SYMDIR, lib, name)).read())
    s = find(t, 'symbol')
    s[1] = '%s:%s' % (lib, name)
    return s

def lib_pins(sym):
    """pin number -> (x, y, angle) in lib coords (connection point)"""
    out = {}
    def walk(x):
        for e in x:
            if isinstance(e, list) and e:
                if e[0] == 'pin':
                    at = find(e, 'at'); num = find(e, 'number')[1]
                    out[num] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0)
                elif e[0] == 'symbol':
                    walk(e)
    walk(sym)
    return out

def renumber(sym, newname, mapping):
    sym[1] = newname
    def walk(x):
        for e in x:
            if isinstance(e, list) and e:
                if e[0] == 'pin':
                    num = find(e, 'number')
                    num[1] = mapping[num[1]]
                elif e[0] == 'symbol':
                    e[1] = e[1].replace(sym_old, newname.split(':')[1])
                    walk(e)
    sym_old = None
    return sym

LIBSYMS = {}
def libsym(kind):
    if kind in LIBSYMS:
        return LIBSYMS[kind]
    if kind == 'R':
        s = load_lib('Device', 'R_Small')
    elif kind == 'C':
        s = load_lib('Device', 'C_Small')
    elif kind == 'L':
        s = load_lib('Device', 'L_Small')
    elif kind == 'LED':
        s = load_lib('Device', 'LED_Small')
    elif kind == 'D_Schottky':
        s = load_lib('Device', 'D_Schottky_Small')
    elif kind == 'Crystal4':
        s = load_lib('Device', 'Crystal_GND24_Small')
    elif kind == 'MountingHole':
        s = load_lib('Mechanical', 'MountingHole')
    elif kind == 'TestPoint':
        s = load_lib('Connector', 'TestPoint')
    elif kind in ('PMOS', 'NMOS'):
        s = load_lib('Device', 'Q_' + kind)
        old = 'Q_' + kind
        s[1] = 'zm_v3:%s_GSD' % kind
        mp = {'G': '1', 'S': '2', 'D': '3'}
        def walk(x):
            for e in x:
                if isinstance(e, list) and e:
                    if e[0] == 'pin':
                        find(e, 'number')[1] = mp[find(e, 'number')[1]]
                    elif e[0] == 'symbol':
                        e[1] = e[1].replace(old, '%s_GSD' % kind); walk(e)
        walk(s)
    elif kind.startswith('PWR:'):
        s = power_sym(kind[4:])
    elif kind == 'PWR_FLAG':
        s = load_lib('power', 'PWR_FLAG')
    else:
        s = box_sym(kind)
    LIBSYMS[kind] = s
    return s

def power_sym(net):
    if net == 'GND':
        s = load_lib('power', 'GND')
        return s
    s = load_lib('power', 'VDD')
    s[1] = 'zm_v3:PWR_%s' % net.replace('+', 'P')
    def walk(x):
        for e in x:
            if isinstance(e, list) and e:
                if e[0] == 'property' and e[1] == 'Value':
                    e[2] = net
                elif e[0] == 'pin':
                    find(e, 'name')[1] = net
                elif e[0] == 'symbol':
                    e[1] = e[1].replace('VDD', 'PWR_%s' % net.replace('+', 'P')); walk(e)
    walk(s)
    return s

def font(size=1.27, hide=False, justify=None, bold=False):
    f = [Sym('font'), [Sym('size'), size, size]]
    if bold:
        f.append([Sym('bold'), Sym('yes')])
    e = [Sym('effects'), f]
    if justify:
        e.append([Sym('justify')] + [Sym(j) for j in justify.split()])
    if hide:
        e.append([Sym('hide'), Sym('yes')])
    return e

def prop(name, val, x=0, y=0, a=0, hide=False, justify=None):
    return [Sym('property'), name, val, [Sym('at'), x, y, a], font(hide=hide, justify=justify)]

def box_geom(kind):
    pins = D.SYMS[kind]
    side = {s: [p for p in pins if p[2] == s] for s in 'LRTB'}
    nl, nr = len(side['L']), len(side['R'])
    nt, nb = len(side['T']), len(side['B'])
    def tw(s):
        return max([len(p[1]) for p in side[s]] + [0]) * 1.27 * 0.85
    w = max(tw('L') + tw('R') + 5, (max(nt, nb) + 1) * 2 * G, 10)
    w = math.ceil(w / (2 * G)) * 2 * G
    toff = math.ceil((tw('T') + 1.5) / G) * G if nt else 0
    boff = math.ceil((tw('B') + 1.5) / G) * G if nb else 0
    P = 2 * G if kind in ('PocketBeagle2', 'ES8388', 'FE1.1s') else G
    h = max(nl, nr) * P + G + toff + boff
    h = math.ceil(h / (2 * G)) * 2 * G
    pos = {}
    for s, lst in side.items():
        for i, p in enumerate(lst):
            if s == 'L':
                pos[p[0]] = (-w / 2 - G, h / 2 - G - toff - i * P, 0)
            elif s == 'R':
                pos[p[0]] = (w / 2 + G, h / 2 - G - toff - i * P, 180)
            elif s == 'T':
                pos[p[0]] = (-(len(lst) - 1) * G + i * 2 * G, h / 2 + G, 270)
            else:
                pos[p[0]] = (-(len(lst) - 1) * G + i * 2 * G, -h / 2 - G, 90)
    # snap
    pos = {k: (round(v[0] / G * 2) * G / 2 if s_in_grid(v[0]) else v[0], v[1], v[2]) for k, v in pos.items()}
    return w, h, pos

def s_in_grid(x):
    return True

def box_sym(kind):
    pins = D.SYMS[kind]
    w, h, pos = box_geom(kind)
    name = 'zm_v3:' + kind.replace('.', '_')
    body = [Sym('symbol'), kind.replace('.', '_') + '_0_1',
            [Sym('rectangle'), [Sym('start'), -w / 2, h / 2], [Sym('end'), w / 2, -h / 2],
             [Sym('stroke'), [Sym('width'), 0.254], [Sym('type'), Sym('default')]],
             [Sym('fill'), [Sym('type'), Sym('background')]]]]
    pl = [Sym('symbol'), kind.replace('.', '_') + '_1_1']
    for num, pname, s, typ in pins:
        x, y, a = pos[num]
        pl.append([Sym('pin'), Sym(typ), Sym('line'), [Sym('at'), x, y, a], [Sym('length'), G],
                   [Sym('name'), pname, font()], [Sym('number'), str(num), font()]])
    sym = [Sym('symbol'), name,
           [Sym('pin_names'), [Sym('offset'), 0.762]],
           [Sym('exclude_from_sim'), Sym('no')], [Sym('in_bom'), Sym('yes')], [Sym('on_board'), Sym('yes')],
           prop('Reference', 'U', 0, h / 2 + 2.5), prop('Value', kind, 0, -h / 2 - 2.5),
           prop('Footprint', '', hide=True), prop('Datasheet', '', hide=True), prop('Description', '', hide=True),
           body, pl]
    return sym

# ---------------------------------------------------------------- transforms
def xform(px, py, rot, mirror=False):
    """lib (y up) -> sheet offset (y down), KiCad rotation CCW in degrees"""
    r = math.radians(rot)
    x = px * math.cos(r) - py * math.sin(r)
    y = px * math.sin(r) + py * math.cos(r)
    return (round(x, 4), round(-y, 4))

def pin_dir(angle, rot):
    """direction from pin connection point away from the body, in sheet coords"""
    # lib pin angle a: pin line goes from 'at' toward body in direction a; away = a+180
    a = math.radians(angle + 180 + rot)
    return (round(math.cos(a)), round(-math.sin(a)))

# ---------------------------------------------------------------- schematic items
items = []        # top-level sexp items (wires, labels, symbols, ...)
symbols = []

SHEET_PATH = ['/' + ROOT_UUID]
def wire(x1, y1, x2, y2):
    items.append([Sym('wire'), [Sym('pts'), [Sym('xy'), x1, y1], [Sym('xy'), x2, y2]],
                  [Sym('stroke'), [Sym('width'), 0], [Sym('type'), Sym('default')]], [Sym('uuid'), U()]])

GLOBAL_NETS = set()
def label(net, x, y, d):
    ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d]
    if net in GLOBAL_NETS:
        just = 'left' if ang in (0, 90) else 'right'
        items.append([Sym('global_label'), net, [Sym('shape'), Sym('bidirectional')], [Sym('at'), x, y, ang],
                      font(justify=just), [Sym('uuid'), U()],
                      [Sym('property'), 'Intersheetrefs', '${INTERSHEET_REFS}', [Sym('at'), x, y, 0],
                       font(hide=True)]])
        c = colour(net)
        if c != (0, 0, 0):
            items[-1][4][1].append([Sym('color'), c[0], c[1], c[2], 1])
        return
    just = 'left bottom' if ang in (0, 90) else 'right bottom'
    items.append([Sym('label'), net, [Sym('at'), x, y, ang], font(justify=just),
                  [Sym('uuid'), U()]])
    c = colour(net)
    if c != (0, 0, 0):
        # KiCad stores label colour via netclass/ directive; use text colour in effects
        items[-1][3][1].append([Sym('color'), c[0], c[1], c[2], 1])

def noconnect(x, y):
    items.append([Sym('no_connect'), [Sym('at'), x, y], [Sym('uuid'), U()]])

pwr_count = [0]
def power(net, x, y, d):
    """power symbol at (x,y); GND hangs down, rails point up (d only used to pick stub)"""
    kind = 'PWR:' + net
    s = libsym(kind)
    pwr_count[0] += 1
    ref = '#PWR%03d' % pwr_count[0]
    place(s[1], ref, net, x, y, 0, {}, hide_ref=True, val_at=(x, y + 3.5) if net == 'GND' else (x, y - 3.5),
          in_bom=False, power=True)

def place(lib_id, ref, value, x, y, rot, fields, hide_ref=False, val_at=None, ref_at=None, in_bom=True,
          dnp=False, power=False, hide_val=False, pins=()):
    props = [prop('Reference', ref, *(ref_at or (x, y - 3)), hide=hide_ref, justify=None),
             prop('Value', value, *(val_at or (x, y + 3)), hide=hide_val)]
    for k, v, show in fields:
        props.append(prop(k, v or '', x, y, hide=not show))
    sym = [Sym('symbol'), [Sym('lib_id'), lib_id], [Sym('at'), x, y, rot], [Sym('unit'), 1],
           [Sym('exclude_from_sim'), Sym('no')], [Sym('in_bom'), Sym('yes' if in_bom else 'no')],
           [Sym('in_pos_files'), Sym('no' if dnp else 'yes')],
           [Sym('on_board'), Sym('yes')], [Sym('dnp'), Sym('no')], [Sym('uuid'), U() if ref.startswith('#') else UREF('sym:' + ref)]] + props
    for p in pins:
        sym.append([Sym('pin'), str(p), [Sym('uuid'), U()]])
    sym.append([Sym('instances'), [Sym('project'), PROJECT, [Sym('path'), SHEET_PATH[0],
                                                             [Sym('reference'), ref], [Sym('unit'), 1]]]])
    symbols.append(sym)

def attach(net, x, y, d, stub=G):
    """from pin end (x,y) going d: stub + label / power / no-connect"""
    if net is None:
        noconnect(x, y)
        return
    ex, ey = x + d[0] * stub, y + d[1] * stub
    wire(x, y, ex, ey)
    if is_power(net):
        if net == 'GND':
            if d == (0, -1):      # pin points up: route around so GND still points down
                wire(ex, ey, ex + G, ey); wire(ex + G, ey, ex + G, ey + 2 * G)
                power(net, ex + G, ey + 2 * G, d)
            else:
                power(net, ex, ey, d)
        else:
            if d == (0, 1):
                wire(ex, ey, ex + G, ey); wire(ex + G, ey, ex + G, ey - 2 * G)
                power(net, ex + G, ey - 2 * G, d)
            else:
                power(net, ex, ey, d)
    else:
        label(net, ex, ey, d)

def label_len(net):
    return len(net) * 1.27 * 0.75 + (4.5 if net in GLOBAL_NETS else 1.5)

# ---------------------------------------------------------------- part drawing
def fields_of(p):
    return [('Footprint', p['fp'], False), ('Datasheet', '', False), ('MPN', p.get('mpn') or '', False),
            ('LCSC', p.get('lcsc') or '', False)]

def draw_box(p, x, y):
    kind = p['kind']
    s = libsym(kind)
    w, h, pos = box_geom(kind)
    first = lambda sd: next((p['pins'].get(str(n)) for n, _, s2, _ in D.SYMS[kind] if s2 == sd), None)
    pw_ = lambda n: bool(n) and is_power(n)
    if not pw_(first('R')):
        ra, va = (x + w / 2 + 0.5, y - h / 2 - 3.5), (x + w / 2 + 0.5, y - h / 2 - 1.0)
    else:
        ra, va = (x + w / 2 + 0.5, y + h / 2 + 2.0), (x + w / 2 + 0.5, y + h / 2 + 4.5)
    place(s[1], p['ref'], p['value'], x, y, 0, fields_of(p), ref_at=ra,
          val_at=va, dnp=p.get('dnp_bom', False),
          in_bom=not p['kind'] in ('MountingHole', 'TestPoint'), pins=[q for q, *_ in D.SYMS[kind]])
    # fix ref/value justification: left
    symbols[-1][9][4].append([Sym('justify'), Sym('left')]) if False else None
    for e in symbols[-1]:
        if isinstance(e, list) and e and e[0] == 'property' and e[1] in ('Reference', 'Value'):
            find(e, 'effects').append([Sym('justify'), Sym('left')])
    for side in 'LRTB':
        lst = [(num, p['pins'].get(str(num))) for num, _, sd, _ in D.SYMS[kind] if sd == side]
        d = {'L': (-1, 0), 'R': (1, 0), 'T': (0, -1), 'B': (0, 1)}[side]
        i = 0
        while i < len(lst):
            num, net = lst[i]
            j = i
            if net and is_power(net):
                while j + 1 < len(lst) and lst[j + 1][1] == net:
                    j += 1
            grp = lst[i:j + 1]
            ends = [(x + pos[n][0], y - pos[n][1]) for n, _ in grp]
            if not (net and is_power(net)):
                attach(net, ends[0][0], ends[0][1], d)
                i = j + 1
                continue
            stub = G
            if side in 'LR':
                idx = ([i - 1, i - 2] if net != 'GND' else [j + 1, j + 2])[:1 if p['kind'] in ('PocketBeagle2', 'ES8388', 'FE1.1s') else 2]
                nbs = [lst[k][1] for k in idx if 0 <= k < len(lst) and lst[k][1]]
                if nbs:
                    stub = G + max(6 if is_power(nb) else label_len(nb) for nb in nbs) + 2
                    stub = math.ceil(stub / G) * G + (2 * G if net != 'GND' else 0)
            if len(grp) == 1:
                attach(net, ends[0][0], ends[0][1], d, stub=stub)
            else:
                outs = [(ex + d[0] * stub, ey + d[1] * stub) for ex, ey in ends]
                for (ex, ey), (ox, oy) in zip(ends, outs):
                    wire(ex, ey, ox, oy)
                wire(outs[0][0], outs[0][1], outs[-1][0], outs[-1][1])
                if side in 'LR':
                    tx, ty = outs[-1] if net == 'GND' else outs[0]
                    if net == 'GND':
                        wire(tx, ty, tx, ty + G); power(net, tx, ty + G, d)
                    else:
                        wire(tx, ty, tx, ty - G); power(net, tx, ty - G, d)
                else:
                    tx, ty = outs[0]
                    if (side == 'T') == (net != 'GND'):
                        power(net, tx, ty, d)
                    else:
                        attach(net, tx, ty, d, stub=G)
            i = j + 1

def box_extent(p):
    w, h, pos = box_geom(p['kind'])
    ln = lambda s: max([label_len(p['pins'].get(str(n)) or 'x') for n, _, sd, _ in D.SYMS[p['kind']] if sd == s] + [3])
    pw = lambda s: 14 if any(p['pins'].get(str(n)) and is_power(p['pins'].get(str(n))) for n, _, sd, _ in D.SYMS[p['kind']] if sd == s) else 0
    left = w / 2 + G * 2 + max(ln('L'), pw('L'))
    right = w / 2 + G * 2 + max(ln('R'), pw('R'))
    top = h / 2 + G * 2 + (8 if any(sd == 'T' for _, _, sd, _ in D.SYMS[p['kind']]) else 3)
    bot = h / 2 + G * 2 + (8 if any(sd == 'B' for _, _, sd, _ in D.SYMS[p['kind']]) else 3)
    return left, right, top, bot

def draw_lib2(p, x, y):
    """2-pin library part drawn horizontally: pin 'a' left, pin 'b' right"""
    kind = p['kind']
    s = libsym(kind)
    lp = lib_pins(s)
    pins = p['pins']
    n1, n2 = pins.get('1'), pins.get('2')
    # orientation: keep power net on the right; GND always right
    flip = (is_power(n1) and not is_power(n2)) or (n1 == 'GND' and n2 != 'GND')
    left_pin, right_pin = ('2', '1') if flip else ('1', '2')
    # find rotation that puts left_pin at -x
    for rot in (0, 90, 180, 270):
        ox, oy = xform(lp[left_pin][0], lp[left_pin][1], rot)
        if ox < -0.5 and abs(oy) < 0.01:
            break
    place(s[1], p['ref'], p['value'], x, y, rot, fields_of(p), ref_at=(x, y - 2.2), val_at=(x, y + 2.2),
          dnp=p.get('dnp_bom', False), pins=['1', '2'])
    for e in symbols[-1]:
        if isinstance(e, list) and e and e[0] == 'property' and e[1] in ('Reference', 'Value'):
            find(e, 'at')[3] = rot % 180
    for pn in (left_pin, right_pin):
        ox, oy = xform(lp[pn][0], lp[pn][1], rot)
        attach(pins.get(pn), x + ox, y + oy, (-1, 0) if ox < 0 else (1, 0))

def lib2_extent(p):
    n1, n2 = p['pins'].get('1'), p['pins'].get('2')
    flip = (is_power(n1) and not is_power(n2)) or (n1 == 'GND' and n2 != 'GND')
    l, r = (n2, n1) if flip else (n1, n2)
    pwd = lambda n: max(6, len(n) * 0.65 + 4)
    wl = pwd(l) if is_power(l) else label_len(l) + G + 2.6
    wr = pwd(r) if is_power(r) else label_len(r) + G + 2.6
    return wl, wr, 6, 6

def draw_libn(p, x, y):
    """library parts with more pins (crystal, FETs, mounting hole, test point): rot 0, stubs outward"""
    kind = p['kind']
    s = libsym(kind)
    lp = lib_pins(s)
    place(s[1], p['ref'], p['value'], x, y, 0, fields_of(p), ref_at=(x + 7, y - 1.5), val_at=(x + 7, y + 1.5),
          dnp=p.get('dnp_bom', False), in_bom=kind not in ('MountingHole', 'TestPoint'), pins=list(lp))
    for pn, (px, py, a) in lp.items():
        d = pin_dir(a, 0)
        attach(p['pins'].get(pn), x + px, y - py, d)

def libn_extent(p):
    return 12, 22, 12, 12

def extent(p):
    if p['kind'] in D.SYMS and p['kind'] not in ('MountingHole', 'TestPoint'):
        return box_extent(p)
    if p['kind'] in ('R', 'C', 'L', 'LED', 'D_Schottky'):
        return lib2_extent(p)
    return libn_extent(p)

def draw(p, x, y):
    if p['kind'] in D.SYMS and p['kind'] not in ('MountingHole', 'TestPoint'):
        draw_box(p, x, y)
    elif p['kind'] in ('R', 'C', 'L', 'LED', 'D_Schottky'):
        draw_lib2(p, x, y)
    else:
        draw_libn(p, x, y)

# ---------------------------------------------------------------- block layout
BLOCKS = [  # name, title, colour, max width
    ('pb2', 'PocketBeagle 2 Industrial (face-down, USB-C to the rear)', (230, 240, 255), 200),
    ('display', '4.58" bar panel FPC + TPS61165 backlight (PWM on P1.06)', (255, 245, 225), 200),
    ('keys_left', 'Key scan chain, left: U10-U12 (under the PocketBeagle)', (225, 250, 245), 200),
    ('keys_right', 'Key scan chain, right: U13-U15 (+ mode keys)', (225, 250, 245), 200),
    ('keys', 'Keys: 40 Choc v1 + 3 mode keys, wired direct to the 165 chain (key to GND)', (235, 255, 235), 560),
    ('hub', 'USB hub FE1.1s on USB1 -> 2 rear USB-A', (230, 235, 255), 260),
    ('power', 'Power: USB-C charge in, IP5306 1S charger/boost, slide switch + P-FET, LEDs', (255, 235, 235), 260),
    ('audio', 'Audio: ES8388 codec (I2S master), headset TRRS + line-out TRS', (255, 235, 250), 260),
    ('mech', 'Mounting holes', (245, 245, 245), 140),
]

def layout_block(name, maxw):
    ps = [p for p in D.PARTS if p['block'] == name]
    # big parts first, then the rest in original order
    big = [p for p in ps if p['kind'] in D.SYMS and len(D.SYMS[p['kind']]) > 4 and p['kind'] not in ('ChocV1',)]
    small = [p for p in ps if p not in big]
    placed = []
    x0, y0 = 0.0, 0.0
    rowh = 0.0
    curx = 0.0
    cury = 0.0
    def put(p):
        nonlocal curx, cury, rowh
        l, r, t, b = extent(p)
        wtot = l + r
        if curx > 0 and curx + wtot > maxw:
            curx = 0; cury += rowh; rowh = 0
        placed.append((p, curx + l, cury + t))
        curx += wtot + 2
        rowh = max(rowh, t + b)
    for p in big:
        put(p)
    if big:
        curx = 0; cury += rowh; rowh = 0
    for p in small:
        put(p)
    w = max([pp[1] + extent(pp[0])[1] for pp in placed] + [10])
    h = cury + rowh
    return placed, w, h

def snap(v):
    return round(v / G) * G

SHEETS = [  # file, title, blocks, paper
    ('pb2_display', 'PocketBeagle 2 + display', ['pb2', 'display', 'mech'], 'A2'),
    ('keys', 'Keys and scan chain', ['keys_left', 'keys_right', 'keys'], 'A2'),
    ('usb_power', 'USB hub and power', ['hub', 'power'], 'A2'),
    ('audio', 'Audio', ['audio'], 'A2'),
]
PAPER = {'A3': (420, 297), 'A2': (594, 420), 'A1': (841, 594)}

def reset():
    items.clear(); symbols.clear()

def title_block(t, n):
    return [Sym('title_block'), [Sym('title'), 'Zine Machine main board v3: ' + t], [Sym('date'), '2026-11-06'],
            [Sym('rev'), '3'], [Sym('comment'), 1, 'bancouver40 + PocketBeagle 2 Industrial + 4.58in bar display'],
            [Sym('comment'), 2, 'Generated by tools/zm_v3/gen_sch.py from design.py']]

def write_sheet(path, sch_uuid, paper, tb, extra):
    libs = [parse(dump(LIBSYMS[k])) for k in LIBSYMS]
    sch = [Sym('kicad_sch'), [Sym('version'), 20250114], [Sym('generator'), 'eeschema'],
           [Sym('generator_version'), '9.0'], [Sym('uuid'), sch_uuid], [Sym('paper'), paper], tb,
           [Sym('lib_symbols')] + libs] + extra + items + symbols
    if path.endswith('bancouver40_pb2.kicad_sch'):
        sch.append([Sym('sheet_instances'), [Sym('path'), '/', [Sym('page'), '1']]])
    sch.append([Sym('embedded_fonts'), Sym('no')])
    open(path, 'w').write(dump(sch) + '\n')

def main(out):
    outdir = os.path.dirname(os.path.abspath(out))
    # nets that cross sheets -> global labels
    where = {}
    for f, t, blocks, paper in SHEETS:
        for p in D.PARTS:
            if p['block'] in blocks:
                for n in p['pins'].values():
                    if n and not is_power(n):
                        where.setdefault(n, set()).add(f)
    GLOBAL_NETS.update(n for n, fs in where.items() if len(fs) > 1)
    margin = 6.0
    sheet_syms = []
    all_custom = {}
    for page, (f, t, blocks, paper) in enumerate(SHEETS, start=2):
        reset()
        LIBSYMS.clear()
        sheet_uuid = UREF('sheet:' + f)
        SHEET_PATH[0] = '/' + ROOT_UUID + '/' + sheet_uuid
        pw, ph = PAPER[paper]
        rects, texts = [], []
        X, Y, rowh = 12.0, 22.0, 0.0
        for name in blocks:
            title, col_rgb, maxw = [b for b in BLOCKS if b[0] == name][0][1:4]
            placed, w, h = layout_block(name, min(maxw, pw - 30))
            rw, rh = w + 2 * margin, h + 2 * margin + 6
            if X > 12 and X + rw > pw - 10:
                X, Y, rowh = 12.0, Y + rowh + 6, 0.0
            bx, by = X, Y
            for p, px, py in placed:
                draw(p, snap(bx + margin + px), snap(by + margin + 6 + py))
            rects.append([Sym('rectangle'), [Sym('start'), bx, by], [Sym('end'), bx + rw, by + rh],
                          [Sym('stroke'), [Sym('width'), 0.4], [Sym('type'), Sym('default')],
                           [Sym('color'), int(col_rgb[0] * 0.6), int(col_rgb[1] * 0.6), int(col_rgb[2] * 0.6), 1]],
                          [Sym('fill'), [Sym('type'), Sym('color')], [Sym('color'), col_rgb[0], col_rgb[1], col_rgb[2], 0.35]],
                          [Sym('uuid'), U()]])
            texts.append([Sym('text'), title, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), bx + 2, by + 4.5, 0],
                          [Sym('effects'), [Sym('font'), [Sym('size'), 2.2, 2.2], [Sym('thickness'), 0.44],
                                            [Sym('bold'), Sym('yes')]], [Sym('justify'), Sym('left'), Sym('bottom')]],
                          [Sym('uuid'), U()]])
            X += rw + 6
            rowh = max(rowh, rh)
        # power flags on the sheet that holds the source
        fx = 14
        for n, blk in (('GND', 'power'), ('VBAT', 'power'), ('VIN_CHG', 'power'), ('+5V_SYS', 'power')):
            if blk in blocks:
                s = libsym('PWR_FLAG')
                pwr_count[0] += 1
                x, y = snap(fx), snap(ph - 30)
                place(s[1], '#FLG%02d' % pwr_count[0], 'PWR_FLAG', x, y, 0, [], hide_ref=True, in_bom=False, pins=['1'])
                attach(n, x, y, (0, 1))
                fx += 16
        if Y + rowh > ph - 35:
            print('WARNING sheet', f, 'overflows', Y + rowh, ph)
        write_sheet(os.path.join(outdir, f + '.kicad_sch'), U(), paper, title_block(t, page), rects + texts)
        for k, s in LIBSYMS.items():
            if str(s[1]).startswith('zm_v3:'):
                all_custom[str(s[1])] = s
        sheet_syms.append((f, t, sheet_uuid, page))
    # root sheet: sheet symbols + notes
    reset()
    LIBSYMS.clear()
    extra = []
    for i, (f, t, su, page) in enumerate(sheet_syms):
        x, y = 30 + (i % 2) * 120, 60 + (i // 2) * 60
        extra.append([Sym('sheet'), [Sym('at'), x, y], [Sym('size'), 90, 35],
                      [Sym('exclude_from_sim'), Sym('no')], [Sym('in_bom'), Sym('yes')], [Sym('on_board'), Sym('yes')],
                      [Sym('dnp'), Sym('no')], [Sym('fields_autoplaced'), Sym('yes')],
                      [Sym('stroke'), [Sym('width'), 0.2], [Sym('type'), Sym('solid')]],
                      [Sym('fill'), [Sym('color'), 240, 245, 255, 1]], [Sym('uuid'), su],
                      [Sym('property'), 'Sheetname', t, [Sym('at'), x, y - 0.7, 0], font(justify='left bottom')],
                      [Sym('property'), 'Sheetfile', f + '.kicad_sch', [Sym('at'), x, y + 35.6, 0],
                       font(justify='left top')],
                      [Sym('instances'), [Sym('project'), PROJECT, [Sym('path'), '/' + ROOT_UUID,
                                                                    [Sym('page'), str(page)]]]]])
    notes = ('Zine Machine main board v3 (bancouver40_pb2) - generated by tools/zm_v3/gen_sch.py from design.py; edit design.py and regenerate.\n'
             'Blocks: PocketBeagle 2 Industrial (face-down on its 3.55 mm sockets) + 4.58in RGB565 bar panel; 43 Choc v1 keys read by the\n'
             'Cortex-M4F through six 74HC165 (CLK P1.26, SH/LD P1.28, QH P2.05); FE1.1s hub on USB1 -> 2 rear USB-A; IP5306 1S charger/boost\n'
             'with a DPDT slide switch (P-FET on +5V_SYS + one KEY press); ES8388 codec (I2S master) -> headset TRRS + line-out TRS.\n'
             'Software: header pins with two balls (P1.04/06/12/26/28, P2.01/03/05/07/09/11) - mux only the ball named here, keep the twin an input.')
    extra.append([Sym('text'), notes, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), 30, 30, 0],
                  [Sym('effects'), [Sym('font'), [Sym('size'), 2, 2]], [Sym('justify'), Sym('left'), Sym('bottom')]],
                  [Sym('uuid'), U()]])
    write_sheet(out, ROOT_UUID, 'A3', title_block('overview', 1), extra)
    lib = [Sym('kicad_symbol_lib'), [Sym('version'), 20250114], [Sym('generator'), 'zm_v3']]
    for name, s in sorted(all_custom.items()):
        c = parse(dump(s)); c[1] = c[1].split(':', 1)[1]
        lib.append(c)
    open(os.path.join(outdir, 'zm_v3.kicad_sym'), 'w').write(dump(lib) + '\n')
    print('global nets', len(GLOBAL_NETS))
if __name__ == '__main__':
    main(sys.argv[1])
