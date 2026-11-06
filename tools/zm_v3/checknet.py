"""compare a KiCad netlist with design.py: every design net must be exactly one netlist net"""
import sys; sys.path.insert(0, '.')
from sexp import parse, find, findall
import design as D
n = parse(open(sys.argv[1]).read())
got = {}
for net in findall(find(n, 'nets'), 'net'):
    nodes = frozenset((find(x, 'ref')[1], find(x, 'pin')[1]) for x in findall(net, 'node'))
    got[find(net, 'name')[1]] = nodes
want = {k: frozenset(v) for k, v in D.nets().items()}
bad = 0
bynode = {}
for name, nodes in got.items():
    for nd in nodes: bynode[nd] = name
for name, nodes in want.items():
    names = {bynode.get(nd) for nd in nodes}
    if len(names) != 1 or None in names:
        print('SPLIT/MISSING', name, names); bad += 1; continue
    gn = names.pop()
    if got[gn] != nodes:
        extra = got[gn] - nodes
        print('MERGED', name, '->', gn, 'extra', sorted(extra)[:6]); bad += 1
print('design nets', len(want), 'netlist nets', len(got), 'problems', bad)
