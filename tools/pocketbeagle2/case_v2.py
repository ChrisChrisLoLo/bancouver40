"""Generate the SolidCraft command scripts for the v2 (4.58" bar LCD) case.  Case coordinates:
x 0..L, y 0..W from the front-left outer corner, z up; KiCad (kx, ky) -> case (kx - 71.775, 85.475 - ky).
  python3 case_v2.py OUTDIR   -> stage1_shell.json, stage2_features.json, stage3_bezel.json, stage4_fitcheck.json
"""
import json, os, sys

out = sys.argv[1]
k2c = lambda kx, ky: (round(kx - 71.775, 3), round(85.475 - ky, 3))
L, W, EXT_Y, H_KB, Z_DECK, BEZ = 175.2, 121.2, 71.6, 12.5, 21.1, 1.5
# z stack: PCB 4.5-6.1; PocketBeagle 2 on its own 8.5 mm sockets 14.6-16.1 (parts to ~18.05, USB-C to ~19.3);
# panel 18.6-21.1 glued under the bezel; bezel 21.1-22.6 resting on M2x15 standoffs (6.1 -> 21.1)
KB_BOSSES = [(19.6, 36.6), (53.6, 19.6), (53.6, 53.6), (121.6, 19.6), (121.6, 53.6), (155.6, 36.6)]
STANDOFFS = [k2c(88.0, -29.5), k2c(236.0, -29.5), k2c(236.0, 9.0)]
PB2 = dict(x0=k2c(74.9, 0)[0], y0=k2c(0, 10.2)[1])                       # PocketBeagle 2, 55 x 35
PANEL = dict(x0=k2c(99.975, 0)[0], x1=k2c(218.775, 0)[0], yc=k2c(0, -10.725)[1], h=41.57, t=2.5)
AA_C = k2c(157.425, -10.725)                                             # active-area centre
VA = (111.1, 37.37)
FPC_YC, FPC_GAP = k2c(0, -8.7)[1], 24.0
J3 = dict(x0=k2c(206.53, 0)[0], x1=k2c(213.28, 0)[0], y0=k2c(0, 5.47)[1], y1=k2c(0, -22.88)[1])


def cmd(c, **p):
    return {"command": c, "params": p}


def save(name, cmds):
    json.dump({"commands": cmds}, open(os.path.join(out, name), "w"), indent=0)


save("stage1_shell.json", [
    cmd("parameters.add", name="L", expression=f"{L} mm"),
    cmd("parameters.add", name="W", expression=f"{W} mm"),
    cmd("parameters.add", name="ext_y", expression=f"{EXT_Y} mm"),
    cmd("parameters.add", name="h_kb", expression=f"{H_KB} mm"),
    cmd("parameters.add", name="z_deck", expression=f"{Z_DECK} mm"),
    cmd("parameters.add", name="wall", expression="2 mm"),
    cmd("parameters.add", name="floor_t", expression="1 mm"),
    cmd("sketch.create", plane="XY", name="OuterSketch"),
    cmd("sketch.rectangle.rounded", p0=[0, 0], p1=[L, W], radius=3),
    cmd("sketch.finish"),
    cmd("solid.extrude", distance="z_deck", name="Outer", body_name="Case"),
    cmd("sketch.create", plane="XY", offset="floor_t", name="PocketSketch"),
    cmd("sketch.rectangle.rounded", p0=[2, 2], p1=[L - 2, W - 2], radius=1),
    cmd("sketch.finish"),
    cmd("solid.extrude", distance="z_deck", operation="cut", name="Pocket"),
    cmd("solid.box", length="L + 2", width="ext_y + 1", height="z_deck - h_kb + 1", corner=[-1, -1, "h_kb"],
        operation="cut", targets=["Case"], name="KeyboardWallStep"),
])

s2 = []
for i, (x, y) in enumerate(KB_BOSSES):
    s2 += [cmd("solid.cylinder", radius=1.8, height=3.5, base=[x, y, 1], operation="join", targets=["Case"], name=f"KbBoss{i+1}"),
           cmd("solid.cylinder", radius=0.875, height=3.5, base=[x, y, 1.0], operation="cut", targets=["Case"], name=f"KbPilot{i+1}")]
s2.append(cmd("solid.cylinder", radius=1, height=3, base=[62.1, 49.6, -1], operation="cut", targets=["Case"], name="ResetAccess"))
for i, (x, y) in enumerate(STANDOFFS):
    s2 += [cmd("solid.cylinder", radius=2.5, height=4.5, base=[x, y, 0], operation="join", targets=["Case"], name=f"StandoffBoss{i+1}"),
           cmd("solid.cylinder", radius=1.2, height=7, base=[x, y, -1], operation="cut", targets=["Case"], name=f"StandoffHole{i+1}"),
           cmd("solid.cylinder", radius=2.1, height=2.6, base=[x, y, -1], operation="cut", targets=["Case"], name=f"StandoffCbore{i+1}")]
pb_yc = PB2["y0"] + 17.5
s2.append(cmd("solid.box", length=4, width=14, height=10, corner=[-1, round(pb_yc - 7, 3), 13.5], operation="cut",
              targets=["Case"], name="PB2_USBC"))
for i in range(6):
    s2.append(cmd("solid.box", length=36, width=2, height=3, corner=[12, round(PB2["y0"] + 4 + i * 5, 3), -1],
                  operation="cut", targets=["Case"], name=f"Vent{i+1}"))
save("stage2_features.json", s2)

px0, px1, pyc, ph = PANEL["x0"], PANEL["x1"], PANEL["yc"], PANEL["h"]
fi = 0.3          # frame clearance around the panel
fw = 1.2          # frame wall
s3 = [
    cmd("parameters.add", name="bezel_t", expression=f"{BEZ} mm"),
    cmd("solid.box", length="L", width="W - ext_y", height="bezel_t", corner=[0, "ext_y", "z_deck"], operation="new",
        body_name="Bezel", name="BezelPlate"),
    cmd("solid.fillet", edges=[[0, W, Z_DECK + BEZ / 2], [L, W, Z_DECK + BEZ / 2]], radius=3, name="BezelCorners"),
    # panel locating frame under the plate (panel is glued to the plate's underside)
    cmd("solid.box", length=round(px1 - px0 + 2 * (fi + fw), 3), width=round(ph + 2 * (fi + fw), 3), height=PANEL["t"],
        corner=[round(px0 - fi - fw, 3), round(pyc - ph / 2 - fi - fw, 3), Z_DECK - PANEL["t"]], operation="join",
        targets=["Bezel"], name="PanelFrame"),
    cmd("solid.box", length=round(px1 - px0 + 2 * fi, 3), width=round(ph + 2 * fi, 3), height=PANEL["t"] + 0.01,
        corner=[round(px0 - fi, 3), round(pyc - ph / 2 - fi, 3), Z_DECK - PANEL["t"] - 0.01], operation="cut",
        targets=["Bezel"], name="PanelPocket"),
    cmd("solid.box", length=fw + 2, width=FPC_GAP, height=PANEL["t"] + 0.01,
        corner=[round(px1 + fi - 1, 3), round(FPC_YC - FPC_GAP / 2, 3), Z_DECK - PANEL["t"] - 0.01], operation="cut",
        targets=["Bezel"], name="FpcExit"),
    cmd("solid.box", length=VA[0], width=VA[1], height=4, center=[AA_C[0], AA_C[1], Z_DECK + BEZ / 2],
        operation="cut", targets=["Bezel"], name="LcdWindow"),
    cmd("solid.chamfer", edges=[[AA_C[0], round(AA_C[1] + VA[1] / 2, 3), Z_DECK + BEZ], [AA_C[0], round(AA_C[1] - VA[1] / 2, 3), Z_DECK + BEZ],
                                [round(AA_C[0] - VA[0] / 2, 3), AA_C[1], Z_DECK + BEZ], [round(AA_C[0] + VA[0] / 2, 3), AA_C[1], Z_DECK + BEZ]],
        distance=0.8, name="WindowChamfer"),
    cmd("solid.box", length=170.6, width=1.6, height=round(Z_DECK - 6.8, 3), corner=[2.3, "ext_y", 6.8], operation="join",
        targets=["Bezel"], name="Skirt"),
]
for i, (x, y) in enumerate(STANDOFFS):
    s3 += [cmd("solid.cylinder", radius=1.1, height=4, base=[x, y, Z_DECK - 1], operation="cut", targets=["Bezel"], name=f"BezelHole{i+1}"),
           cmd("solid.cylinder", radius=2.1, height=2, base=[x, y, Z_DECK + 0.5], operation="cut", targets=["Bezel"], name=f"BezelCbore{i+1}")]
save("stage3_bezel.json", s3)

s4 = [
    cmd("solid.box", length=170, width=116, height=1.6, corner=[2.6, 2.6, 4.5], operation="new", body_name="REF_PCB", name="RefPCB"),
    cmd("solid.box", length=round(px1 - px0, 3), width=ph, height=PANEL["t"], corner=[px0, round(pyc - ph / 2, 3), Z_DECK - PANEL["t"]],
        operation="new", body_name="REF_LCD_Panel", name="RefPanel"),
    cmd("solid.box", length=round(J3["x1"] - J3["x0"], 3), width=round(J3["y1"] - J3["y0"], 3), height=2.0,
        corner=[J3["x0"], J3["y0"], 6.1], operation="new", body_name="REF_J3_FPC_Conn", name="RefJ3"),
    # folded FPC: returns under the panel at z ~7, folds at the panel's east end
    cmd("solid.box", length=round(px1 + 6.0 - (J3["x1"] - 3), 3), width=20.5, height=0.3, corner=[round(J3["x1"] - 3, 3), round(FPC_YC - 10.25, 3), 7.4],
        operation="new", body_name="REF_FPC_Lower", name="RefFpcLow"),
    cmd("solid.box", length=0.3, width=20.5, height=12.2, corner=[round(px1 + 6.0, 3), round(FPC_YC - 10.25, 3), 7.4],
        operation="new", body_name="REF_FPC_Fold", name="RefFpcFold"),
] + [cmd("solid.box", length=46.2, width=5.0, height=8.5, corner=[round(PB2["x0"] + 4.4, 3), round(PB2["y0"] + yo, 3), 6.1],
          operation="new", body_name=f"REF_PB2_Socket{i+1}", name=f"RefSock{i+1}") for i, yo in enumerate((2.3, 27.7))
] + [cmd("solid.cylinder", radius=2.0, height=15, base=[x, y, 6.1], operation="new", body_name=f"REF_Standoff{i+1}", name=f"RefSO{i+1}")
     for i, (x, y) in enumerate(STANDOFFS)]
save("stage4_fitcheck.json", s4)
print("panel", round(px0, 2), round(px1, 2), "y", round(pyc - ph / 2, 2), round(pyc + ph / 2, 2), "window c", AA_C,
      "standoffs", STANDOFFS)
