#!/bin/sh
# Route the generated board with KiCadRoutingTools (https://github.com/drandyhaas/KiCadRoutingTools), within the
# fab limits (escalation off): GND plane on In1, USB pairs as diff pairs, then everything else with rip-up.
# Usage: tools/zm_v3/krt_route.sh <stage.kicad_pcb> <workdir>   (KRT checkout in $KRT, python in $PY)
set -e
KRT=${KRT:-/tmp/krt/repo}; PY=${PY:-/tmp/zmvenv/bin/python}
STAGE=$(readlink -f "$1"); W=$(readlink -m "$2"); HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$W"
python3 - "$STAGE" "$W/board.kicad_pcb" "$HERE" <<'PYEOF'
import sys; sys.path.insert(0, sys.argv[3])
from sexp import parse, dump, find
b = parse(open(sys.argv[1]).read())
b = [e for e in b if not (isinstance(e, list) and e and e[0] == 'zone' and find(e, 'keepout') is None)]
open(sys.argv[2], 'w').write(dump(b) + '\n')
PYEOF
PRO=$(readlink -f "$(dirname "$STAGE")/../bancouver40_pb2.kicad_pro")
for f in board p d; do cp "$PRO" "$W/$f.kicad_pro"; done
cd "$KRT"
COMMON="--clearance 0.127 --via-size 0.6 --via-drill 0.3 --escalation off --fab-tier standard"
$PY py_router/route_planes.py "$W/board.kicad_pcb" --output "$W/p.kicad_pcb" --nets GND --plane-layers In1.Cu \
    --clearance 0.127 --via-size 0.6 --via-drill 0.3 --board-edge-clearance 0.3 --zone-clearance 0.2 --min-thickness 0.2 > "$W/planes.log" 2>&1
cp "$PRO" "$W/p.kicad_pro"
$PY py_router/route_diff.py "$W/p.kicad_pcb" --output "$W/d.kicad_pcb" --nets "*USB1_[PN]" "*USB2_[PN]" --track-width 0.3 \
    --diff-pair-gap 0.15 --layers F.Cu In2.Cu B.Cu $COMMON > "$W/diff.log" 2>&1
cp "$PRO" "$W/d.kicad_pro"
$PY py_router/route.py "$W/d.kicad_pcb" --output "$W/r.kicad_pcb" --nets "*" --layers F.Cu In2.Cu B.Cu --track-width 0.15 $COMMON \
    --power-nets "+5V_SYS" "+5V_BOOST" "VBAT" "VIN_CHG" "*CHG_SW" "*USB1_VBUS" "*USB2_VBUS" "*BAT_SNUB" "*CHG_SNUB" "*BL_SW" "*BL_LEDA" "GND" "+3V3" "AVDD_3V3" "HUB_3V3" \
    --power-nets-widths 0.6 0.6 0.6 0.6 0.6 0.6 0.6 0.4 0.4 0.4 0.4 0.4 0.3 0.3 0.3 > "$W/route.log" 2>&1
grep -E 'Diff pairs:|Single-ended|Ships broken|JSON_SUMMARY_MIN' "$W/diff.log" "$W/route.log" | tail -6 | cut -c1-600
