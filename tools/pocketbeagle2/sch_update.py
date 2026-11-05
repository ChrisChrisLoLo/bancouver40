"""Update the bancouver40 schematic to match pcb_extend.py / pcb_route.py.

  python3 tools/sch_update.py IN.kicad_sch OUT.kicad_sch

- removes the USB-C receptacle (J1), its CC resistors (R2, R3) and their wiring/labels
- adds U2 PocketBeagle 2 (72-pin, P1 left / P2 right), J3 (40-pin FPC for the 4.58" 320x960 bar LCD),
  the TPS61165 backlight boost (U3, L1, D41, C8-C10, R7, R8) and H11-H13
- connects everything with global labels (D+, D-, VOUT_Dn, LCD_*, BL_*) and power symbols (VBUS, GND, +3V3)
Symbol UUIDs are uuid5(ref), shared with pcb_extend.py so footprints stay linked to their symbols.
"""
import re
import sys
import uuid

NS = uuid.UUID("6f0c5d1e-8b1a-4c55-9d3a-b40a40b40b40")


def uid(key):
    return str(uuid.uuid5(NS, key))


src = open(sys.argv[1]).read()


# ---------------------------------------------------------------- s-expression helpers
def block_end(s, i):
    """index of the ')' closing the '(' at s[i], skipping quoted strings"""
    depth, j, n = 0, i, len(s)
    while j < n:
        c = s[j]
        if c == '"':
            j += 1
            while s[j] != '"':
                j += 2 if s[j] == "\\" else 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError("unbalanced")


def top_blocks(s):
    """(start, end, text) of every 2-space-indented top-level item"""
    for m in re.finditer(r"\n  \(", s):
        st = m.start() + 3
        en = block_end(s, st)
        yield st, en, s[st:en + 1]


def first_xy(blk):
    return [(float(a), float(b)) for a, b in re.findall(r"\((?:xy|at) ([-\d.]+) ([-\d.]+)", blk)]


# ---------------------------------------------------------------- 1. remove the USB-C block
REMOVE_REFS = {"J1", "R2", "R3"}
GND_SYMS_AT = {(176.53, 27.94), (140.97, 58.42)}   # GND symbols only J1/R2/R3 used
KEEP_WIRES = {((162.56, 20.32), (166.37, 20.32)), ((171.45, 20.32), (175.26, 20.32))}  # VBUS-fuse-+5V


def in_usb_box(x, y):
    return 128 <= x <= 185 and 14 <= y <= 62


cuts = []
removed_paths = []
for st, en, blk in top_blocks(src):
    kind = blk[1:blk.index(" ")]
    pts = first_xy(blk)
    if kind == "symbol":
        ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
        at = pts[0]
        if ref in REMOVE_REFS or (blk.startswith('(symbol (lib_id "power:GND")') and at in GND_SYMS_AT):
            cuts.append((st, en)); removed_paths.append(re.search(r"\(uuid ([-0-9a-f]+)\)", blk).group(1))
    elif kind in ("wire", "junction", "no_connect", "global_label"):
        ends = pts[:2] if kind == "wire" else pts[:1]
        if all(in_usb_box(*p) for p in ends):
            if kind == "wire" and tuple(ends) in KEEP_WIRES:
                continue
            cuts.append((st, en))
out = src
for st, en in sorted(cuts, reverse=True):
    out = out[:st - 3] + out[en + 1:]
for p in removed_paths:
    out = re.sub(r'\n    \(path "/' + p + r'"\n.*?\n    \)', "", out, flags=re.S)

out = out.replace('(paper "A4")', '(paper "A3")')

# ---------------------------------------------------------------- 2. library symbols
F = '(effects (font (size 1.27 1.27))'
# must match P1N / P2N in pcb_extend.py (the PCB names no-connect pads after these)
P1 = ["VIN_5V", "GPIO1_10", "USB1_DRVVBUS", "GPIO1_12", "USB1_VBUS", "GPIO1_13", "VIN_USB", "GPIO1_14",
      "USB1_D-", "GPIO1_30", "USB1_D+", "GPIO1_8", "GPIO0_36", "VDD_3V3", "GND", "GND", "AIN_REF-", "AIN_REF+",
      "AIN0", "VOUT0_D5", "AIN1", "GND", "AIN2", "VOUT", "AIN3", "GPIO0_44", "AIN4", "GPIO0_43", "VOUT0_DE",
      "UART0_TXD", "VOUT0_D14", "UART0_RXD", "I2C1_SDA_D11", "GPIO1_2", "GPIO0_88", "I2C1_SCL_D10"]
P2 = ["GPIO1_11_PWM", "VOUT0_D0", "GPIO0_85", "VOUT0_D1", "MCAN0_TX", "VOUT0_D2", "MCAN0_RX", "VOUT0_D3",
      "GPIO1_22", "GPIO0_91", "GPIO1_23", "PWR_BTN", "VOUT_VSYS", "VBAT", "GND", "BAT_TEMP", "VOUT0_PCLK",
      "VOUT0_D8", "GPIO1_0", "VOUT0_D4", "GND", "VOUT0_VSYNC", "VDD_3V3", "VOUT0_D6", "SPI0_D1", "nRESET",
      "SPI0_D0", "VOUT0_HSYNC", "SPI0_CLK", "VOUT0_D13", "SPI0_CS0", "VOUT0_D12", "VOUT0_D7", "VOUT0_D15",
      "VOUT0_D9", "SPI0_CS1"]
POWER_OUT = {("P1", 24), ("P2", 23)}  # VOUT 5 V, VDD_3V3


def pin(num, name, x, y, ang, etype="passive", length=5.08):
    return (f'      (pin {etype} line (at {x} {y} {ang}) (length {length})\n'
            f'        (name "{name}" {F}))\n        (number "{num}" {F}))\n      )\n')


def libsym(name, ref, value, fp, ds, rect, pins, ref_y, val_y):
    short = name.split(":")[1]
    return (f'    (symbol "{name}" (in_bom yes) (on_board yes)\n'
            f'      (property "Reference" "{ref}" (id 0) (at 0 {ref_y} 0)\n        {F})\n      )\n'
            f'      (property "Value" "{value}" (id 1) (at 0 {val_y} 0)\n        {F})\n      )\n'
            f'      (property "Footprint" "{fp}" (id 2) (at 0 0 0)\n        {F} hide)\n      )\n'
            f'      (property "Datasheet" "{ds}" (id 3) (at 0 0 0)\n        {F} hide)\n      )\n'
            f'      (symbol "{short}_0_1"\n        (rectangle (start {rect[0]} {rect[1]}) (end {rect[2]} {rect[3]})\n'
            f'          (stroke (width 0.254) (type default) (color 0 0 0 0))\n          (fill (type background))\n        )\n      )\n'
            f'      (symbol "{short}_1_1"\n{pins}      )\n    )\n')


PX = 30.48          # pin tips; body is +/-25.4 so the long pin names fit
pb_pins = ""
for n in range(1, 37):
    y = round(44.45 - (n - 1) * 2.54, 2)
    pb_pins += pin(n, f"P1.{n:02d} {P1[n - 1]}", -PX, y, 0, "power_out" if ("P1", n) in POWER_OUT else "passive")
    pb_pins += pin(36 + n, f"P2.{n:02d} {P2[n - 1]}", PX, y, 180, "power_out" if ("P2", n) in POWER_OUT else "passive")
LIB_PB2 = libsym("bancouver40_pb2:PocketBeagle2", "U", "PocketBeagle2", "Module:BeagleBoard_PocketBeagle",
                 "https://docs.beagleboard.org/boards/pocketbeagle-2/", (-25.4, 46.99, 25.4, -46.99), pb_pins, 49.53, -49.53)

# 4.58" 320x960 bar TFT FPC (Maxen MX-046HS40FS-N01 / BuyDisplay ER-TFT4.58-1 pinout)
FPC_NAMES = (["LEDA", "LEDK", "LEDK", "GND", "VCI", "RESET", "NC", "NC", "SDA", "SCK", "CS", "PCLK", "DE",
              "VSYNC", "HSYNC"] + [f"DB{i}" for i in range(18)] +
             ["GND", "TP_INT", "TP_SDA", "TP_SCL", "TP_RESET", "TP_VCI", "GND"])
fpc_pins = "".join(pin(n, FPC_NAMES[n - 1], -7.62, round(49.53 - (n - 1) * 2.54, 2), 0) for n in range(1, 41))
fpc_pins += pin("MP", "SHIELD", 0, -53.34, 90)
LIB_FPC = libsym("bancouver40_pb2:LCD_FPC40", "J", "LCD_FPC40",
                 "Connector_FFC-FPC:Amphenol_F32Q-1A7x1-11040_1x40-1MP_P0.5mm_Horizontal",
                 "https://maxen-lcddisplay.com/wp-content/uploads/2025/07/MX-046HS40FS-N01.pdf",
                 (-2.54, 50.8, 7.62, -50.8), fpc_pins, 52.07, -55.88)
tps_pins = (pin(1, "VIN", -10.16, 2.54, 0, "power_in") + pin(2, "CTRL", -10.16, -2.54, 0, "input") +
            pin(3, "SW", 10.16, 2.54, 180, "passive") + pin(5, "COMP", 10.16, -2.54, 180, "passive") +
            pin(6, "FB", 10.16, -5.08, 180, "input") + pin(4, "GND", 0, -12.7, 90, "power_in"))
LIB_TPS = libsym("bancouver40_pb2:TPS61165DBV", "U", "TPS61165DBV", "Package_TO_SOT_SMD:SOT-23-6",
                 "https://www.ti.com/lit/ds/symlink/tps61165.pdf", (-5.08, 5.08, 5.08, -7.62), tps_pins, 7.62, -10.16)
LIB_L = libsym("bancouver40_pb2:L", "L", "L", "", "~", (-2.54, 0.762, 2.54, -0.762),
               pin(1, "1", -5.08, 0, 0, length=2.54) + pin(2, "2", 5.08, 0, 180, length=2.54), 2.54, -2.54)
LIB_L = LIB_L.replace('(name "1"', '(name "1"').replace("(in_bom yes) (on_board yes)",
                                                         "(pin_names (offset 0) hide) (in_bom yes) (on_board yes)", 1)
# +3V3 power symbol: clone the embedded power:+5V definition
m = re.search(r'\n    \(symbol "power:\+5V".*?\n    \)\n', out, flags=re.S)
LIB_3V3 = m.group(0).replace("+5V", "+3V3")
out = out.replace("\n  (lib_symbols\n", "\n  (lib_symbols\n" + LIB_PB2 + LIB_FPC + LIB_TPS + LIB_L +
                  LIB_3V3.lstrip("\n"), 1)

# ---------------------------------------------------------------- 3. placed items
items = []
instances = []
pwr_n = [100]


def fields(ref, value, fp, x, y, ref_dy=-3, val_dy=3, hide_ref=False):
    h = " hide" if hide_ref else ""
    return (f'    (property "Reference" "{ref}" (id 0) (at {x} {round(y + ref_dy, 2)} 0)\n      {F}{h})\n    )\n'
            f'    (property "Value" "{value}" (id 1) (at {x} {round(y + val_dy, 2)} 0)\n      {F})\n    )\n'
            f'    (property "Footprint" "{fp}" (id 2) (at {x} {y} 0)\n      {F} hide)\n    )\n'
            f'    (property "Datasheet" "~" (id 3) (at {x} {y} 0)\n      {F} hide)\n    )\n')


def place_symbol(lib_id, ref, value, fp, x, y, pins, ref_dy=-3, val_dy=3, hide_ref=False, in_bom=True):
    u = uid(ref)
    pin_txt = "".join(f'    (pin "{p}" (uuid {uid(ref + ":" + str(p))}))\n' for p in pins)
    items.append(f'  (symbol (lib_id "{lib_id}") (at {x} {y} 0) (unit 1)\n    (in_bom {"yes" if in_bom else "no"}) (on_board yes)\n'
                 f'    (uuid {u})\n' + fields(ref, value, fp, x, y, ref_dy, val_dy, hide_ref) + pin_txt + '  )\n')
    instances.append(f'    (path "/{u}"\n      (reference "{ref}") (unit 1) (value "{value}") (footprint "{fp}")\n    )\n')


def power(name, x, y, down):
    pwr_n[0] += 1
    ref = f"#PWR0{pwr_n[0]}"
    place_symbol(f"power:{name}", ref, name, "", x, y, ["1"], ref_dy=(6.35 if down else -6.35),
                 val_dy=(3.81 if down else -3.81), hide_ref=True)


def wire(a, b):
    items.append(f'  (wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]}))\n'
                 f'    (stroke (width 0) (type default) (color 0 0 0 0))\n    (uuid {uid("w" + str(a + b))})\n  )\n')


def glabel(name, x, y, left):
    ang, just = (180, "right") if left else (0, "left")
    items.append(f'  (global_label "{name}" (shape input) (at {x} {y} {ang}) (fields_autoplaced)\n'
                 f'    {F} (justify {just}))\n    (uuid {uid("gl" + name + str((x, y)))})\n'
                 f'    (property "Intersheet References" "${{INTERSHEET_REFS}}" (id 0) (at {x} {y} 0)\n'
                 f'      {F} hide)\n    )\n  )\n')


def noconnect(x, y):
    items.append(f'  (no_connect (at {x} {y}) (uuid {uid("nc" + str((x, y)))}))\n')


def text(s, x, y):
    items.append(f'  (text "{s}" (at {x} {y} 0)\n    {F} (justify left bottom))\n    (uuid {uid("t" + s)})\n  )\n')


POWER = {"GND", "VBUS", "+3V3"}
STEP = {"left": (-2.54, 0), "right": (2.54, 0), "up": (0, -2.54), "down": (0, 2.54)}


def attach(net, pt, d, n=2):
    """wire n grid steps out of a pin end, then a power symbol or a global label"""
    dx, dy = STEP[d]
    end = (round(pt[0] + n * dx, 2), round(pt[1] + n * dy, 2))
    wire(pt, end)
    if net in POWER:
        if d in ("left", "right") and net == "GND" or d in ("left", "right"):
            end2 = (round(end[0] + dx, 2), end[1])
            wire(end, end2); end = end2
        power(net, end[0], end[1], down=(net == "GND"))
    elif d in ("up", "down"):
        glabel(net, end[0], end[1], left=False)
    else:
        glabel(net, end[0], end[1], left=(d == "left"))


# U2 PocketBeagle 2
UX, UY = 229.87, 201.93   # on the 1.27 mm grid, clear of the matrix and title block
place_symbol("bancouver40_pb2:PocketBeagle2", "U2", "PocketBeagle 2", "Module:BeagleBoard_PocketBeagle",
             UX, UY, range(1, 73), ref_dy=-48.26, val_dy=48.26)
NETS = {("P1", 9): "D-", ("P1", 11): "D+", ("P1", 24): "VBUS",
        ("P1", 15): "GND", ("P1", 16): "GND", ("P1", 22): "GND", ("P2", 15): "GND", ("P2", 21): "GND",
        ("P2", 23): "+3V3",
        ("P2", 25): "LCD_SDA", ("P2", 29): "LCD_SCK", ("P2", 31): "LCD_CS", ("P2", 10): "LCD_RESET",
        ("P2", 1): "BL_PWM",
        ("P2", 17): "LCD_PCLK", ("P1", 29): "LCD_DE", ("P2", 22): "LCD_VSYNC", ("P2", 28): "LCD_HSYNC",
        ("P2", 2): "VOUT_D0", ("P2", 4): "VOUT_D1", ("P2", 6): "VOUT_D2", ("P2", 8): "VOUT_D3",
        ("P2", 20): "VOUT_D4", ("P1", 20): "VOUT_D5", ("P2", 24): "VOUT_D6", ("P2", 33): "VOUT_D7",
        ("P2", 18): "VOUT_D8", ("P2", 35): "VOUT_D9", ("P1", 36): "VOUT_D10", ("P1", 33): "VOUT_D11",
        ("P2", 32): "VOUT_D12", ("P2", 30): "VOUT_D13", ("P1", 31): "VOUT_D14", ("P2", 34): "VOUT_D15"}
for hdr, sx, d in (("P1", UX - PX, "left"), ("P2", UX + PX, "right")):
    for n in range(1, 37):
        py = round(UY - (44.45 - (n - 1) * 2.54), 2)
        px = round(sx, 2)
        net = NETS.get((hdr, n))
        if net is None:
            noconnect(px, py)
        else:
            attach(net, (px, py), d)

# J3 panel FPC: ST7701S 18-bit (MDT=1) DB17..12=R5..R0, DB11..6=G5..G0, DB5..0=B5..B0; RGB565 from the AM62,
# R0/B0 LSBs grounded
DB = {17: "VOUT_D15", 16: "VOUT_D14", 15: "VOUT_D13", 14: "VOUT_D12", 13: "VOUT_D11", 12: "GND",
      11: "VOUT_D10", 10: "VOUT_D9", 9: "VOUT_D8", 8: "VOUT_D7", 7: "VOUT_D6", 6: "VOUT_D5",
      5: "VOUT_D4", 4: "VOUT_D3", 3: "VOUT_D2", 2: "VOUT_D1", 1: "VOUT_D0", 0: "GND"}
J3N = {1: "BL_LEDA", 2: "BL_LEDK", 3: "BL_LEDK", 4: "GND", 5: "+3V3", 6: "LCD_RESET",
       9: "LCD_SDA", 10: "LCD_SCK", 11: "LCD_CS", 12: "LCD_PCLK", 13: "LCD_DE", 14: "LCD_VSYNC",
       15: "LCD_HSYNC", 34: "GND", 40: "GND"}
J3N.update({16 + i: DB[i] for i in range(18)})
JX, JY = 320.04, 205.74
J3_FP = "Connector_FFC-FPC:Amphenol_F32Q-1A7x1-11040_1x40-1MP_P0.5mm_Horizontal"
place_symbol("bancouver40_pb2:LCD_FPC40", "J3", "F32Q-1A7H1-11040 (40p 0.5mm FPC, top contact)", J3_FP,
             JX, JY, list(range(1, 41)) + ["MP"], ref_dy=-52.07, val_dy=58.42)
for n in range(1, 41):
    pt = (round(JX - 7.62, 2), round(JY - 49.53 + (n - 1) * 2.54, 2))
    if n in J3N:
        attach(J3N[n], pt, "left")
    else:
        noconnect(*pt)
attach("GND", (JX, round(JY + 53.34, 2)), "down", 1)

# backlight: TPS61165 boost, 2 strings x 4 LEDs, 11.2-13.2 V @ 40 mA; Rsense = 0.2 V / 39 mA
BX, BY = 370.84, 180.34
place_symbol("bancouver40_pb2:TPS61165DBV", "U3", "TPS61165DBV", "Package_TO_SOT_SMD:SOT-23-6", BX, BY,
             range(1, 7), ref_dy=-8.89, val_dy=17.78)
attach("VBUS", (BX - 10.16, BY - 2.54), "left")
attach("BL_PWM", (BX - 10.16, BY + 2.54), "left")
attach("BL_SW", (BX + 10.16, BY - 2.54), "right")
attach("BL_COMP", (BX + 10.16, BY + 2.54), "right")
attach("BL_LEDK", (BX + 10.16, BY + 5.08), "right")
attach("GND", (BX, BY + 12.7), "down", 1)
place_symbol("bancouver40_pb2:L", "L1", "22uH", "Inductor_SMD:L_Bourns-SRN4018", 370.84, 160.02, [1, 2])
attach("VBUS", (365.76, 160.02), "left")
attach("BL_SW", (375.92, 160.02), "right")
place_symbol("Device:D_Small", "D41", "MBR0540", "Diode_SMD:D_SOD-123", 397.51, 160.02, [1, 2])
attach("BL_LEDA", (394.97, 160.02), "left")          # pin 1 = cathode
attach("BL_SW", (400.05, 160.02), "right")
for i, (ref, val, fp, top) in enumerate([
        ("C8", "4.7uF 10V", "Capacitor_SMD:C_0805_2012Metric", "VBUS"),
        ("C9", "1uF 50V", "Capacitor_SMD:C_0805_2012Metric", "BL_LEDA"),
        ("C10", "220nF", "Capacitor_SMD:C_0603_1608Metric", "BL_COMP"),
        ("R7", "5.1R 1%", "Resistor_SMD:R_0603_1608Metric", "BL_LEDK"),
        ("R8", "100k", "Resistor_SMD:R_0603_1608Metric", "BL_PWM")]):
    x, y = round(350.52 + i * 12.7, 2), 213.36
    place_symbol("Device:C_Small" if ref.startswith("C") else "Device:R_Small", ref, val, fp, x, y, [1, 2],
                 ref_dy=-1.27, val_dy=1.27)
    attach(top, (x, round(y - 2.54, 2)), "up")
    attach("GND", (x, round(y + 2.54, 2)), "down", 1)

# bezel standoffs
for i in range(3):
    place_symbol("Mechanical:MountingHole", f"H{11 + i}", "M2x15 bezel standoff", "MountingHole:MountingHole_2.2mm_M2",
                 350.52 + i * 12.7, 238.76, [], ref_dy=-2, val_dy=2, in_bom=False)

text("PocketBeagle 2: USB1 host <- ATmega32U4 (D+/D-); VOUT (P1.24) powers the keyboard via F1.", 105.41, 180.34)
text("P1.05 USB1_VBUS left open (host mode needs no VBUS sense).", 105.41, 184.15)
text("LCD: 4.58in 320x960 ST7701S, RGB565 on VOUT0 (DPI) + 3-wire SPI on SPI0 for init.", 105.41, 187.96)
text("VOUT0_D10/D11 share P1.36/P1.33 with I2C1: keep the I2C1 balls unmuxed.", 105.41, 191.77)
text("Backlight: TPS61165, 39 mA, PWM on P2.01 (ECAP2 APWM, mode 2).", 105.41, 195.58)

body = "".join(items)
out = out.replace("\n  (sheet_instances", "\n" + body + "\n  (sheet_instances", 1)
out = out.replace("  (symbol_instances\n", "  (symbol_instances\n" + "".join(instances), 1)
open(sys.argv[2], "w").write(out)
print(f"removed {len(cuts)} items ({len(removed_paths)} symbols); added {len(instances)} symbols")
