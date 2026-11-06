#!/bin/sh
# Close the last open connections: grid router with rip-up (connect.py, RIP=1) then KiCadRoutingTools reroutes the
# ripped nets; repeat. Usage: finish.sh <dir> <start-name>   (files <dir>/<name>.kicad_pcb/.kicad_pro)
D=$(readlink -f "$1"); N=$2; KRT=${KRT:-/tmp/krt/repo}; PY=${PY:-/tmp/zmvenv/bin/python}; HERE=$(cd "$(dirname "$0")" && pwd)
K=/home/bp/opt/backplane-kicad-10.99.0-bp.6/bin/kicad-cli
for i in 1 2 3 4; do
  "$K" pcb drc --refill-zones -o "$D/$N.rpt" "$D/$N.kicad_pcb" >/dev/null 2>&1
  U=$(grep -c '^\[unconnected' "$D/$N.rpt"); E=$(grep -A2 -E '^\[' "$D/$N.rpt" | grep -c '; error')
  echo "round $i: $N unconnected $U, error items $E"
  [ "$U" = 0 ] && break
  RIP=1 $PY "$HERE/connect.py" "$D/$N.kicad_pcb" "$D/$N.rpt" "$D/${N}c.kicad_pcb" | sed 's/^/  /'
  cp "$D/$N.kicad_pro" "$D/${N}c.kicad_pro"; NEXT=${N}c
  if [ -s "$D/${N}c.kicad_pcb.ripped" ]; then
    NETS=$(while read -r n; do printf '"*%s" ' "$(basename "$n")"; done < "$D/${N}c.kicad_pcb.ripped")
    rm -f "$D/${N}c.kicad_pcb.ripped"
    (cd "$KRT" && eval $PY py_router/route.py "$D/${N}c.kicad_pcb" --output "$D/${N}k.kicad_pcb" --nets $NETS \
      --rip-existing-nets '"*"' --layers F.Cu In2.Cu B.Cu --track-width 0.15 --clearance 0.127 --via-size 0.6 --via-drill 0.3 \
      --escalation off --fab-tier standard > "$D/${N}k.log" 2>&1)
    cp "$D/$N.kicad_pro" "$D/${N}k.kicad_pro"; NEXT=${N}k
  fi
  N=$NEXT
done
echo "final: $N"
