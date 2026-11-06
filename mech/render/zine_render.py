# Blender product renders of the Zine Machine (mech/fitcheck_board_full.glb: the real main board from KiCad plus the
# tray, display chassis, panel, battery, PocketBeagle envelope and keycaps with legends).
#   blender -b -P mech/render/zine_render.py -- [samples] [views...]
# Writes mech/render/out/zine-<view>.png and mech/render/out/zine.blend.
import bpy, sys, math, os
from mathutils import Vector

ROOT = '/home/bp/projects/zinemachine0/.backplane/worktrees/backplane-871755f1'
SRC = ROOT + '/mech/fitcheck_board_full.glb'
OUTDIR = ROOT + '/mech/render/out'
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SAMPLES = int(args[0]) if args else 96
VIEWS = args[1:] or ['hero', 'top', 'rear', 'detail']
RES = (1920, 1200)
os.makedirs(OUTDIR, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

# ---------- materials ----------
def principled(name, color, rough=0.5, metal=0.0, coat=0.0, coat_rough=0.1, sss=0.0, emission=None, estrength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = coat_rough
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (0.5, 0.5, 0.5)
        b.inputs['Subsurface Scale'].default_value = 0.0005
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1)
        b.inputs['Emission Strength'].default_value = estrength
    return m

def base_color(o):
    if o.active_material and o.active_material.use_nodes:
        n = o.active_material.node_tree.nodes.get('Principled BSDF')
        if n: return tuple(n.inputs['Base Color'].default_value[:3])
    return (0.5, 0.5, 0.5)

M = {
    'tray': principled('Tray PLA', (0.0, 0.62, 0.80), rough=0.38, coat=0.15, coat_rough=0.3),
    'cap': principled('PBT keycap', (0.80, 0.77, 0.66), rough=0.62, sss=0.08),
    'chassis': principled('Chassis print', (0.85, 0.50, 0.05), rough=0.55),
    'glass': principled('Panel glass', (0.005, 0.006, 0.008), rough=0.12, coat=0.4, coat_rough=0.08),
    'foil': principled('Battery foil', (0.75, 0.76, 0.78), rough=0.32, metal=0.85),
    'mask_green': principled('Soldermask green', (0.02, 0.18, 0.06), rough=0.32, coat=0.5, coat_rough=0.12),
    'mask_red': principled('Soldermask red', (0.45, 0.02, 0.02), rough=0.32, coat=0.5, coat_rough=0.12),
    'metal': principled('Connector steel', (0.80, 0.80, 0.82), rough=0.25, metal=1.0),
    'black_plastic': principled('Black plastic', (0.02, 0.02, 0.022), rough=0.45),
}
mode_cache = {}
for o in meshes:
    n = o.name
    c = base_color(o)
    if n.startswith('Case'):
        mat = M['tray']
    elif n.startswith('K_Cap'):
        mat = M['cap']
    elif n.startswith('K_Legend'):
        key = ('leg',) + tuple(round(x, 2) for x in c)
        if key not in mode_cache:
            mode_cache[key] = principled('Legend', c, rough=0.5)
        mat = mode_cache[key]
    elif n.startswith('K_Mode_key'):
        key = ('mode',) + tuple(round(x, 2) for x in c)
        if key not in mode_cache:
            mode_cache[key] = principled('Mode key', c, rough=0.28, coat=0.6, coat_rough=0.08)
        mat = mode_cache[key]
    elif n.startswith('Display_chassis'):
        mat = M['chassis']
    elif n.startswith('Panel'):
        mat = M['glass']
    elif n.startswith('Battery'):
        mat = M['foil']
    elif n.startswith(('PB2_PCB',)):
        mat = M['mask_red']
    elif n.startswith('PB2_USB_C'):
        mat = M['metal']
    elif n.startswith(('K_PB2_Parts', 'K_PB2_Headers')):
        mat = M['black_plastic']
    else:                                   # board parts from KiCad: keep their colours, tune by hue
        r, g, b = c
        if g > r * 1.5 and g > b:          # green board
            mat = M['mask_green']
        elif abs(r - g) < 0.05 and abs(g - b) < 0.05 and r > 0.55:
            mat = M['metal']
        elif r < 0.12 and g < 0.12 and b < 0.12:
            mat = M['black_plastic']
        else:
            key = ('part',) + tuple(round(x, 2) for x in c)
            if key not in mode_cache:
                mode_cache[key] = principled('Part', c, rough=0.45)
            mat = mode_cache[key]
    o.data.materials.clear(); o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = False

# ---------- screen: an amber 'terminal' glow on the viewing area ----------
VA, AA_C = (0.1111, 0.03737), (0.08165, 0.0962)        # viewing area and its centre, metres (case coords)
panel = [o for o in meshes if o.name.startswith('Panel')]
if panel:
    ztop = max((o.matrix_world @ Vector(v)).z for o in panel for v in o.bound_box)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(AA_C[0], AA_C[1], ztop + 0.00005))
    scr = bpy.context.object; scr.scale = (VA[0], VA[1], 1); scr.name = 'Screen'
    m = bpy.data.materials.new('Screen'); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.004, 0.004, 0.005, 1)
    b.inputs['Roughness'].default_value = 0.4; b.inputs['Coat Weight'].default_value = 0.0
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (VA[0] / VA[1] * 2.2, 2.2, 1)
    br = nt.nodes.new('ShaderNodeTexBrick')
    br.inputs['Color1'].default_value = (1.0, 0.55, 0.08, 1); br.inputs['Color2'].default_value = (0.55, 0.28, 0.03, 1)
    br.inputs['Mortar'].default_value = (0.0, 0.0, 0.0, 1)
    br.inputs['Scale'].default_value = 6.0; br.inputs['Mortar Size'].default_value = 0.035
    br.inputs['Brick Width'].default_value = 0.22; br.inputs['Row Height'].default_value = 0.09
    br.offset = 0.37; br.squash = 1.0
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 40
    gate = nt.nodes.new('ShaderNodeMath'); gate.operation = 'GREATER_THAN'; gate.inputs[1].default_value = 0.42
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (0, 0, 0, 1)
    nt.links.new(tc.outputs['UV'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], br.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], nz.inputs['Vector'])
    nt.links.new(nz.outputs['Fac'], gate.inputs[0]); nt.links.new(gate.outputs['Value'], mix.inputs['Factor'])
    nt.links.new(br.outputs['Color'], mix.inputs['B'])
    nt.links.new(mix.outputs['Result'], b.inputs['Emission Color'])
    b.inputs['Emission Strength'].default_value = 2.2
    scr.data.materials.append(m)

# ---------- framing ----------
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in meshes:
    for v in o.bound_box:
        w = o.matrix_world @ Vector(v)
        mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
ctr = (mn + mx) / 2; size = (mx - mn).length
print('bounds', mn, mx)

# stage: a big sweep-ish floor
bpy.ops.mesh.primitive_plane_add(size=size * 60, location=(ctr.x, ctr.y, mn.z - 0.0002))
floor = bpy.context.object
floor.data.materials.append(principled('Stage', (0.035, 0.037, 0.042), rough=0.7))

world = bpy.data.worlds.new('World'); bpy.context.scene.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.012, 0.013, 0.016, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0

def area(name, loc, energy, sz, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.size = sz; l.color = color
    o = bpy.data.objects.new(name, l); bpy.context.scene.collection.objects.link(o)
    o.location = loc
    d = ctr - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return o
s = size
area('Key', ctr + Vector((-2.2 * s, -0.3 * s, 1.7 * s)), 8, 0.35)
area('Fill', ctr + Vector((1.8 * s, -1.0 * s, 1.0 * s)), 1.6, 0.5, (0.85, 0.92, 1.0))
area('Rim', ctr + Vector((0.4 * s, 2.0 * s, 1.2 * s)), 5, 0.25, (1.0, 0.95, 0.88))
area('Top', ctr + Vector((0, 0, 3.0 * s)), 1.2, 0.6)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.get_devices()
    for dev_type in ('OPTIX', 'CUDA', 'HIP', 'ONEAPI', 'METAL'):
        try:
            prefs.compute_device_type = dev_type
            if any(d.type == dev_type for d in prefs.devices):
                for d in prefs.devices: d.use = True
                scene.cycles.device = 'GPU'; break
        except TypeError:
            pass
except Exception as e:
    print('GPU setup skipped', e)
print('cycles device', scene.cycles.device)
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'

cam_data = bpy.data.cameras.new('Cam'); cam = bpy.data.objects.new('Cam', cam_data)
scene.collection.objects.link(cam); scene.camera = cam
cam_data.dof.use_dof = True

L = mx.x - mn.x; Wd = mx.y - mn.y
VIEW = {   # view direction from the target (unit-ish), target offset, lens, f-stop, framing (fraction of the model to fit)
    'hero':   (Vector((-0.45, -1.0, 0.62)), Vector((0, 0.02 * Wd, 0)), 85, 8, 1.0),
    'top':    (Vector((0.0, -0.18, 1.0)), Vector((0, 0, 0)), 85, 11, 1.0),
    'rear':   (Vector((0.55, 1.0, 0.42)), Vector((0.08 * L, 0.3 * Wd, 0)), 85, 8, 0.8),
    'detail': (Vector((0.75, -0.75, 0.45)), Vector((0.33 * L, 0.15 * Wd, 0.01)), 100, 4.5, 0.42),
    'exploded': (Vector((-0.55, -1.0, 0.55)), Vector((0, 0.05 * Wd, 0.055)), 85, 11, 1.35),
}
# exploded view: each layer lifted straight up (metres), by object-name prefix
EXPLODE = [('Case', 0.0), ('B_', 0.035), ('K_PB2', 0.058), ('PB2_', 0.058), ('Battery', 0.062),
           ('K_Cap', 0.08), ('K_Legend', 0.08), ('K_Mode_key', 0.08), ('Display_chassis', 0.095),
           ('Panel', 0.125), ('Screen', 0.125)]
exploded = False
sensor = 36.0
for v in VIEWS:
    if v == 'exploded' and not exploded:
        for o in list(scene.objects):
            dz = next((z for k, z in EXPLODE if o.name.startswith(k)), None)
            if dz is not None and o.type == 'MESH': o.location.z += dz
        exploded = True
    d, toff, lens, fstop, frac = VIEW[v]
    tgt = ctr + toff
    fov = 2 * math.atan(sensor / 2 / lens) * RES[1] / RES[0] * 1.1
    dist = (size * frac / 2) / math.tan(fov / 2)
    cam.location = tgt + d.normalized() * dist
    cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam_data.lens = lens; cam_data.sensor_width = sensor
    cam_data.dof.focus_distance = dist
    cam_data.dof.aperture_fstop = fstop
    scene.render.filepath = f'{OUTDIR}/zine-{v}.png'
    bpy.ops.render.render(write_still=True)
    print('wrote', scene.render.filepath)
bpy.ops.wm.save_as_mainfile(filepath=OUTDIR + '/zine.blend')
