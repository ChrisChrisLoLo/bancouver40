"""Build the Zine Machine v0 (bancouver40 + PocketBeagle 2) BOM (with order links) from the KiCad project.

  python3 tools/pocketbeagle2/make_bom.py

Writes bom/ : BOM.csv (everything, with links), BOM.md, jlcpcb_bom.csv + jlcpcb_cpl.csv (PCBA upload),
and the BOM table in site/index.html (between <!--BOM--> markers).
Links and prices were checked on 2026-11-05 (LCSC product pages / API, JLCPCB parts search, DigiKey, Mouser,
vendor stores). Prices move; re-check before ordering.
"""
import csv, html, io, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
PCB = os.path.join(ROOT, "pcb/bancouver40_pb2")
OUT = os.path.join(ROOT, "bom")
LC = lambda c: f"https://www.lcsc.com/product-detail/{c}.html"

# ---- PCB assembly parts (JLCPCB/LCSC).  refs must cover every SMD/THT part in the KiCad BOM.
PCBA = [
    # refs, value, footprint, MPN, LCSC, unit $, note
    ("U1", "ATmega32U4", "QFN-44 7x7", "Microchip ATMEGA32U4-MU", "C112161", None, "original bancouver40"),
    ("Y1", "16 MHz", "3225-4P", "YXC X322516MLB4SI", "C13738", None, "original"),
    ("C1,C2", "22 pF", "0402", "Yageo CC0402JRNPO9BN220", "C106203", None, "original"),
    ("C3", "1 µF", "0402", "Samsung CL05A105KP5NNNC", "C14445", None, "original"),
    ("C4,C5,C6", "100 nF", "0402", "Yageo CC0402KRX5R6BB104", "C129131", None, "original"),
    ("C7", "10 µF", "0402", "Samsung CL05A106MQ5NUNC", "C15525", None, "original"),
    ("R1,R6", "10 k", "0402", "Yageo AC0402FR-0710KL", "C144807", None, "original"),
    ("R4,R5", "22 Ω", "0402", "Yageo RC0402FR-0722RL", "C114765", None, "original (USB series)"),
    ("F1", "500 mA PTC", "1206", "Littelfuse 1206L050YR", "C163512", None, "original"),
    ("B1", "Reset switch", "SKQG", "ALPS SKQGAKE010", "C127478", None, "original"),
    (",".join(f"D{i}" for i in range(1, 41)), "1N4148WS", "SOD-323", "MDD 1N4148WS", "C437156", None, "original (matrix diodes)"),
    ("U3", "TPS61165", "SOT-23-6", "TI TPS61165DBVR", "C58756", 0.76, "backlight boost"),
    ("L1", "22 µH", "4x4 (SRN4018 pads)", "Taiyo Yuden NRS4018T220MDGJ", "C304460", 0.15,
     "Bourns SRN4018-220M is the drawn part (0 LCSC stock); NRS4018 pads fit the footprint"),
    ("D41", "MBR0540", "SOD-123", "onsemi MBR0540T1G", "C21353", 0.058, "alt JSCJ MBR0540 C77337"),
    ("C8", "4.7 µF 25 V X5R", "0805", "Samsung CL21A475KAQNNNE", "C1779", 0.035, "JLC basic"),
    ("C9", "1 µF 50 V X7R", "0805", "Samsung CL21B105KBFNNNE", "C28323", 0.042, "JLC basic"),
    ("C10", "220 nF 25 V X7R", "0603", "Samsung CL10B224KA8NNNC", "C21120", 0.009, "JLC basic"),
    ("R7", "5.1 Ω 1%", "0603", "UNI-ROYAL 0603WAF510KT5E", "C25197", 0.0036, "sets backlight current 39 mA"),
    ("R8", "100 k 1%", "0603", "UNI-ROYAL 0603WAF1003T5E", "C25803", 0.003, "CTRL pull-down"),
    ("J3", "40p 0.5 mm FPC, top contact", "F32Q", "Amphenol F32Q-1A7H1-11040", "C3168061", 0.99,
     "bottom-contact twin F32R-1A7H1-11040 (same footprint) from DigiKey/Mouser if your panel tail needs it"),
]
LINK2 = {
    "C58756": "https://www.digikey.com/en/products/detail/texas-instruments/TPS61165DBVR/2340764",
    "C304460": "https://www.digikey.com/en/products/detail/bourns-inc/SRN4018-220M/3821626",
    "C21353": "https://www.digikey.com/en/products/detail/onsemi/MBR0540T1G/918576",
    "C3168061": "https://www.digikey.com/en/products/detail/amphenol-cs-fci/F32Q-1A7H1-11040/11564739",
}

# ---- everything else
OTHER = [
    # section, item, qty, MPN/spec, link1, link2, unit price note
    ("Compute", "PocketBeagle 2 (AM6254, ships as Rev A1)", 1, "BeagleBoard 102110780",
     "https://www.digikey.com/en/products/detail/beagleboard-by-seeed-studio/102110780/25927193",
     "https://www.mouser.com/ProductDetail/BeagleBoard-by-Seeed-Studio/102110780?qs=%252BXxaIXUDbq3pDS5bF5qfpw%3D%3D",
     "$39.53 (DigiKey)"),
    ("Compute", "2x18 male header 2.54 mm, straight THT (PB2 plugs onto these)", 2, "HC-PZ254-11.5L-2x18PZ · LCSC C41376109",
     LC("C41376109"), LC("C2894979"), "$0.20"),
    ("Display", "4.58\" 320x960 IPS bar TFT, ST7701S, 40p FPC — choose \"No Touch Panel\"", 1, "BuyDisplay ER-TFT4.58-1",
     "https://www.buydisplay.com/bar-type-4-58-inch-320x960-ips-tft-lcd-display-spi-rgb-interface",
     "https://www.adafruit.com/product/5805", "$14.33 (BuyDisplay)"),
    ("Keyboard", "Kailh Choc v1 low-profile switches (PG1350)", 40, "Kailh CPG1350",
     "https://splitkb.com/products/kailh-low-profile-choc-switches",
     "https://www.chosfox.com/products/kailh-chocs", "~$5 / 10"),
    ("Keyboard", "Kailh Choc hot-swap sockets (hand-solder)", 40, "Kailh CPG135001S30",
     "https://splitkb.com/products/kailh-hotswap-sockets",
     "https://www.chosfox.com/products/kailh-choc-switch-1350-hot-swap-sockets", "$6.57 / 50"),
    ("Keyboard", "Chosfox CFX keycaps 16.5 x 16.5 mm (not \"CFX Puls\"), 1U x10 packs", 40, "Chocfox CFX 1U",
     "https://www.chosfox.com/products/chocfox-cfx-choc-keycaps",
     "https://www.chosfox.com/collections/cfx-keycaps", "$3.50 / 10"),
    ("Hardware", "M2 x 15 mm F-F brass hex standoff", 3, "Würth 970150244",
     "https://uk.farnell.com/wurth-elektronik/970150244/standoff-brass-hex-f-f-m2-15mm/dp/3757947",
     "https://www.mouser.com/c/?q=970150244", "stock unverified — an M2 standoff kit works"),
    ("Hardware", "M2 x 4 flat-head screws (PCB to keyboard bosses)", 6, "Essentra 50M020040H004",
     "https://www.mouser.com/c/?q=50M020040H004", "", "$0.15"),
    ("Hardware", "M2 x 4-5 button/pan-head screws (standoffs: 3 below, 3 through bezel)", 6, "any M2 x 4-5",
     "", "", "not verified — use an M2 kit"),
    ("Hardware", "Rubber bumpons 7.9 mm", 4, "3M SJ5302",
     "https://www.digikey.com/en/products/detail/3m/SJ5302/2345107", "https://www.mouser.com/c/?q=SJ5302",
     "DigiKey min. 144; Mouser from $0.10"),
    ("Hardware", "Thin double-sided tape to glue the panel (optional)", 1, "3M 9495LE ½\" x 5 yd",
     "https://www.digikey.com/en/products/detail/3m-tc/9495LE-0-5-5/2649291", "", "$11.28"),
    ("Fabrication", "PCB + assembly (upload fab/ gerbers + bom/jlcpcb_*.csv)", 1, "2-layer, 170 x 116 mm",
     "https://jlcpcb.com/quote", "https://jlcpcb.com/parts", ""),
    ("Fabrication", "Case + bezel print (translucent resin)", 1, "case/pocketbeagle2/*.stl",
     "https://jlc3dp.com/3d-printing-quote", "https://jlc3dp.com/", ""),
]


def kicad_refs():
    rows = list(csv.DictReader(open(os.path.join(PCB, "fab/bancouver40_pb2-bom.csv"))))
    refs = set()
    for r in rows:
        refs.update(x.strip() for x in r["Refs"].split(","))
    return refs


def main():
    os.makedirs(OUT, exist_ok=True)
    # coverage check: every KiCad ref is either assembled, hand-fit, or mechanical
    have = {x for r in PCBA for x in r[0].split(",")}
    hand = {"U2"} | {f"SW{i}" for i in range(1, 41)} | {f"H{i}" for i in range(1, 15)}
    missing = sorted(kicad_refs() - have - hand, key=lambda s: (re.sub(r"\d", "", s), int(re.sub(r"\D", "", s) or 0)))
    assert not missing, f"refs not in BOM: {missing}"

    # full BOM
    with open(os.path.join(OUT, "BOM.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Section", "Refs", "Qty", "Item", "Value/Spec", "MPN", "LCSC", "Order link", "Alt link", "Unit price (2026-11-05)", "Notes"])
        for refs, val, fp, mpn, lcsc, price, note in PCBA:
            n = len(refs.split(","))
            w.writerow(["PCB assembly", refs, n, f"{val} {fp}", val, mpn, lcsc, LC(lcsc), LINK2.get(lcsc, ""),
                        f"${price}" if price else "", note])
        for sec, item, qty, mpn, l1, l2, price in OTHER:
            w.writerow([sec, "", qty, item, "", mpn, "", l1, l2, price, ""])

    # JLCPCB BOM + CPL (KiCad pos -> JLC columns)
    with open(os.path.join(OUT, "jlcpcb_bom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for refs, val, fp, mpn, lcsc, *_ in PCBA:
            w.writerow([val, refs, fp, lcsc])
    pos = list(csv.DictReader(open(os.path.join(PCB, "fab/bancouver40_pb2-pos.csv"))))
    with open(os.path.join(OUT, "jlcpcb_cpl.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for p in pos:
            if p["Ref"] in have:
                w.writerow([p["Ref"], f'{float(p["PosX"]):.4f}mm', f'{float(p["PosY"]):.4f}mm',
                            "Top" if p["Side"].lower().startswith("top") else "Bottom", p["Rot"]])

    # markdown
    md = io.StringIO()
    md.write("# Zine Machine v0 — bill of materials\n\nLinks and prices checked 2026-11-05; re-check before ordering.\n"
             "PCB assembly parts are LCSC numbers for JLCPCB (`jlcpcb_bom.csv` + `jlcpcb_cpl.csv`); "
             "check part rotations in JLC's preview.\n\n## PCB assembly\n\n| Refs | Qty | Part | MPN | LCSC | Price | Notes |\n|---|---|---|---|---|---|---|\n")
    for refs, val, fp, mpn, lcsc, price, note in PCBA:
        n = len(refs.split(","))
        shown = refs if n <= 6 else f"{refs.split(',')[0]}–{refs.split(',')[-1]}"
        alt = f" · [alt]({LINK2[lcsc]})" if lcsc in LINK2 else ""
        md.write(f"| {shown} | {n} | {val} {fp} | {mpn} | [{lcsc}]({LC(lcsc)}){alt} | {f'${price}' if price else ''} | {note} |\n")
    md.write("\n## Everything else\n\n| Section | Qty | Item | Part | Order | Price |\n|---|---|---|---|---|---|\n")
    for sec, item, qty, mpn, l1, l2, price in OTHER:
        links = " · ".join(f"[{t}]({u})" for t, u in (("order", l1), ("alt", l2)) if u) or "—"
        md.write(f"| {sec} | {qty} | {item} | {mpn} | {links} | {price} |\n")
    md.write("\n### Notes\n"
             "- The panel pinout was taken from the 4.58\" 320x960 ST7701S datasheet (Maxen MX-046HS40FS-N01 drawing, same outline as "
             "ER-TFT4.58-1). Check the pin table of the panel you actually receive before ordering the PCB; the Adafruit 5805 "
             "alternative has not been compared.\n"
             "- J3: F32Q is top contact (assumed: contacts face up after the 180° fold). Fit the F32R twin if your tail's contacts "
             "are on the other side.\n"
             "- The keyboard's original parts keep the LCSC numbers the bancouver40 author used.\n")
    open(os.path.join(OUT, "BOM.md"), "w").write(md.getvalue())

    # site table
    rows = []
    for refs, val, fp, mpn, lcsc, price, note in PCBA:
        n = len(refs.split(","))
        shown = refs if n <= 6 else f"{refs.split(',')[0]}–{refs.split(',')[-1]}"
        rows.append((shown, n, f"{val} {fp}", mpn, [(lcsc, LC(lcsc))] + ([("alt", LINK2[lcsc])] if lcsc in LINK2 else []),
                     f"${price}" if price else ""))
    for sec, item, qty, mpn, l1, l2, price in OTHER:
        rows.append((sec, qty, item, mpn, [(t, u) for t, u in (("order", l1), ("alt", l2)) if u], price))
    e = html.escape
    body = "\n".join(
        f"<tr><td>{e(str(a))}</td><td>{q}</td><td>{e(it)}</td><td>{e(m)}</td><td>"
        + " · ".join(f'<a href="{e(u)}" target="_blank" rel="noopener">{e(t)}</a>' for t, u in links)
        + f"</td><td>{e(p)}</td></tr>" for a, q, it, m, links, p in rows)
    table = ('<table class="bomt"><thead><tr><th>Refs / group</th><th>Qty</th><th>Part</th><th>MPN</th><th>Order</th>'
             f'<th>Price</th></tr></thead><tbody>\n{body}\n</tbody></table>')
    idx = os.path.join(ROOT, "site/index.html")
    s = open(idx).read()
    s = re.sub(r"<!--BOM-->.*?<!--/BOM-->", "<!--BOM-->\n" + table + "\n<!--/BOM-->", s, flags=re.S)
    open(idx, "w").write(s)
    print(f"{len(PCBA)} assembly lines ({sum(len(r[0].split(',')) for r in PCBA)} placements), {len(OTHER)} other lines; "
          f"CPL rows {sum(1 for p in pos if p['Ref'] in have)}")


main()
