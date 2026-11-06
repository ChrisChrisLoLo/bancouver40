"""Plot the board's copper for review: SVG per layer (page fitted to the board) -> PNG, composited
(F.Cu red, B.Cu blue, fab grey, outline black). Optional crop window in KiCad mm.
python plot.py <board> <out.png> [x0 y0 x1 y1]"""
import sys, os, subprocess, glob, io
import cairosvg
from PIL import Image, ImageChops
K = '/home/bp/opt/backplane-kicad-10.99.0-bp.6/bin/kicad-cli'
BX0, BY0, BX1, BY1 = 74.375, -43.125, 244.375, 82.875
board, out = sys.argv[1], sys.argv[2]
d = '/tmp/zm_plot'
os.makedirs(d, exist_ok=True)
SCALE = int(os.environ.get('SCALE', 12))  # px per mm
layers = ('F.Cu', 'B.Cu', 'Edge.Cuts', 'F.Fab')
masks = {}
for lay in layers:
    f = os.path.join(d, lay.replace('.', '_') + '.svg')
    subprocess.run([K, 'pcb', 'export', 'svg', '--layers', lay + ',Edge.Cuts', '--mode-single', '--exclude-drawing-sheet',
                    '--fit-page-to-board', '--black-and-white', '-o', f, board], check=True, capture_output=True)
    png = cairosvg.svg2png(url=f, output_width=int((BX1 - BX0 + 0.0) * SCALE))
    im = Image.open(io.BytesIO(png)).convert('RGBA')
    masks[lay] = im.getchannel('A')
w, h = masks['F.Cu'].size
img = Image.new('RGB', (w, h), (255, 255, 255))
for lay, col, a in (('F.Fab', (160, 160, 160), 0.5), ('B.Cu', (40, 80, 230), 0.8), ('F.Cu', (220, 30, 30), 0.7),
                    ('Edge.Cuts', (0, 0, 0), 1.0)):
    img.paste(Image.new('RGB', (w, h), col), (0, 0), masks[lay].point(lambda v: int(v * a)))
ebb = masks['Edge.Cuts'].getbbox()          # board outline in pixels
ex0, ey0, ex1, ey1 = ebb
sx, sy = (ex1 - ex0) / (BX1 - BX0), (ey1 - ey0) / (BY1 - BY0)
if len(sys.argv) > 6:
    x0, y0, x1, y1 = map(float, sys.argv[3:7])
    img = img.crop((int(ex0 + (x0 - BX0) * sx), int(ey0 + (y0 - BY0) * sy), int(ex0 + (x1 - BX0) * sx), int(ey0 + (y1 - BY0) * sy)))
else:
    img = img.crop(ebb)
img.save(out)
print(out, img.size)
