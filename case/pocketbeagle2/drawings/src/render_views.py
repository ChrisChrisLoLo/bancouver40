#!/usr/bin/env python3
"""Render every drawing view with solidcraft-cli snapshot (orthographic, known mm->px scale).
Camera: orthographic (fov 0) => visible half-height = 0.4*distance mm, so px/mm s = H/(0.8*distance).
View coordinates (u right, v up):  top: (x, y)   front: (x, z)   left: (-y, z)   right: (y, z)   bottom: (x, -y)
Writes img/<name>.png (background made white) and img/views.json (target, s, W, H, uv window per view).
usage: render_views.py [name ...]   (no names = all)"""
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = "/Applications/SolidCraft.app/Contents/MacOS/solidcraft-cli"
PD = "/Users/elevenarms/Code/cadkey/bancouver40/case/pocketbeagle2"
STEP = f"{PD}/bancouver40_pb2_case.step"
ASM = f"{PD}/bancouver40_pb2.solidcraft"
IMG = os.path.join(HERE, "img")
os.makedirs(IMG, exist_ok=True)
HIDE = {}
for b in ("Case", "Bezel"):
    p = os.path.join(HERE, f"hide_{b}.json")
    json.dump({"commands": [{"command": "browser.visibility", "params": {"visible": False, "items": [b]}}]}, open(p, "w"))
    HIDE[b] = p
PI2 = math.pi / 2
CAM = {  # yaw, pitch, function (u,v,depth) -> world target
    "top": (0, PI2, lambda u, v, d: [u, v, d]),
    "bottom": (0, -PI2, lambda u, v, d: [u, -v, d]),
    "front": (0, 0, lambda u, v, d: [u, d, v]),
    "left": (PI2, 0, lambda u, v, d: [d, -u, v]),
    "right": (-PI2, 0, lambda u, v, d: [d, u, v]),
}
CASE = dict(src=STEP, script=HIDE["Bezel"], bodies=["Case:color=#f6f6f6"])
BEZ = dict(src=STEP, script=HIDE["Case"], bodies=["Bezel:color=#f6f6f6"])
ASMB = dict(src=ASM, script=None, bodies=["Case:opacity=1,color=#e2e2e2", "Bezel:opacity=1,color=#c9d6e3"], flood=True)
sec = lambda o, n: {"plane": {"origin": o, "normal": n}}
VIEWS = {
    # name: (model, view, u-range, v-range, depth for target, px/mm, section)
    "c_top":   (CASE, "top",   (-3, 178.2), (-3, 124.2), 10, 8, None),
    "c_front": (CASE, "front", (-3, 178.2), (-1.5, 22.6), 60, 8, None),
    "c_left":  (CASE, "left",  (-124.2, 3), (-1.5, 22.6), 87, 8, None),
    "c_secD":  (CASE, "right", (-3, 124.2), (-1.5, 22.6), 87.6, 8, sec([87.6, 0, 0], [1, 0, 0])),
    "c_vent":  (CASE, "top",   (-3, 54), (74, 111), 10, 16, None),
    "c_usb":   (CASE, "left",  (-106, -79.5), (-1.5, 23), 1, 20, None),
    "c_secA":  (CASE, "front", (47.5, 59.7), (-0.8, 6.0), 19.6, 40, sec([0, 19.6, 0], [0, -1, 0])),
    "c_secB":  (CASE, "front", (9.7, 22.7), (-0.8, 6.0), 114.975, 40, sec([0, 114.975, 0], [0, -1, 0])),
    "b_top":   (BEZ, "top",    (-3, 178.2), (69.0, 124.2), 22, 8, None),
    "b_front": (BEZ, "front",  (-3, 178.2), (5.3, 23.6), 60, 8, None),
    "b_bot":   (BEZ, "bottom", (-3, 178.2), (-124.2, -69.0), 22, 8, None),
    "b_secE":  (BEZ, "right",  (69.0, 124.2), (5.3, 23.6), 60, 24, sec([60, 0, 0], [1, 0, 0])),
    "b_detC":  (BEZ, "right",  (72.8, 79.6), (18.0, 23.2), 60, 80, sec([60, 0, 0], [1, 0, 0])),
    "b_secF":  (BEZ, "front",  (11.0, 21.5), (17.9, 23.2), 114.975, 48, sec([0, 114.975, 0], [0, -1, 0])),
    "a_secG":  (ASMB, "right", (-3, 124.2), (-1.5, 24.0), 48, 16, sec([48, 0, 0], [1, 0, 0])),
    "a_detH":  (ASMB, "right", (67.5, 123.2), (-1.0, 24.0), 48, 32, sec([48, 0, 0], [1, 0, 0])),
    "a_secK":  (ASMB, "front", (-3, 178.2), (-1.5, 24.0), 96, 8, sec([0, 96, 0], [0, -1, 0])),
}
ISO = {"c_iso": (CASE, 1200, 800), "b_iso": (BEZ, 1200, 600), "a_iso": (ASMB, 1400, 900)}


def whiten(path, flood):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    bg = (a[..., 2] - a[..., 0] >= 5) & (a[..., 0] > 150)          # the blue-grey viewport gradient
    if flood:   # only background connected to the border (the assembly has coloured parts)
        m = Image.fromarray((bg * 255).astype(np.uint8)).copy()
        h, w = bg.shape
        for sx, sy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
            if m.getpixel((sx, sy)) == 255:
                ImageDraw.floodfill(m, (sx, sy), 128)
        bg = np.asarray(m) == 128
    a[bg] = 255
    a[a.min(axis=2) >= 242] = 255                               # near-white shading -> paper white
    Image.fromarray(a.astype(np.uint8)).save(path)


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])


def render(name):
    out = os.path.join(IMG, f"{name}.png")
    if name in ISO:
        m, W, H = ISO[name]
        args = [CLI, "snapshot"] + ([m["script"]] if m["script"] else []) + ["--in", m["src"], "--out", out,
                "--width", str(W), "--height", str(H), "--view", "iso", "--no-grid", "--no-axes"]
        for b in m["bodies"]:
            args += ["--body", b]
        run(args)
        whiten(out, m.get("flood", False))
        return {"view": "iso", "W": W, "H": H}
    m, view, ur, vr, depth, s, section = VIEWS[name]
    W = round((ur[1] - ur[0]) * s); H = round((vr[1] - vr[0]) * s)
    tu, tv = (ur[0] + ur[1]) / 2, (vr[0] + vr[1]) / 2
    yaw, pitch, tgt = CAM[view]
    D = H / (0.8 * s)
    cam = {"target": tgt(tu, tv, depth), "yaw": yaw, "pitch": pitch, "distance": D, "fov": 0}
    args = [CLI, "snapshot"] + ([m["script"]] if m["script"] else []) + ["--in", m["src"], "--out", out,
            "--width", str(W), "--height", str(H), "--camera", json.dumps(cam), "--no-grid", "--no-axes"]
    for b in m["bodies"]:
        args += ["--body", b]
    if section:
        args += ["--section", json.dumps(section)]
    run(args)
    whiten(out, m.get("flood", False))
    return {"view": view, "u": [tu - W / s / 2, tu + W / s / 2], "v": [tv - H / s / 2, tv + H / s / 2],
            "s": s, "W": W, "H": H, "camera": cam, "section": section}


if __name__ == "__main__":
    meta_p = os.path.join(IMG, "views.json")
    meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
    names = sys.argv[1:] or list(VIEWS) + list(ISO)
    for n in names:
        meta[n] = render(n)
        print(n, meta[n].get("W"), meta[n].get("H"), flush=True)
        json.dump(meta, open(meta_p, "w"), indent=1)
