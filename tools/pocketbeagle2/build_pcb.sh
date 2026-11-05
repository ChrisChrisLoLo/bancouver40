#!/bin/sh
# Rebuild the extended bancouver40 PCB from the untouched original and run DRC.
#   tools/pocketbeagle2/build_pcb.sh ORIGINAL.kicad_pcb OUTPUT.kicad_pcb
set -e
PY="$HOME/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3"
KCLI="$HOME/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
D="$(cd "$(dirname "$0")" && pwd)"
T="$(mktemp -d)"
quiet() { grep -v -E "assert|memory leak|Debug:" || true; }
"$PY" "$D/pcb_strip.py"  "$1"              "$T/s0.kicad_pcb" 2>&1 | quiet
"$PY" "$D/pcb_extend.py" "$T/s0.kicad_pcb" "$T/s1.kicad_pcb" 2>&1 | quiet
"$PY" "$D/pcb_route.py"  "$T/s1.kicad_pcb" "$2" "$T"         2>&1 | quiet
echo "work dir: $T"
"$KCLI" pcb drc --format json --severity-error -o "${2%.kicad_pcb}-drc.json" "$2" | tail -2
