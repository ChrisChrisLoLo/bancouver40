# Zine Machine main board v3: design spec

This board replaces v2 (`bancouver40_pb2`, the 32U4 + hot-swap version). It is the main board of the Zine Machine:
the bancouver40 keyboard + a PocketBeagle 2 **Industrial** + the 4.58" 320x960 bar panel (unchanged), battery powered,
in an open 3D-printed tray. The mechanical layout is fixed by `mech/zine_concept.py` (renders in `mech/renders/`);
positions below come from it.

Coordinates: **KiCad** (mm, y down). Case/tray coordinates convert as `kx = cx + 71.775`, `ky = 85.475 - cy`.

## Rules

- **All assembled (SMD) parts on F.Cu (top).** Through-hole parts are fine (switches, jacks, USB-A, slide switch,
  PocketBeagle header, battery connector) but nothing assembled on the bottom.
- **No hot-swap sockets.** Kailh Choc v1 switches soldered directly (plain Choc v1 footprint, 17 x 17 mm grid).
- 2 layers preferred; 4 layers allowed if routing or USB/audio quality needs it (say why).
- Every BOM line has an MPN in the fab's stock (prefer basic/preferred parts).
- Fab limits: tracks/gaps >= 0.127 mm comfortable (0.10 min), vias 0.3/0.45 mm, copper 0.3 mm from the edge.

## Outline and fixed positions

| Item | KiCad position |
|---|---|
| Board outline | x 74.375..244.375, y -43.125..82.875 (170 x 126 mm), corner radius 1 mm. Was 170 x 116: grows 10 mm to the rear (-y). |
| 40 keyswitches (unchanged grid) | columns x 82.875 + 17*c (c = 0..9), rows y 23.375 / 40.375 / 57.375 / 74.375 (row 0 = Q..P) |
| 3 mode keys (Choc v1) | x 233.375, y -32.725 (red), -15.725 (yellow), 1.275 (blue) |
| PocketBeagle 2 (U2) | board outline x 74.9..109.9, y -43.225..11.775, **USB-C end at the rear** (y = -43.2) so it exits the rear wall. Mounted face-down on its own 3.55 mm SMT female sockets. P1.01 at (78.455, -37.315), P1.02 at (80.995, -37.315), P1 pins run +y (P1.35 at y 5.865); P2.01 at (103.859, -37.315), P2.02 at (106.399, -37.315). Check pads against `case/pocketbeagle2/models/industrial/pocketbeagle2 revA_dimension.pdf`. |
| J3 panel FPC connector | same part, moved 4 mm to -x: body x 202.53..209.28, y -22.88..5.47 |
| Display chassis posts (M2, 4) | (112.575, 9.475), (112.575, -33.025), (219.275, 9.475), (219.275, -33.025) |
| Tray screws, keyboard area (M2, 6, unchanged bosses) | (91.375, 48.875), (125.375, 65.875), (125.375, 31.875), (193.375, 65.875), (193.375, 31.875), (227.375, 48.875) |
| Battery keep-out (no parts, F.Cu) | x 115.175..189.175, y -30.025..9.975 (9 x 40 x 70 LiPo pouch + 4 mm protection board, on a 0.5 mm foam pad) |
| Rear I/O, each at the rear edge (y -43.1), x ranges | power slide switch 115.8..127.8; headset TRRS 130.8..136.8; line-out TRS 139.8..145.8; charge USB-C 149.8..158.8; USB-A1 188.3..201.4; USB-A2 203.4..216.5 |

Height limits: parts under the PocketBeagle (between its sockets) <= 1.5 mm; everything else under the display
chassis (z 17.2 from the tray floor, board top at 6.1) <= 10 mm. Old H11-H13 standoffs go.

## Blocks

### Key scanning on the PocketBeagle's Cortex-M4F
No matrix and no diodes: every key (40 + 3 mode keys) wired **directly** to a chain of **six 74HC165** (48 inputs,
43 used, 5 spare tied high), pull-ups to 3V3 (resistor arrays), key to GND. The M4F reads the chain on its own
MCU-domain pins (Linux never touches them):
- CLK = P1.26 (MCU_GPIO0_13, ball D6), SH/LD = P1.28 (MCU_GPIO0_14, ball B3), QH = P2.05 (MCU_GPIO0_5, ball B5)
- spare MCU pin P2.07 (MCU_GPIO0_6) to a test pad
- the main-domain balls shorted to those header pins (GPIO0_44, GPIO0_43, GPIO1_24) stay unmuxed inputs in Linux.
Place the 165s where the routing works (top side); the bottom layer is free for the key traces.

### Display (unchanged except PWM)
Same RGB565 DPI + 3-wire SPI wiring as v2 (`README.md` table), same TPS61165 backlight boost.
**Backlight PWM moves from P2.01 to P1.06** (EHRPWM0_A) because P2.01 becomes I2S BCLK.

### USB hub and rear USB-A
FE1.1s (SSOP-28, 12 MHz crystal) upstream on USB1: D-/D+ = P1.09/P1.11. Check the PocketBeagle schematic (sheet with
USB1) for how USB1_VBUS (P1.05) and USB1_DRVVBUS (P1.03) must be handled for host mode. Ports 1-2 to the two
rear USB-A receptacles through current-limited power switches (~0.5-1 A each, fault flag to the hub) and USB ESD
protection; ports 3-4 unused.

### Power
- **Charge input:** rear USB-C receptacle (power only, CC1/CC2 5.1k to GND) -> IP5306-I2C VIN.
- **IP5306-I2C** (ESOP-8): 1S LiPo on a 2-pin JST-PH, 5 V boost out. Charges at up to 2.1 A.
- **Power switch:** a chunky, finger-friendly slide switch on the rear wall. OFF must drop the system rail while
  charging keeps working; ON must reliably wake the IP5306's boost (it sleeps with no load: pulse its KEY pin or
  similar). Use a load switch / P-FET for the current, not the slide switch contacts.
- **+5V_SYS** feeds: PocketBeagle VIN_5V (P1.01), hub, USB-A switches, backlight boost, codec LDO.
- **3V3 logic** (165 chain, pull-ups, LEDs) from the PocketBeagle's VDD_3V3 (P1.14/P2.23).
- **Status LEDs:** charge LED from the IP5306's LED outputs (charging / full), boot LED on P1.35 (GPIO0_88). Place
  both where they show (rear-right of the display or near the mode keys).

### Audio
**ES8388** codec as **I2S master**, clocked by its own 12.288 MHz oscillator on MCLK; the McASP is the slave.
- BCLK = P2.01 (MCASP0_ACLKX), LRCK = P1.04 (MCASP0_AFSX)
- codec DSDIN <- P2.03 (MCASP0_AXR1, ball B18 via P2.03A), codec ASDOUT -> P1.12 (MCASP0_AXR2)
- low-noise 3.3 V LDO from +5V_SYS for AVDD
- LOUT1/ROUT1 -> **headset TRRS jack** (CTIA: tip L, ring1 R, ring2 GND, sleeve mic) through coupling caps; mic in
  with MICBIAS; jack-detect switch -> P1.08 (GPIO1_14)
- LOUT2/ROUT2 -> **line-out TRS jack** through coupling caps
- Check the AIN pins (P1.02, P1.19-P1.27, P2.35, P2.36) carry ADC filtering on the PocketBeagle; none are used for audio.

### I2C
I2C3 on P2.09 (SCL) / P2.11 (SDA), 2.2k pull-ups to 3V3: IP5306-I2C (0x75) + ES8388 (0x10).
Their MCU-domain twin balls (MCU_GPIO0_16/15) are then not used.

### Removed from v2
ATmega32U4 (U1) with its crystal, reset button, caps; 40 diodes; 40 hot-swap sockets; F1/VBUS-from-USB1 keyboard
power; H11-H13.

## Header pin map (PocketBeagle 2)

| Pin | Use | | Pin | Use |
|---|---|---|---|---|
| P1.01 | +5V_SYS in | | P2.01 | I2S BCLK |
| P1.04 | I2S LRCK | | P2.03 | I2S data to codec |
| P1.06 | backlight PWM | | P2.05 | M4F keys QH |
| P1.08 | headset detect | | P2.07 | M4F spare (test pad) |
| P1.09 / P1.11 | USB1 D- / D+ to hub | | P2.09 / P2.11 | I2C3 SCL / SDA |
| P1.12 | I2S data from codec | | P2.10 | panel RESET (unchanged) |
| P1.14, P2.23 | 3V3 out | | P2.25/29/31 | panel SPI (unchanged) |
| P1.26 / P1.28 | M4F keys CLK / SH-LD | | display RGB + sync | unchanged (v2 README) |
| P1.35 | boot LED | | GND | all GND pins |

Spare: P1.02, P1.03, P1.10, P1.13, P1.19, P1.21, P1.23, P1.25, P1.27, P1.30, P1.32, P1.34, P2.19, P2.27, P2.36.

## Done means
1. Schematic complete, ERC clean (or every remaining item explained), BOM with MPNs in the fab's stock.
2. Placement matches the positions above; placement DRC clean; a STEP of the board fits `mech/zine_concept`.
3. Fully routed, DRC clean, GND pour, USB pairs at 90 ohm differential where practical.
4. Fab outputs, `bancouver40_pb2.fab.json` with measured `width_mm`, `height_mm`, `min_drill_mm`; README updated.
