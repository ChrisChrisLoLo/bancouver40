# Zine Machine v0 — bill of materials

Links and prices checked 2026-11-05; re-check before ordering.
PCB assembly parts are LCSC numbers for JLCPCB (`jlcpcb_bom.csv` + `jlcpcb_cpl.csv`); check part rotations in JLC's preview.

## PCB assembly

| Refs | Qty | Part | MPN | LCSC | Price | Notes |
|---|---|---|---|---|---|---|
| U1 | 1 | ATmega32U4 QFN-44 7x7 | Microchip ATMEGA32U4-MU | [C112161](https://www.lcsc.com/product-detail/C112161.html) |  | original bancouver40 |
| Y1 | 1 | 16 MHz 3225-4P | YXC X322516MLB4SI | [C13738](https://www.lcsc.com/product-detail/C13738.html) |  | original |
| C1,C2 | 2 | 22 pF 0402 | Yageo CC0402JRNPO9BN220 | [C106203](https://www.lcsc.com/product-detail/C106203.html) |  | original |
| C3 | 1 | 1 µF 0402 | Samsung CL05A105KP5NNNC | [C14445](https://www.lcsc.com/product-detail/C14445.html) |  | original |
| C4,C5,C6 | 3 | 100 nF 0402 | Yageo CC0402KRX5R6BB104 | [C129131](https://www.lcsc.com/product-detail/C129131.html) |  | original |
| C7 | 1 | 10 µF 0402 | Samsung CL05A106MQ5NUNC | [C15525](https://www.lcsc.com/product-detail/C15525.html) |  | original |
| R1,R6 | 2 | 10 k 0402 | Yageo AC0402FR-0710KL | [C144807](https://www.lcsc.com/product-detail/C144807.html) |  | original |
| R4,R5 | 2 | 22 Ω 0402 | Yageo RC0402FR-0722RL | [C114765](https://www.lcsc.com/product-detail/C114765.html) |  | original (USB series) |
| F1 | 1 | 500 mA PTC 1206 | Littelfuse 1206L050YR | [C163512](https://www.lcsc.com/product-detail/C163512.html) |  | original |
| B1 | 1 | Reset switch SKQG | ALPS SKQGAKE010 | [C127478](https://www.lcsc.com/product-detail/C127478.html) |  | original |
| D1–D40 | 40 | 1N4148WS SOD-323 | MDD 1N4148WS | [C437156](https://www.lcsc.com/product-detail/C437156.html) |  | original (matrix diodes) |
| U3 | 1 | TPS61165 SOT-23-6 | TI TPS61165DBVR | [C58756](https://www.lcsc.com/product-detail/C58756.html) · [alt](https://www.digikey.com/en/products/detail/texas-instruments/TPS61165DBVR/2340764) | $0.76 | backlight boost |
| L1 | 1 | 22 µH 4x4 (SRN4018 pads) | Taiyo Yuden NRS4018T220MDGJ | [C304460](https://www.lcsc.com/product-detail/C304460.html) · [alt](https://www.digikey.com/en/products/detail/bourns-inc/SRN4018-220M/3821626) | $0.15 | Bourns SRN4018-220M is the drawn part (0 LCSC stock); NRS4018 pads fit the footprint |
| D41 | 1 | MBR0540 SOD-123 | onsemi MBR0540T1G | [C21353](https://www.lcsc.com/product-detail/C21353.html) · [alt](https://www.digikey.com/en/products/detail/onsemi/MBR0540T1G/918576) | $0.058 | alt JSCJ MBR0540 C77337 |
| C8 | 1 | 4.7 µF 25 V X5R 0805 | Samsung CL21A475KAQNNNE | [C1779](https://www.lcsc.com/product-detail/C1779.html) | $0.035 | JLC basic |
| C9 | 1 | 1 µF 50 V X7R 0805 | Samsung CL21B105KBFNNNE | [C28323](https://www.lcsc.com/product-detail/C28323.html) | $0.042 | JLC basic |
| C10 | 1 | 220 nF 25 V X7R 0603 | Samsung CL10B224KA8NNNC | [C21120](https://www.lcsc.com/product-detail/C21120.html) | $0.009 | JLC basic |
| R7 | 1 | 5.1 Ω 1% 0603 | UNI-ROYAL 0603WAF510KT5E | [C25197](https://www.lcsc.com/product-detail/C25197.html) | $0.0036 | sets backlight current 39 mA |
| R8 | 1 | 100 k 1% 0603 | UNI-ROYAL 0603WAF1003T5E | [C25803](https://www.lcsc.com/product-detail/C25803.html) | $0.003 | CTRL pull-down |
| J3 | 1 | 40p 0.5 mm FPC, top contact F32Q | Amphenol F32Q-1A7H1-11040 | [C3168061](https://www.lcsc.com/product-detail/C3168061.html) · [alt](https://www.digikey.com/en/products/detail/amphenol-cs-fci/F32Q-1A7H1-11040/11564739) | $0.99 | bottom-contact twin F32R-1A7H1-11040 (same footprint) from DigiKey/Mouser if your panel tail needs it |

## Everything else

| Section | Qty | Item | Part | Order | Price |
|---|---|---|---|---|---|
| Compute | 1 | PocketBeagle 2 (AM6254, ships as Rev A1) | BeagleBoard 102110780 | [order](https://www.digikey.com/en/products/detail/beagleboard-by-seeed-studio/102110780/25927193) · [alt](https://www.mouser.com/ProductDetail/BeagleBoard-by-Seeed-Studio/102110780?qs=%252BXxaIXUDbq3pDS5bF5qfpw%3D%3D) | $39.53 (DigiKey) |
| Compute | 2 | 2x18 male header 2.54 mm, straight THT (PB2 plugs onto these) | HC-PZ254-11.5L-2x18PZ · LCSC C41376109 | [order](https://www.lcsc.com/product-detail/C41376109.html) · [alt](https://www.lcsc.com/product-detail/C2894979.html) | $0.20 |
| Display | 1 | 4.58" 320x960 IPS bar TFT, ST7701S, 40p FPC — choose "No Touch Panel" | BuyDisplay ER-TFT4.58-1 | [order](https://www.buydisplay.com/bar-type-4-58-inch-320x960-ips-tft-lcd-display-spi-rgb-interface) · [alt](https://www.adafruit.com/product/5805) | $14.33 (BuyDisplay) |
| Keyboard | 40 | Kailh Choc v1 low-profile switches (PG1350) | Kailh CPG1350 | [order](https://splitkb.com/products/kailh-low-profile-choc-switches) · [alt](https://www.chosfox.com/products/kailh-chocs) | ~$5 / 10 |
| Keyboard | 40 | Kailh Choc hot-swap sockets (hand-solder) | Kailh CPG135001S30 | [order](https://splitkb.com/products/kailh-hotswap-sockets) · [alt](https://www.chosfox.com/products/kailh-choc-switch-1350-hot-swap-sockets) | $6.57 / 50 |
| Keyboard | 40 | Chosfox CFX keycaps 16.5 x 16.5 mm (not "CFX Puls"), 1U x10 packs | Chocfox CFX 1U | [order](https://www.chosfox.com/products/chocfox-cfx-choc-keycaps) · [alt](https://www.chosfox.com/collections/cfx-keycaps) | $3.50 / 10 |
| Hardware | 3 | M2 x 15 mm F-F brass hex standoff | Würth 970150244 | [order](https://uk.farnell.com/wurth-elektronik/970150244/standoff-brass-hex-f-f-m2-15mm/dp/3757947) · [alt](https://www.mouser.com/c/?q=970150244) | stock unverified — an M2 standoff kit works |
| Hardware | 6 | M2 x 4 flat-head screws (PCB to keyboard bosses) | Essentra 50M020040H004 | [order](https://www.mouser.com/c/?q=50M020040H004) | $0.15 |
| Hardware | 6 | M2 x 4-5 button/pan-head screws (standoffs: 3 below, 3 through bezel) | any M2 x 4-5 | — | not verified — use an M2 kit |
| Hardware | 4 | Rubber bumpons 7.9 mm | 3M SJ5302 | [order](https://www.digikey.com/en/products/detail/3m/SJ5302/2345107) · [alt](https://www.mouser.com/c/?q=SJ5302) | DigiKey min. 144; Mouser from $0.10 |
| Hardware | 1 | Thin double-sided tape to glue the panel (optional) | 3M 9495LE ½" x 5 yd | [order](https://www.digikey.com/en/products/detail/3m-tc/9495LE-0-5-5/2649291) | $11.28 |
| Fabrication | 1 | PCB + assembly (upload fab/ gerbers + bom/jlcpcb_*.csv) | 2-layer, 170 x 116 mm | [order](https://jlcpcb.com/quote) · [alt](https://jlcpcb.com/parts) |  |
| Fabrication | 1 | Case + bezel print (translucent resin) | case/pocketbeagle2/*.stl | [order](https://jlc3dp.com/3d-printing-quote) · [alt](https://jlc3dp.com/) |  |

### Notes
- The panel pinout was taken from the 4.58" 320x960 ST7701S datasheet (Maxen MX-046HS40FS-N01 drawing, same outline as ER-TFT4.58-1). Check the pin table of the panel you actually receive before ordering the PCB; the Adafruit 5805 alternative has not been compared.
- J3: F32Q is top contact (assumed: contacts face up after the 180° fold). Fit the F32R twin if your tail's contacts are on the other side.
- The keyboard's original parts keep the LCSC numbers the bancouver40 author used.
