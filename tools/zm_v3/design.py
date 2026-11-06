"""Zine Machine main board v3 (bancouver40_pb2): the whole circuit as data.

Each part: ref, kind (symbol), value, footprint, mpn, lcsc, pins {pin number: net}, block.
Custom symbols are boxes built from SYMS (pin number, name, side, electrical type).
Nets starting with '+' or equal to GND are power nets (drawn with power symbols).
"""

FP_R = 'Resistor_SMD:R_0402_1005Metric'
FP_C = 'Capacitor_SMD:C_0402_1005Metric'
FP_C0603 = 'Capacitor_SMD:C_0603_1608Metric'
FP_C0805 = 'Capacitor_SMD:C_0805_2012Metric'
FP_C1206 = 'Capacitor_SMD:C_1206_3216Metric'
FP_R0603 = 'Resistor_SMD:R_0603_1608Metric'
FP_LED = 'LED_SMD:LED_0603_1608Metric'

# ---------------- passive catalogue: value -> (footprint, mpn, lcsc) ----------------
# filled/checked against the fab's stock (see BOM step); basic parts where they exist
PASSIVE = {
    # resistors 0402
    ('R', '33R'): (FP_R, '0402WGF330JTCE', 'C25105'),
    ('R', '1k'): (FP_R, '0402WGF1001TCE', 'C11702'),
    ('R', '2.2k'): (FP_R, '0402WGF2201TCE', 'C25879'),
    ('R', '2.7k 1%'): (FP_R0603, '0603WAF2701T5E', 'C13167'),
    ('R', '5.1k'): (FP_R, '0402WGF5101TCE', 'C25905'),
    ('R', '10k'): (FP_R, '0402WGF1002TCE', 'C25744'),
    ('R', '47k'): (FP_R, '0402WGF4702TCE', 'C25792'),
    ('R', '100k'): (FP_R, '0402WGF1003TCE', 'C25741'),
    ('R', '470k'): (FP_R, '0402WGF4703TCE', 'C25790'),
    ('R', '1M'): (FP_R, '0402WGF1004TCE', 'C26083'),
    ('R', '2R'): (FP_R0603, '0603WAF200KT5E', 'C22977'),
    ('R', '0.5R'): (FP_R0603, 'FRL0603JR500TS', 'C2930046'),
    ('R', '5.1R 1%'): (FP_R0603, '0603WAF510KT5E', 'C25197'),
    # capacitors
    ('C', '10nF'): (FP_C, 'CL05B103KB5NNNC', 'C15195'),
    ('C', '100nF'): (FP_C, 'CL05B104KO5NNNC', 'C1525'),
    ('C', '1uF'): (FP_C, 'CL05A105KA5NQNC', 'C52923'),
    ('C', '220nF'): (FP_C0603, 'CL10B224KA8NNNC', 'C21120'),
    ('C', '10uF'): (FP_C0603, 'CL10A106KP8NNNC', 'C19702'),
    ('C', '22uF'): (FP_C0805, 'CL21A226MAQNNNE', 'C45783'),
    ('C', '4.7uF 25V'): (FP_C0805, 'CL21A475KAQNNNE', 'C1779'),
    ('C', '1uF 50V'): (FP_C0805, 'CL21B105KBFNNNE', 'C28323'),
    ('C', '100uF'): (FP_C1206, 'CL31A107MQHNNNE', 'C15008'),
}

SYMS = {}      # custom box symbols: name -> list of (num, name, side, type)
PARTS = []

def part(ref, kind, value, pins, block, fp=None, mpn=None, lcsc=None, **kw):
    if kind in ('R', 'C') and fp is None:
        fp, mpn, lcsc = PASSIVE[(kind, value)]
    d = dict(ref=ref, kind=kind, value=value, pins={str(k): v for k, v in pins.items()}, block=block,
             fp=fp, mpn=mpn, lcsc=lcsc)
    d.update(kw)
    PARTS.append(d)
    return d

def R(ref, value, a, b, block):
    return part(ref, 'R', value, {1: a, 2: b}, block)

def C(ref, value, a, b, block):
    return part(ref, 'C', value, {1: a, 2: b}, block)

# ======================================================================================
# PocketBeagle 2 (U2): P1.n = pad n, P2.n = pad 36+n (Module:BeagleBoard_PocketBeagle)
# ======================================================================================
P1 = {1: ('VIN_5V', '+5V_SYS', 'power_in'), 2: ('AIN6/GPIO1_10', None, 'bidirectional'),
      3: ('USB1_DRVVBUS', None, 'bidirectional'), 4: ('MCASP0_AFSX', 'I2S_LRCK', 'bidirectional'),
      5: ('USB1_VBUS', '+5V_SYS', 'input'), 6: ('EHRPWM0_A', 'BL_PWM', 'bidirectional'),
      7: ('VIN_USB', None, 'passive'), 8: ('GPIO1_14', 'HP_DET', 'bidirectional'),
      9: ('USB1_D-', 'USB_UP_N', 'bidirectional'), 10: ('GPIO1_30', None, 'bidirectional'),
      11: ('USB1_D+', 'USB_UP_P', 'bidirectional'), 12: ('MCASP0_AXR2', 'I2S_ADC', 'bidirectional'),
      13: ('GPIO0_36', None, 'bidirectional'), 14: ('VDD_3V3', '+3V3', 'power_out'),
      15: ('GND', 'GND', 'power_in'), 16: ('GND', 'GND', 'power_in'), 17: ('AIN_VREF-', None, 'passive'),
      18: ('AIN_VREF+', None, 'passive'), 19: ('AIN0', 'VBAT_SENSE', 'input'),
      20: ('VOUT0_D5', 'VOUT_D5', 'bidirectional'), 21: ('AIN1', None, 'input'), 22: ('GND', 'GND', 'power_in'),
      23: ('AIN2', None, 'input'), 24: ('VOUT_VSYS', None, 'passive'), 25: ('AIN3', None, 'input'),
      26: ('MCU_GPIO0_13', 'KEY_CLK_PB', 'bidirectional'), 27: ('AIN4', None, 'input'),
      28: ('MCU_GPIO0_14', 'KEY_SHLD_PB', 'bidirectional'), 29: ('VOUT0_DE', 'LCD_DE', 'bidirectional'),
      30: ('UART0_TXD', None, 'bidirectional'), 31: ('VOUT0_D14', 'VOUT_D14', 'bidirectional'),
      32: ('UART0_RXD', None, 'bidirectional'), 33: ('VOUT0_D11', 'VOUT_D11', 'bidirectional'),
      34: ('GPIO0_26', None, 'bidirectional'), 35: ('GPIO0_88', 'LED_BOOT', 'bidirectional'),
      36: ('VOUT0_D10', 'VOUT_D10', 'bidirectional')}
P2 = {1: ('MCASP0_ACLKX', 'I2S_BCLK', 'bidirectional'), 2: ('VOUT0_D0', 'VOUT_D0', 'bidirectional'),
      3: ('MCASP0_AXR1', 'I2S_DAC', 'bidirectional'), 4: ('VOUT0_D1', 'VOUT_D1', 'bidirectional'),
      5: ('MCU_GPIO0_5', 'KEY_QH', 'bidirectional'), 6: ('VOUT0_D2', 'VOUT_D2', 'bidirectional'),
      7: ('MCU_GPIO0_6', 'M4F_SPARE', 'bidirectional'), 8: ('VOUT0_D3', 'VOUT_D3', 'bidirectional'),
      9: ('I2C3_SCL', 'I2C_SCL', 'bidirectional'), 10: ('GPIO0_91', 'LCD_RESET', 'bidirectional'),
      11: ('I2C3_SDA', 'I2C_SDA', 'bidirectional'), 12: ('PWR_BTN', None, 'passive'),
      13: ('VOUT_VSYS', None, 'passive'), 14: ('BAT_VIN', None, 'passive'), 15: ('GND', 'GND', 'power_in'),
      16: ('BAT_TEMP', None, 'passive'), 17: ('VOUT0_PCLK', 'LCD_PCLK', 'bidirectional'),
      18: ('VOUT0_D8', 'VOUT_D8', 'bidirectional'), 19: ('GPIO0_27', None, 'bidirectional'),
      20: ('VOUT0_D4', 'VOUT_D4', 'bidirectional'), 21: ('GND', 'GND', 'power_in'),
      22: ('VOUT0_VSYNC', 'LCD_VSYNC', 'bidirectional'), 23: ('VDD_3V3', '+3V3', 'passive'),
      24: ('VOUT0_D6', 'VOUT_D6', 'bidirectional'), 25: ('SPI0_D1', 'LCD_SDA', 'bidirectional'),
      26: ('nRESET', None, 'passive'), 27: ('SPI0_D0', None, 'bidirectional'),
      28: ('VOUT0_HSYNC', 'LCD_HSYNC', 'bidirectional'), 29: ('SPI0_CLK', 'LCD_SCK', 'bidirectional'),
      30: ('VOUT0_D13', 'VOUT_D13', 'bidirectional'), 31: ('SPI0_CS0', 'LCD_CS', 'bidirectional'),
      32: ('VOUT0_D12', 'VOUT_D12', 'bidirectional'), 33: ('VOUT0_D7', 'VOUT_D7', 'bidirectional'),
      34: ('VOUT0_D15', 'VOUT_D15', 'bidirectional'), 35: ('VOUT0_D9', 'VOUT_D9', 'bidirectional'),
      36: ('AIN7', None, 'input')}
SYMS['PocketBeagle2'] = ([(n, 'P1.%02d %s' % (n, P1[n][0]), 'L', P1[n][2]) for n in range(1, 37)] +
                         [(36 + n, 'P2.%02d %s' % (n, P2[n][0]), 'R', P2[n][2]) for n in range(1, 37)])
pb_pins = {n: P1[n][1] for n in P1}
pb_pins.update({36 + n: P2[n][1] for n in P2})
part('U2', 'PocketBeagle2', 'PocketBeagle 2 Industrial', pb_pins, 'pb2',
     fp='zm_v3:PocketBeagle2_FaceDown', mpn='100003007 (BeagleBoard PocketBeagle 2 Industrial)', lcsc=None,
     dnp_bom=True, note='Plugs in on its own 3.55 mm SMT sockets; carrier gets 2x 2x18 male headers (hand-fit).')

# ======================================================================================
# Key scanning: 43 Choc v1 keys -> six 74HC165, pull-ups to +3V3, key to GND
# ======================================================================================
SYMS['74HC165'] = [(1, 'SH/~{LD}', 'L', 'input'), (2, 'CLK', 'L', 'input'),
                   (10, 'SER', 'L', 'input'), (11, 'A', 'L', 'input'), (12, 'B', 'L', 'input'),
                   (13, 'C', 'L', 'input'), (14, 'D', 'L', 'input'), (3, 'E', 'L', 'input'),
                   (4, 'F', 'L', 'input'), (5, 'G', 'L', 'input'), (6, 'H', 'L', 'input'),
                   (15, 'CLK_INH', 'L', 'input'), (16, 'VCC', 'T', 'power_in'), (8, 'GND', 'B', 'power_in'),
                   (9, 'QH', 'R', 'output'), (7, '~{QH}', 'R', 'output')]
SYMS['ChocV1'] = [(1, '1', 'L', 'passive'), (2, '2', 'R', 'passive')]
SYMS['RN4'] = [(1, 'R1.1', 'L', 'passive'), (2, 'R2.1', 'L', 'passive'), (3, 'R3.1', 'L', 'passive'),
               (4, 'R4.1', 'L', 'passive'), (8, 'R1.2', 'R', 'passive'), (7, 'R2.2', 'R', 'passive'),
               (6, 'R3.2', 'R', 'passive'), (5, 'R4.2', 'R', 'passive')]

KEY_X = [82.875 + 17 * c for c in range(10)]
KEY_Y = [23.375, 40.375, 57.375, 74.375]
LEGEND = ['QWERTYUIOP', 'ASDFGHJKL;', 'ZXCVBNM,./', ['Esc', 'GUI', 'Ctl', 'Tab', 'Spc', 'L1', 'Bsp', 'Sft', 'Alt', 'Ent']]
keys = []          # (ref, net, x, y)
for r in range(4):
    for c in range(10):
        n = r * 10 + c + 1
        keys.append(('SW%d' % n, 'K%d%d' % (r, c), KEY_X[c], KEY_Y[r]))
MODE = [('SW41', 'K_RED', 233.375, -32.725), ('SW42', 'K_YEL', 233.375, -15.725), ('SW43', 'K_BLU', 233.375, 1.275)]
keys += MODE
for ref, net, x, y in keys:
    part(ref, 'ChocV1', 'Choc_v1', {1: net, 2: 'GND'}, 'keys', fp='zm_v3:SW_Kailh_Choc_V1_Plain',
         mpn='CPG135001D01 (Kailh Choc v1, hand-soldered)', lcsc=None, dnp_bom=True, pos=(x, y))

# shift chain: QH of U10 -> P2.05; U10.SER <- U11.QH ... U15.SER <- GND
CHAIN = ['U10', 'U11', 'U12', 'U13', 'U14', 'U15']
INPUTS = {   # chip -> nets on A..H (None = spare, pulled up by its array resistor)
    'U10': ['K00', 'K10', 'K20', 'K30', 'K01', 'K11', 'K21', 'K31'],
    'U11': ['K02', 'K12', 'K22', 'K32', 'K03', 'K13', 'K23', 'K33'],
    'U12': ['K04', 'K14', 'K24', 'K34', None, None, None, None],
    'U13': ['K05', 'K15', 'K25', 'K35', 'K06', 'K16', 'K26', 'K36'],
    'U14': ['K07', 'K17', 'K27', 'K37', 'K08', 'K18', 'K28', 'K38'],
    'U15': ['K09', 'K19', 'K29', 'K39', 'K_RED', 'K_YEL', 'K_BLU', None],
}
IN_PINS = [11, 12, 13, 14, 3, 4, 5, 6]
rn = 1
cap = 1
for i, u in enumerate(CHAIN):
    nets = [n if n else '%s_SP%s' % (u, 'ABCDEFGH'[k]) for k, n in enumerate(INPUTS[u])]
    pins = {1: 'KEY_SHLD', 2: 'KEY_CLK', 15: 'GND', 16: '+3V3', 8: 'GND', 7: None,
            9: 'KEY_QH' if i == 0 else 'KEY_S%d' % i,
            10: 'KEY_S%d' % (i + 1) if i < 5 else 'GND'}
    for k, p in enumerate(IN_PINS):
        pins[p] = nets[k]
    part(u, '74HC165', '74HC165', pins, 'keys_' + ('left' if i < 3 else 'right'),
         fp='Package_SO:TSSOP-16_4.4x5mm_P0.65mm', mpn='74HC165PW,118', lcsc='C80696')
    for half in range(2):
        part('RN%d' % rn, 'RN4', '4x10k', {1: nets[half * 4], 2: nets[half * 4 + 1], 3: nets[half * 4 + 2],
                                            4: nets[half * 4 + 3], 5: '+3V3', 6: '+3V3', 7: '+3V3', 8: '+3V3'},
             'keys_' + ('left' if i < 3 else 'right'), fp='Resistor_SMD:R_Array_Convex_4x0603',
             mpn='4D03WGJ0103T5E', lcsc='C29718')
        rn += 1
    C('C%d' % (60 + i), '100nF', '+3V3', 'GND', 'keys_' + ('left' if i < 3 else 'right'))
R('R60', '33R', 'KEY_CLK_PB', 'KEY_CLK', 'keys_left')
R('R61', '33R', 'KEY_SHLD_PB', 'KEY_SHLD', 'keys_left')
part('TP1', 'TestPoint', 'M4F_SPARE', {1: 'M4F_SPARE'}, 'pb2', fp='TestPoint:TestPoint_Pad_D1.0mm',
     mpn=None, lcsc=None, dnp_bom=True)
SYMS['TestPoint'] = [(1, '1', 'B', 'passive')]

# ======================================================================================
# Display: 40-pin FPC (J3) + TPS61165 backlight boost (unchanged from v2 except PWM pin)
# ======================================================================================
J3PINS = {1: ('LEDA', 'BL_LEDA'), 2: ('LEDK', 'BL_LEDK'), 3: ('LEDK', 'BL_LEDK'), 4: ('GND', 'GND'),
          5: ('VCI', '+3V3'), 6: ('RESET', 'LCD_RESET'), 7: ('NC', None), 8: ('NC', None),
          9: ('SDA', 'LCD_SDA'), 10: ('SCK', 'LCD_SCK'), 11: ('CS', 'LCD_CS'), 12: ('PCLK', 'LCD_PCLK'),
          13: ('DE', 'LCD_DE'), 14: ('VSYNC', 'LCD_VSYNC'), 15: ('HSYNC', 'LCD_HSYNC'), 16: ('DB0', 'GND'),
          28: ('DB12', 'GND'), 34: ('GND', 'GND'), 35: ('TP_INT', None), 36: ('TP_SDA', None),
          37: ('TP_SCL', None), 38: ('TP_RESET', None), 39: ('TP_VCI', None), 40: ('GND', 'GND'),
          'MP': ('MP', 'GND')}
for k in range(11):           # DB1..DB11 = VOUT_D0..D10 on pins 17..27
    J3PINS[17 + k] = ('DB%d' % (k + 1), 'VOUT_D%d' % k)
for k in range(5):            # DB13..DB17 = VOUT_D11..D15 on pins 29..33
    J3PINS[29 + k] = ('DB%d' % (13 + k), 'VOUT_D%d' % (11 + k))
SYMS['LCD_FPC40'] = [(n, '%s' % J3PINS[n][0], 'L' if n != 'MP' and n <= 20 else 'R',
                      'power_in' if J3PINS[n][1] in ('GND',) else 'passive') for n in
                     sorted([k for k in J3PINS if k != 'MP']) ] + [('MP', 'MP', 'R', 'passive')]
part('J3', 'LCD_FPC40', 'F32Q-1A7H1-11040', {n: J3PINS[n][1] for n in J3PINS}, 'display',
     fp='Connector_FFC-FPC:Amphenol_F32Q-1A7x1-11040_1x40-1MP_P0.5mm_Horizontal',
     mpn='F32Q-1A7H1-11040', lcsc='C3168061')
SYMS['TPS61165'] = [(1, 'VIN', 'L', 'power_in'), (2, 'CTRL', 'L', 'input'), (4, 'GND', 'B', 'power_in'),
                    (3, 'SW', 'R', 'passive'), (6, 'FB', 'R', 'input'), (5, 'COMP', 'R', 'passive')]
part('U3', 'TPS61165', 'TPS61165DBVR', {1: '+5V_SYS', 2: 'BL_PWM', 3: 'BL_SW', 4: 'GND', 5: 'BL_COMP', 6: 'BL_LEDK'},
     'display', fp='Package_TO_SOT_SMD:SOT-23-6', mpn='TPS61165DBVR', lcsc='C58756')
part('L1', 'L', '22uH', {1: '+5V_SYS', 2: 'BL_SW'}, 'display', fp='Inductor_SMD:L_Changjiang_FNR4030S',
     mpn='FNR4030S220MT', lcsc='C167883')
part('D1', 'D_Schottky', 'B5819W', {1: 'BL_LEDA', 2: 'BL_SW'}, 'display', fp='Diode_SMD:D_SOD-123',
     mpn='B5819W SL', lcsc='C8598')
C('C1', '4.7uF 25V', '+5V_SYS', 'GND', 'display')
C('C2', '1uF 50V', 'BL_LEDA', 'GND', 'display')
C('C3', '220nF', 'BL_COMP', 'GND', 'display')
R('R1', '5.1R 1%', 'BL_LEDK', 'GND', 'display')
R('R2', '100k', 'BL_PWM', 'GND', 'display')

# ======================================================================================
# USB hub FE1.1s on USB1 + 2 rear USB-A (TPS2051B switch + USBLC6 ESD each)
# ======================================================================================
SYMS['FE1.1s'] = [(18, 'VBUSM', 'L', 'input'), (19, 'BUSJ', 'L', 'input'),
                  (16, 'DPU', 'L', 'bidirectional'), (15, 'DMU', 'L', 'bidirectional'),
                  (17, 'XRSTJ', 'L', 'input'),
                  (3, 'XIN', 'L', 'input'), (2, 'XOUT', 'L', 'output'), (14, 'REXT', 'L', 'passive'),
                  (26, 'OVCJ', 'L', 'input'), (25, 'PWRJ', 'L', 'open_collector'),
                  (20, 'VDD5', 'T', 'power_in'), (21, 'VD33F', 'T', 'power_out'), (1, 'VSS', 'B', 'power_in'),
                  (11, 'DP1', 'R', 'bidirectional'), (10, 'DM1', 'R', 'bidirectional'),
                  (9, 'DP2', 'R', 'bidirectional'), (8, 'DM2', 'R', 'bidirectional'),
                  (7, 'DP3', 'R', 'bidirectional'), (6, 'DM3', 'R', 'bidirectional'),
                  (5, 'DP4', 'R', 'bidirectional'), (4, 'DM4', 'R', 'bidirectional'),
                  (22, 'DRV', 'R', 'bidirectional'), (23, 'LED1', 'R', 'bidirectional'),
                  (24, 'LED2', 'R', 'bidirectional'), (27, 'TESTJ', 'R', 'bidirectional'),
                  (12, 'NC', 'R', 'no_connect'), (13, 'NC', 'R', 'no_connect'), (28, 'NC', 'R', 'no_connect')]
part('U4', 'FE1.1s', 'FE1.1s', {16: 'USB_UP_P', 15: 'USB_UP_N', 17: 'HUB_RST', 18: 'HUB_3V3', 19: 'HUB_3V3',
                                 3: 'HUB_XI', 2: 'HUB_XO', 14: 'HUB_REXT', 26: 'USB_OC_N', 25: None,
                                 20: '+5V_SYS', 21: 'HUB_3V3', 1: 'GND', 11: 'USB1_P', 10: 'USB1_N',
                                 9: 'USB2_P', 8: 'USB2_N', 7: None, 6: None, 5: None, 4: None,
                                 22: 'HUB_DRV', 23: None, 24: None, 27: None, 12: None, 13: None, 28: None},
     'hub', fp='Package_SO:SSOP-28_3.9x9.9mm_P0.635mm', mpn='FE1.1S-BSOP28BCN', lcsc='C9359')
part('Y1', 'Crystal4', '12MHz', {1: 'HUB_XI', 2: 'GND', 3: 'HUB_XO', 4: 'GND'}, 'hub',
     fp='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', mpn='TAXM12M4RLBDDT2T', lcsc='C133334')
R('R10', '2.7k 1%', 'HUB_REXT', 'GND', 'hub')
R('R11', '10k', 'HUB_3V3', 'HUB_RST', 'hub')
R('R12', '10k', 'HUB_3V3', 'USB_OC_N', 'hub')
R('R13', '10k', 'HUB_DRV', 'GND', 'hub')
C('C10', '100nF', 'HUB_RST', 'GND', 'hub')
C('C11', '10uF', '+5V_SYS', 'GND', 'hub')
C('C12', '100nF', '+5V_SYS', 'GND', 'hub')
C('C13', '10uF', 'HUB_3V3', 'GND', 'hub')
C('C14', '100nF', 'HUB_3V3', 'GND', 'hub')
SYMS['TPS2051B'] = [(5, 'IN', 'L', 'power_in'), (4, 'EN', 'L', 'input'), (2, 'GND', 'B', 'power_in'),
                    (1, 'OUT', 'R', 'power_out'), (3, '~{OC}', 'R', 'open_collector')]
SYMS['USBLC6-2SC6'] = [(1, 'I/O1', 'L', 'passive'), (6, 'I/O1', 'R', 'passive'), (3, 'I/O2', 'L', 'passive'),
                       (4, 'I/O2', 'R', 'passive'), (5, 'VBUS', 'T', 'passive'), (2, 'GND', 'B', 'passive')]
SYMS['USB_A'] = [(1, 'VBUS', 'L', 'passive'), (2, 'D-', 'L', 'passive'), (3, 'D+', 'L', 'passive'),
                 (4, 'GND', 'L', 'passive'), ('SH', 'SHIELD', 'B', 'passive')]
for k, (u, e, j, cb) in enumerate([('U5', 'U7', 'J7', 15), ('U6', 'U8', 'J8', 17)]):
    p = k + 1
    part(u, 'TPS2051B', 'TPS2051BDBVR', {5: '+5V_SYS', 4: '+5V_SYS', 2: 'GND', 1: 'USB%d_VBUS' % p, 3: 'USB_OC_N'},
         'hub', fp='Package_TO_SOT_SMD:SOT-23-5', mpn='TPS2051BDBVR', lcsc='C24593')
    part(e, 'USBLC6-2SC6', 'USBLC6-2SC6', {1: 'USB%d_N' % p, 6: 'USB%d_N' % p, 3: 'USB%d_P' % p, 4: 'USB%d_P' % p,
                                           5: 'USB%d_VBUS' % p, 2: 'GND'},
         'hub', fp='Package_TO_SOT_SMD:SOT-23-6', mpn='USBLC6-2SC6', lcsc='C2687116')
    part(j, 'USB_A', 'USB-A', {1: 'USB%d_VBUS' % p, 2: 'USB%d_N' % p, 3: 'USB%d_P' % p, 4: 'GND', 'SH': 'GND'},
         'hub', fp='zm_v3:USB_A_GCT_USB1046', mpn='USB1046-GF-0190-L-B-A', lcsc='C6307429')
    C('C%d' % cb, '100uF', 'USB%d_VBUS' % p, 'GND', 'hub')
    C('C%d' % (cb + 1), '100nF', '+5V_SYS', 'GND', 'hub')

# ======================================================================================
# Power: rear USB-C (charge only) -> IP5306 (2-LED mode) -> P-FET switched +5V_SYS
# ======================================================================================
SYMS['USB_C_6P'] = [('A9', 'VBUS', 'L', 'passive'), ('B9', 'VBUS', 'L', 'passive'), ('A5', 'CC1', 'L', 'passive'),
                    ('B5', 'CC2', 'L', 'passive'), ('A12', 'GND', 'B', 'passive'), ('B12', 'GND', 'B', 'passive'),
                    ('7', 'SHIELD', 'B', 'passive')]
part('J6', 'USB_C_6P', 'USB-C 6P', {'A9': 'VIN_CHG', 'B9': 'VIN_CHG', 'A5': 'CHG_CC1', 'B5': 'CHG_CC2',
                                    'A12': 'GND', 'B12': 'GND', '7': 'GND'},
     'power', fp='zm_v3:USB_C_Receptacle_6P_ShouHan', mpn='TYPE-C 6P', lcsc='C456012')
R('R20', '5.1k', 'CHG_CC1', 'GND', 'power')
R('R21', '5.1k', 'CHG_CC2', 'GND', 'power')
SYMS['IP5306'] = [(1, 'VIN', 'T', 'power_in'), (3, 'LED2', 'T', 'passive'), (6, 'BAT', 'T', 'power_in'),
                  (8, 'VOUT', 'T', 'power_out'),
                  (5, 'KEY', 'L', 'input'), (2, 'LED1', 'L', 'output'), (4, 'LED3', 'L', 'output'),
                  (7, 'SW', 'R', 'output'),
                  (9, 'EP', 'B', 'power_in')]
part('U9', 'IP5306', 'IP5306', {1: 'VIN_CHG', 5: 'PWR_KEY', 2: 'LED_CHG', 3: 'VBAT', 4: 'LED_PWR', 8: '+5V_BOOST',
                                7: 'CHG_SW', 6: 'VBAT', 9: 'GND'},
     'power', fp='Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm', mpn='IP5306', lcsc='C181692')
part('L2', 'L', '1uH', {1: 'CHG_SW', 2: 'VBAT'}, 'power', fp='Inductor_SMD:L_Sunlord_MWSA0603S',
     mpn='MWSA0603S-1R0MT', lcsc='C112125')
C('C20', '10uF', 'VIN_CHG', 'GND', 'power')
R('R22', '2R', 'VIN_CHG', 'CHG_SNUB', 'power')
C('C21', '10uF', 'CHG_SNUB', 'GND', 'power')
C('C22', '22uF', 'VBAT', 'GND', 'power')
R('R23', '0.5R', 'VBAT', 'BAT_SNUB', 'power')
C('C23', '22uF', 'BAT_SNUB', 'GND', 'power')
C('C24', '22uF', '+5V_BOOST', 'GND', 'power')
C('C25', '22uF', '+5V_BOOST', 'GND', 'power')
C('C26', '22uF', '+5V_BOOST', 'GND', 'power')
part('D2', 'LED', 'red CHG', {1: 'CHG_LED_K', 2: 'LED_CHG'}, 'power', fp=FP_LED, mpn='KT-0603R', lcsc='C2286')
R('R24', '1k', 'CHG_LED_K', 'GND', 'power')
part('D3', 'LED', 'green PWR', {1: 'PWR_LED_K', 2: 'LED_PWR'}, 'power', fp=FP_LED, mpn='XL-1608UGC-04', lcsc='C965804')
R('R25', '1k', 'PWR_LED_K', 'GND', 'power')
SYMS['Batt_JST'] = [(1, '+', 'L', 'passive'), (2, '-', 'L', 'passive')]
part('J5', 'Batt_JST', 'LiPo 1S', {1: 'VBAT', 2: 'GND'}, 'power',
     fp='Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical', mpn='B2B-PH-K-S(LF)(SN)', lcsc='C131337')
# power switch: pole A grounds the P-FET gate (ON); pole B gives the IP5306 KEY one short press
SYMS['SW_DPDT'] = [(5, 'B', 'L', 'passive'), (2, 'A', 'L', 'passive'),
                   (6, 'B_ON', 'R', 'passive'), (4, 'B_OFF', 'R', 'passive'),
                   (1, 'A_ON', 'R', 'passive'), (3, 'A_OFF', 'R', 'passive'),
                   (7, 'MNT', 'B', 'passive'), (8, 'MNT', 'B', 'passive')]
part('SW44', 'SW_DPDT', 'SK22D02G4', {2: 'PWR_SW', 1: 'GND', 3: None, 5: 'VBAT', 6: 'PWR_KEY_C', 4: None,
                                      7: 'GND', 8: 'GND'},
     'power', fp='zm_v3:SW_Slide_DPDT_SK22D02G4_Angled', mpn='SK22D02G4', lcsc='C22435630')
part('Q1', 'PMOS', 'AO3401A', {1: 'PWR_GATE', 2: '+5V_BOOST', 3: '+5V_SYS'}, 'power',
     fp='Package_TO_SOT_SMD:SOT-23', mpn='AO3401A', lcsc='C15127')
R('R26', '100k', 'PWR_GATE', '+5V_BOOST', 'power')
C('C27', '100nF', 'PWR_GATE', '+5V_BOOST', 'power')
R('R27', '10k', 'PWR_SW', 'PWR_GATE', 'power')
C('C28', '22uF', '+5V_SYS', 'GND', 'power')
C('C29', '22uF', '+5V_SYS', 'GND', 'power')
C('C30', '1uF', 'PWR_KEY_C', 'PWR_KEY_G', 'power')
R('R28', '1M', 'PWR_KEY_C', 'GND', 'power')
R('R29', '470k', 'PWR_KEY_G', 'GND', 'power')
part('Q2', 'NMOS', 'AO3400A', {1: 'PWR_KEY_G', 2: 'GND', 3: 'PWR_KEY_D'}, 'power',
     fp='Package_TO_SOT_SMD:SOT-23', mpn='AO3400A', lcsc='C20917')
R('R30', '1k', 'PWR_KEY_D', 'PWR_KEY', 'power')
R('R31', '1M', 'VBAT', 'VBAT_SENSE', 'power')
R('R32', '1M', 'VBAT_SENSE', 'GND', 'power')
C('C31', '100nF', 'VBAT_SENSE', 'GND', 'power')
# boot LED on P1.35
part('D4', 'LED', 'yellow BOOT', {1: 'BOOT_LED_K', 2: 'LED_BOOT'}, 'pb2', fp=FP_LED, mpn='NCD0603Y2', lcsc='C89811')
R('R33', '1k', 'BOOT_LED_K', 'GND', 'pb2')

# ======================================================================================
# Audio: ES8388 (I2S master, 12.288 MHz osc) + TPS73633 AVDD + headset TRRS + line-out TRS
# ======================================================================================
SYMS['ES8388'] = [(1, 'MCLK', 'L', 'input'), (5, 'SCLK', 'L', 'bidirectional'), (7, 'LRCK', 'L', 'bidirectional'),
                  (6, 'DSDIN', 'L', 'input'), (8, 'ASDOUT', 'L', 'output'), (28, 'CCLK', 'L', 'input'),
                  (27, 'CDATA', 'L', 'bidirectional'),
                  (24, 'LIN1', 'L', 'input'), (23, 'RIN1', 'L', 'input'), (22, 'LIN2', 'L', 'input'),
                  (21, 'RIN2', 'L', 'input'), (26, 'CE', 'L', 'input'),
                  (2, 'DVDD', 'T', 'power_in'), (3, 'PVDD', 'T', 'power_in'), (17, 'AVDD', 'T', 'power_in'),
                  (16, 'HPVDD', 'T', 'power_in'),
                  (4, 'DGND', 'B', 'power_in'), (18, 'AGND', 'B', 'power_in'), (13, 'HPGND', 'B', 'power_in'),
                  (29, 'EP', 'B', 'power_in'),
                  (12, 'LOUT1', 'R', 'output'), (11, 'ROUT1', 'R', 'output'), (15, 'LOUT2', 'R', 'output'),
                  (14, 'ROUT2', 'R', 'output'), (10, 'VREF', 'R', 'passive'), (19, 'ADCVREF', 'R', 'passive'),
                  (20, 'VMID', 'R', 'passive'), (9, 'NC', 'R', 'no_connect'), (25, 'NC', 'R', 'no_connect')]
part('U17', 'ES8388', 'ES8388', {1: 'MCLK', 5: 'I2S_BCLK_C', 7: 'I2S_LRCK_C', 6: 'I2S_DAC_C', 8: 'I2S_ADC_C',
                                 28: 'I2C_SCL', 27: 'I2C_SDA', 26: 'GND', 24: 'MIC_IN', 23: None, 22: None, 21: None,
                                 2: '+3V3', 3: '+3V3', 17: 'AVDD_3V3', 16: 'AVDD_3V3', 4: 'GND', 18: 'GND',
                                 13: 'GND', 29: 'GND', 12: 'HP_L_C', 11: 'HP_R_C', 15: 'LO_L_C', 14: 'LO_R_C',
                                 10: 'CODEC_VREF', 19: 'CODEC_ADCVREF', 20: 'CODEC_VMID', 9: None, 25: None},
     'audio', fp='Package_DFN_QFN:QFN-28-1EP_4x4mm_P0.4mm_EP2.4x2.4mm', mpn='ES8388', lcsc='C365736')
SYMS['Osc'] = [(1, 'OE', 'L', 'input'), (4, 'VDD', 'T', 'power_in'), (2, 'GND', 'B', 'power_in'),
               (3, 'OUT', 'R', 'output')]
part('X1', 'Osc', '12.288MHz', {1: '+3V3', 4: '+3V3', 2: 'GND', 3: 'MCLK_OSC'}, 'audio',
     fp='Oscillator:Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm', mpn='OT2EL4C4JI-111OLP-12.288M', lcsc='C5203546')
C('C40', '100nF', '+3V3', 'GND', 'audio')
R('R40', '33R', 'MCLK_OSC', 'MCLK', 'audio')
R('R41', '33R', 'I2S_BCLK_C', 'I2S_BCLK', 'audio')
R('R42', '33R', 'I2S_LRCK_C', 'I2S_LRCK', 'audio')
R('R43', '33R', 'I2S_ADC_C', 'I2S_ADC', 'audio')
R('R44', '33R', 'I2S_DAC', 'I2S_DAC_C', 'audio')
R('R45', '2.2k', '+3V3', 'I2C_SCL', 'audio')
R('R46', '2.2k', '+3V3', 'I2C_SDA', 'audio')
C('C41', '100nF', '+3V3', 'GND', 'audio')      # DVDD
C('C42', '100nF', '+3V3', 'GND', 'audio')      # PVDD
C('C43', '10uF', '+3V3', 'GND', 'audio')
C('C44', '100nF', 'AVDD_3V3', 'GND', 'audio')  # AVDD
C('C45', '10uF', 'AVDD_3V3', 'GND', 'audio')
C('C46', '100nF', 'AVDD_3V3', 'GND', 'audio')  # HPVDD
C('C47', '10uF', 'AVDD_3V3', 'GND', 'audio')
C('C48', '10uF', 'CODEC_VREF', 'GND', 'audio')
C('C49', '100nF', 'CODEC_VREF', 'GND', 'audio')
C('C50', '10uF', 'CODEC_ADCVREF', 'GND', 'audio')
C('C51', '10uF', 'CODEC_VMID', 'GND', 'audio')
C('C52', '100nF', 'CODEC_VMID', 'GND', 'audio')
SYMS['LDO_NR'] = [(1, 'IN', 'L', 'power_in'), (3, 'EN', 'L', 'input'), (2, 'GND', 'B', 'power_in'),
                  (5, 'OUT', 'R', 'power_out'), (4, 'NR', 'R', 'passive')]
part('U16', 'LDO_NR', 'TPS73633DBVR', {1: '+5V_SYS', 3: '+5V_SYS', 2: 'GND', 5: 'AVDD_3V3', 4: 'LDO_NR'}, 'audio',
     fp='Package_TO_SOT_SMD:SOT-23-5', mpn='TPS73633DBVR', lcsc='C28038')
C('C53', '1uF', '+5V_SYS', 'GND', 'audio')
C('C54', '10nF', 'LDO_NR', 'GND', 'audio')
C('C55', '10uF', 'AVDD_3V3', 'GND', 'audio')
# headphone (headset jack, CTIA) and line out
C('C56', '100uF', 'HP_L_C', 'HP_L', 'audio')
C('C57', '100uF', 'HP_R_C', 'HP_R', 'audio')
R('R47', '10k', 'HP_L', 'GND', 'audio')
R('R48', '10k', 'HP_R', 'GND', 'audio')
C('C58', '10uF', 'LO_L_C', 'LO_L', 'audio')
C('C59', '10uF', 'LO_R_C', 'LO_R', 'audio')
R('R49', '47k', 'LO_L', 'GND', 'audio')
R('R50', '47k', 'LO_R', 'GND', 'audio')
R('R51', '1k', 'AVDD_3V3', 'MIC_BIAS_F', 'audio')
C('C66', '10uF', 'MIC_BIAS_F', 'GND', 'audio')
R('R52', '2.2k', 'MIC_BIAS_F', 'MIC', 'audio')
C('C67', '1uF', 'MIC', 'MIC_IN', 'audio')
R('R53', '100k', '+3V3', 'HP_DET', 'audio')
SYMS['Jack_TRRS_SW'] = [(2, 'T', 'L', 'passive'), (4, 'R1', 'L', 'passive'), (5, 'R1_SW', 'L', 'passive'),
                        (1, 'S', 'L', 'passive'), (3, 'R2', 'L', 'passive')]
part('J9', 'Jack_TRRS_SW', 'Headset (CTIA)', {2: 'HP_L', 4: 'HP_R', 5: 'HP_DET', 3: 'GND', 1: 'MIC'}, 'audio',
     fp='zm_v3:Jack_3.5mm_PJ-327A_5JJ', mpn='PJ-327A 5JJ', lcsc='C668605')
SYMS['Jack_TRS'] = [(4, 'T', 'L', 'passive'), (2, 'R', 'L', 'passive'), (3, 'S', 'L', 'passive')]
part('J10', 'Jack_TRS', 'Line out', {4: 'LO_L', 2: 'LO_R', 3: 'GND'}, 'audio',
     fp='zm_v3:Jack_3.5mm_PJ-320A-3P_DIP', mpn='PJ-320A-3P DIP', lcsc='C17701689')

# ======================================================================================
# Mechanical: tray screws (unchanged) + display chassis posts
# ======================================================================================
HOLES = [('H1', 91.375, 48.875), ('H2', 125.375, 65.875), ('H3', 125.375, 31.875), ('H4', 193.375, 65.875),
         ('H5', 193.375, 31.875), ('H6', 227.375, 48.875),
         ('H7', 112.575, 9.475), ('H8', 112.575, -33.025), ('H9', 219.275, 9.475), ('H10', 219.275, -33.025)]
for ref, x, y in HOLES:
    part(ref, 'MountingHole', 'M2', {}, 'mech',
         fp='MountingHole:MountingHole_2.2mm_M2_ISO7380' if int(ref[1:]) <= 6 else 'MountingHole:MountingHole_2.2mm_M2',
         mpn=None, lcsc=None, dnp_bom=True, pos=(x, y))
SYMS['MountingHole'] = []

# power flags (ERC): nets driven only through passive pins
FLAGS = ['GND', 'VBAT', 'VIN_CHG', '+5V_SYS']

def nets():
    out = {}
    for p in PARTS:
        for pin, n in p['pins'].items():
            if n:
                out.setdefault(n, []).append((p['ref'], pin))
    return out

if __name__ == '__main__':
    ns = nets()
    print(len(PARTS), 'parts', len(ns), 'nets')
    for n, nodes in sorted(ns.items()):
        if len(nodes) < 2:
            print('single-node net', n, nodes)
