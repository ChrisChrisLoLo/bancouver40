"""Stage 1 (v2): extend the bancouver40 PCB north for a PocketBeagle 2 + 4.58" 320x960 bar LCD.

Run with KiCad's bundled python (see build_pcb.sh):  pcb_extend.py IN OUT
- new 48 mm extension outline (no USB tab)
- U2 PocketBeagle 2, J3 40-pin 0.5 mm FPC connector for the panel, U3 TPS61165 backlight boost + passives,
  H11-H13 bezel standoff holes
- assigns every new net (routing is pcb_route.py)

Panel: Maxen MX-046HS40FS-N01 / BuyDisplay ER-TFT4.58-1 class 4.58" bar TFT, ST7701S, 18-bit RGB + 3-wire SPI.
It is glued under the bezel above the PocketBeagle; its FPC leaves the panel's east end and folds 180 deg
back under the panel into J3.
"""
import sys
import uuid
import pcbnew
from pcbnew import VECTOR2I, FromMM as MM

SRC, DST = sys.argv[1], sys.argv[2]
FP = "/Users/elevenarms/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"

# ---- geometry (KiCad board coordinates, mm, y down) -------------------------
X0, X1 = 74.375, 244.375          # unchanged left/right edges
Y_TOP, Y_BOT = -33.125, 82.875    # was 14.875 at the top: 48 mm extension
R_CORNER = 1.5
PB2_CENTER = (102.4, -7.3)        # PocketBeagle 2 board centre, USB-C end facing -X
PANEL = dict(x0=99.975, x1=218.775, yc=-10.725, h=41.57)   # 118.8 x 41.57 panel outline (for reference)
FPC_YC = -8.7                     # FPC centre line (drawing: tail 8.53 mm in from one long edge)
J3_POS = (210.5, FPC_YC)          # connector centre; cable entry faces +X (towards the fold).
                                  # Panel at z 18.6-21.1 (above the PocketBeagle on its 8.5 mm sockets): the
                                  # 30 mm tail = 1 straight + ~19 fold (r~6) + ~10 return -> cable end at x ~209.8
STANDOFFS = [(88.0, -29.5), (236.0, -29.5), (236.0, 9.0)]

PARTS = [  # (lib, footprint, ref, value, (x, y), rot)
    ("Module", "BeagleBoard_PocketBeagle", "U2", "PocketBeagle 2",
     (PB2_CENTER[0] + 21.59, PB2_CENTER[1] - 13.97), -90),
    ("Connector_FFC-FPC", "Amphenol_F32Q-1A7x1-11040_1x40-1MP_P0.5mm_Horizontal", "J3",
     "F32Q-1A7H1-11040 (40p 0.5mm FPC, top contact)", J3_POS, 90),
    ("Package_TO_SOT_SMD", "SOT-23-6", "U3", "TPS61165DBV", (234.0, -10.0), 0),
    ("Inductor_SMD", "L_Bourns-SRN4018", "L1", "22uH", (234.0, -16.0), 0),
    ("Diode_SMD", "D_SOD-123", "D41", "MBR0540", (240.0, -13.0), 90),
    ("Capacitor_SMD", "C_0805_2012Metric", "C8", "4.7uF 10V", (229.0, -14.0), 90),
    ("Capacitor_SMD", "C_0805_2012Metric", "C9", "1uF 50V", (242.5, -9.0), 90),
    ("Capacitor_SMD", "C_0603_1608Metric", "C10", "220nF", (230.5, -7.0), 0),
    ("Resistor_SMD", "R_0603_1608Metric", "R7", "5.1R 1%", (234.0, -5.0), 0),
    ("Resistor_SMD", "R_0603_1608Metric", "R8", "100k", (238.5, -5.0), 0),
] + [("MountingHole", "MountingHole_2.2mm_M2", f"H{11 + i}", "M2x15 bezel standoff", p, 0)
     for i, p in enumerate(STANDOFFS)]

b = pcbnew.LoadBoard(SRC)
IO = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)  # pcbnew.FootprintLoad is broken here
# load every footprint before editing the board: this build's SWIG proxies go stale after Remove()
PRELOADED = []
for lib, name, *_ in PARTS:
    f = IO.FootprintLoad(FP + lib + ".pretty", name)
    f.SetFPID(pcbnew.LIB_ID(lib, name))
    PRELOADED.append(f)

# ---- board outline ------------------------------------------------------------
def seg(a, c):
    s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(VECTOR2I(MM(a[0]), MM(a[1]))); s.SetEnd(VECTOR2I(MM(c[0]), MM(c[1])))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1)); b.Add(s)


def arc(start, mid, end):
    s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(*(VECTOR2I(MM(p[0]), MM(p[1])) for p in (start, mid, end)))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1)); b.Add(s)


r = R_CORNER
k = r * (1 - 0.70710678)
seg((X0 + r, Y_TOP), (X1 - r, Y_TOP)); seg((X1, Y_TOP + r), (X1, Y_BOT - r))
seg((X1 - r, Y_BOT), (X0 + r, Y_BOT)); seg((X0, Y_BOT - r), (X0, Y_TOP + r))
arc((X1 - r, Y_TOP), (X1 - k, Y_TOP + k), (X1, Y_TOP + r))
arc((X1, Y_BOT - r), (X1 - k, Y_BOT - k), (X1 - r, Y_BOT))
arc((X0 + r, Y_BOT), (X0 + k, Y_BOT - k), (X0, Y_BOT - r))
arc((X0, Y_TOP + r), (X0 + k, Y_TOP + k), (X0 + r, Y_TOP))


# ---- nets / placement -------------------------------------------------------------
def net(name):
    n = b.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(b, name); b.Add(n)
    return n


NS = uuid.UUID("6f0c5d1e-8b1a-4c55-9d3a-b40a40b40b40")   # same scheme as sch_update.py
fp = {}
for (lib, name, ref, value, pos, rot), f in zip(PARTS, PRELOADED):
    f.SetReference(ref); f.SetValue(value)
    b.Add(f)
    f.SetOrientationDegrees(rot)
    f.SetPosition(VECTOR2I(MM(pos[0]), MM(pos[1])))
    f.SetPath(pcbnew.KIID_PATH("/" + str(uuid.uuid5(NS, ref))))
    fp[ref] = f


def connect(ref, pad, netname):
    hits = [p for p in fp[ref].Pads() if p.GetNumber() == str(pad)]
    assert hits, (ref, pad)
    for p in hits:
        p.SetNet(net(netname))


# PocketBeagle 2 header map (P1.n = pad n, P2.n = pad 36+n).  Verified against
# docs.beagleboard.org/boards/pocketbeagle-2/04-expansion.html pinmux tables (mode 0).
P1, P2 = (lambda n: n), (lambda n: 36 + n)
PB = {
    P1(9): "D-", P1(11): "D+", P1(24): "VBUS",
    P1(15): "GND", P1(16): "GND", P1(22): "GND", P2(15): "GND", P2(21): "GND",
    P2(23): "+3V3",
    # 3-wire SPI for the ST7701S init sequence
    P2(25): "LCD_SDA", P2(29): "LCD_SCK", P2(31): "LCD_CS", P2(10): "LCD_RESET",
    # backlight dimming (P2.01 mode 2 = ECAP2_IN_APWM_OUT)
    P2(1): "BL_PWM",
    # DPI / VOUT0, RGB565 on DATA[15:0]
    P2(17): "LCD_PCLK", P1(29): "LCD_DE", P2(22): "LCD_VSYNC", P2(28): "LCD_HSYNC",
    P2(2): "VOUT_D0", P2(4): "VOUT_D1", P2(6): "VOUT_D2", P2(8): "VOUT_D3",
    P2(20): "VOUT_D4", P1(20): "VOUT_D5", P2(24): "VOUT_D6", P2(33): "VOUT_D7",
    P2(18): "VOUT_D8", P2(35): "VOUT_D9", P1(36): "VOUT_D10", P1(33): "VOUT_D11",
    P2(32): "VOUT_D12", P2(30): "VOUT_D13", P1(31): "VOUT_D14", P2(34): "VOUT_D15",
}
P1N = ["VIN_5V", "GPIO1_10", "USB1_DRVVBUS", "GPIO1_12", "USB1_VBUS", "GPIO1_13", "VIN_USB", "GPIO1_14",
       "USB1_D-", "GPIO1_30", "USB1_D+", "GPIO1_8", "GPIO0_36", "VDD_3V3", "GND", "GND", "AIN_REF-", "AIN_REF+",
       "AIN0", "VOUT0_D5", "AIN1", "GND", "AIN2", "VOUT", "AIN3", "GPIO0_44", "AIN4", "GPIO0_43", "VOUT0_DE",
       "UART0_TXD", "VOUT0_D14", "UART0_RXD", "I2C1_SDA_D11", "GPIO1_2", "GPIO0_88", "I2C1_SCL_D10"]
P2N = ["GPIO1_11_PWM", "VOUT0_D0", "GPIO0_85", "VOUT0_D1", "MCAN0_TX", "VOUT0_D2", "MCAN0_RX", "VOUT0_D3",
       "GPIO1_22", "GPIO0_91", "GPIO1_23", "PWR_BTN", "VOUT_VSYS", "VBAT", "GND", "BAT_TEMP", "VOUT0_PCLK",
       "VOUT0_D8", "GPIO1_0", "VOUT0_D4", "GND", "VOUT0_VSYNC", "VDD_3V3", "VOUT0_D6", "SPI0_D1", "nRESET",
       "SPI0_D0", "VOUT0_HSYNC", "SPI0_CLK", "VOUT0_D13", "SPI0_CS0", "VOUT0_D12", "VOUT0_D7", "VOUT0_D15",
       "VOUT0_D9", "SPI0_CS1"]
PIN_NAMES = {**{n: f"P1.{n:02d}_{P1N[n - 1]}" for n in range(1, 37)},
             **{36 + n: f"P2.{n:02d}_{P2N[n - 1]}" for n in range(1, 37)}}
for p in fp["U2"].Pads():
    n = int(p.GetNumber())
    p.SetNet(net(PB[n] if n in PB else f"unconnected-(U2-{PIN_NAMES[n]}-Pad{n})"))

# J3: panel FPC.  ST7701S 18-bit (MDT=1): DB17..12 = R5..R0, DB11..6 = G5..G0, DB5..0 = B5..B0.
# RGB565 from the AM62: R4..R0 = D15..D11, G5..G0 = D10..D5, B4..B0 = D4..D0; the R0/B0 LSBs are grounded.
DB = {17: "VOUT_D15", 16: "VOUT_D14", 15: "VOUT_D13", 14: "VOUT_D12", 13: "VOUT_D11", 12: "GND",
      11: "VOUT_D10", 10: "VOUT_D9", 9: "VOUT_D8", 8: "VOUT_D7", 7: "VOUT_D6", 6: "VOUT_D5",
      5: "VOUT_D4", 4: "VOUT_D3", 3: "VOUT_D2", 2: "VOUT_D1", 1: "VOUT_D0", 0: "GND"}
J3 = {1: "BL_LEDA", 2: "BL_LEDK", 3: "BL_LEDK", 4: "GND", 5: "+3V3", 6: "LCD_RESET",
      9: "LCD_SDA", 10: "LCD_SCK", 11: "LCD_CS", 12: "LCD_PCLK", 13: "LCD_DE", 14: "LCD_VSYNC",
      15: "LCD_HSYNC", 34: "GND", 40: "GND"}
J3.update({16 + i: DB[i] for i in range(18)})
J3_NC = {7: "NC", 8: "NC", 35: "TP_INT", 36: "TP_SDA", 37: "TP_SCL", 38: "TP_RESET", 39: "TP_VCI"}
for n in range(1, 41):
    connect("J3", n, J3[n] if n in J3 else f"unconnected-(J3-{J3_NC[n]}-Pad{n})")
connect("J3", "MP", "GND")

# backlight: TPS61165 boost, 2 strings x 4 white LEDs, 11.2-13.2 V, 40 mA -> Rsense = 0.2 V / 40 mA
for pad, n in {1: "VBUS", 2: "BL_PWM", 3: "BL_SW", 4: "GND", 5: "BL_COMP", 6: "BL_LEDK"}.items():
    connect("U3", pad, n)
connect("L1", 1, "VBUS"); connect("L1", 2, "BL_SW")
connect("D41", 2, "BL_SW"); connect("D41", 1, "BL_LEDA")        # SOD-123: pad 1 = cathode
connect("C8", 1, "VBUS"); connect("C8", 2, "GND")
connect("C9", 1, "BL_LEDA"); connect("C9", 2, "GND")
connect("C10", 1, "BL_COMP"); connect("C10", 2, "GND")
connect("R7", 1, "BL_LEDK"); connect("R7", 2, "GND")
connect("R8", 1, "BL_PWM"); connect("R8", 2, "GND")

b.BuildConnectivity()
pcbnew.SaveBoard(DST, b)
for ref in ("U2", "J3", "U3"):
    bb = fp[ref].GetBoundingBox(False)
    print(ref, [round(pcbnew.ToMM(v), 2) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())])
for n in (1, 2, 40):
    p = [q for q in fp["J3"].Pads() if q.GetNumber() == str(n)][0]
    print("J3 pad", n, p.GetNetname(), round(pcbnew.ToMM(p.GetPosition().x), 2), round(pcbnew.ToMM(p.GetPosition().y), 2))
