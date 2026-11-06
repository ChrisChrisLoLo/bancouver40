"""Drive Backplane KiCad's SketchRoute over IPC (kipy transport + dynamic protobuf types).
Run with the kistack layout-placement Python (has kicad-python):
  ~/.cache/kistack/layout-placement/<hash>/bin/python tools/zm_v3/ipc_route.py <step> [args]
Steps: open | route <name> <filter> [layer] [time_ms] | refill | save | stats
"""
import sys, os, json, glob, fnmatch
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from kipy import KiCad
from kipy.proto.common.types import base_types_pb2
from kipy.proto.board import board_types_pb2
from kipy.proto.common.commands import editor_commands_pb2 as ec
from kipy.proto.board import board_commands_pb2 as bc

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'pcb', 'bancouver40_pb2'))
BOARD = os.path.join(PROJ, 'bancouver40_pb2.kicad_pcb')

def socket_path():
    socks = glob.glob('/run/user/1000/backplane/kicad/*/api.sock')
    return 'ipc://' + max(socks, key=os.path.getmtime)

def build_types():
    f = descriptor_pb2.FileDescriptorProto(name='backplane/sketch_route.proto', package='kiapi.backplane', syntax='proto3')
    f.dependency.extend([base_types_pb2.DESCRIPTOR.name, board_types_pb2.DESCRIPTOR.name])
    e = f.enum_type.add(name='SketchRouteCornerMode')
    for i, n in enumerate(['SRCM_UNKNOWN', 'SRCM_MITERED_45', 'SRCM_ROUNDED_45', 'SRCM_MITERED_90', 'SRCM_ROUNDED_90']):
        e.value.add(name=n, number=i)
    T = descriptor_pb2.FieldDescriptorProto
    m = f.message_type.add(name='SketchRoute')
    m.field.add(name='board', number=1, type=T.TYPE_MESSAGE, type_name='.kiapi.common.types.DocumentSpecifier')
    m.field.add(name='items', number=2, type=T.TYPE_MESSAGE, type_name='.kiapi.common.types.KIID', label=T.LABEL_REPEATED)
    m.field.add(name='guide', number=3, type=T.TYPE_MESSAGE, type_name='.kiapi.common.types.PolyLine')
    m.field.add(name='preferred_layer', number=4, type=T.TYPE_ENUM, type_name='.kiapi.board.types.BoardLayer')
    m.field.add(name='corner_mode', number=5, type=T.TYPE_ENUM, type_name='.kiapi.backplane.SketchRouteCornerMode')
    m.field.add(name='disallow_vias', number=6, type=T.TYPE_BOOL)
    m.field.add(name='time_limit_ms', number=7, type=T.TYPE_UINT32)
    r = f.message_type.add(name='SketchRouteResponse')
    for n, num, t in (('connections', 1, T.TYPE_INT32), ('routed', 2, T.TYPE_INT32), ('failed', 3, T.TYPE_INT32),
                      ('vias', 4, T.TYPE_INT32), ('length_nm', 5, T.TYPE_INT64), ('timed_out', 6, T.TYPE_BOOL),
                      ('elapsed_ms', 7, T.TYPE_DOUBLE)):
        r.field.add(name=n, number=num, type=t)
    r.field.add(name='created_items', number=8, type=T.TYPE_MESSAGE, type_name='.kiapi.common.types.KIID',
                label=T.LABEL_REPEATED)
    pool = descriptor_pool.Default()
    try:
        pool.Add(f)
    except Exception:
        pass
    get = lambda n: message_factory.GetMessageClass(pool.FindMessageTypeByName(n))
    return get('kiapi.backplane.SketchRoute'), get('kiapi.backplane.SketchRouteResponse')

def main():
    step = sys.argv[1]
    kc = KiCad(socket_path=socket_path(), client_name='zm_v3_route', timeout_ms=600000)
    if step == 'open':
        req = ec.OpenDocument(type=base_types_pb2.DOCTYPE_PCB, path=BOARD)
        print(kc._client.send(req, ec.OpenDocumentResponse))
        return
    board = kc.get_board()
    if step == 'route':
        name, filt = sys.argv[2], sys.argv[3]
        layer = sys.argv[4] if len(sys.argv) > 4 else ''
        tms = int(sys.argv[5]) if len(sys.argv) > 5 else 60000
        pads = json.load(open(os.path.join(PROJ, 'build', 'pads.json')))
        pats = filt.split(',')
        neg = [p[1:] for p in pats if p.startswith('!')]
        pos = [p for p in pats if not p.startswith('!')]
        def want(ref, net):
            if not net:
                return False
            key = net.split('/')[-1]
            if any(fnmatch.fnmatch(key, q) or fnmatch.fnmatch(ref + ':' + key, q) for q in neg):
                return False
            return any(fnmatch.fnmatch(key, q) or fnmatch.fnmatch(ref + ':' + key, q) for q in pos)
        ids = [u for ref, num, u, net in pads if want(ref, net)]
        SR, SRR = build_types()
        msg = SR()
        msg.board.CopyFrom(board._doc)
        for u in ids:
            msg.items.add(value=u)
        if layer:
            msg.preferred_layer = board_types_pb2.BoardLayer.Value(layer)
        msg.corner_mode = 1
        guide = os.environ.get('GUIDE')
        if guide:
            for pt in guide.split(';'):
                x, y = map(float, pt.split(','))
                nd = msg.guide.nodes.add()
                nd.point.x_nm = int(round(x * 1e6)); nd.point.y_nm = int(round(y * 1e6))
        if os.environ.get('NOVIAS'):
            msg.disallow_vias = True
        msg.time_limit_ms = tms
        commit = board.begin_commit()
        resp = kc._client.send(msg, SRR)
        board.push_commit(commit, 'route ' + name)
        board.save()
        print('%s: pads %d connections %d routed %d failed %d vias %d length %.0f mm timed_out %s %.0f ms'
              % (name, len(ids), resp.connections, resp.routed, resp.failed, resp.vias, resp.length_nm / 1e6,
                 resp.timed_out, resp.elapsed_ms))
    elif step == 'refill':
        board.refill_zones(block=True, max_poll_seconds=120)
        board.save()
        print('refilled')
    elif step == 'save':
        board.save(); print('saved')

if __name__ == '__main__':
    main()
