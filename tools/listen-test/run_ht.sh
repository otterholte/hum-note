#!/bin/bash
# Runs a variant on a HumTrans set and scores it. usage: run_ht.sh <set: ht|htx> <variant.html> [vib]
cd "$(dirname "$0")"; SET=$1; H=$2; M=${3:+vib}; mkdir -p "out_$SET"
for f in "$SET"/*.wav; do b=$(basename "$f" .wav); SWMODE=$M SWIFT=$PWD/${SET}_swift DRIFT=1 nice -n 19 node ../pitch-compare/app_dump.js "$H" "$f" "out_$SET/$b.json" >/dev/null 2>&1 || echo "FAIL $b"; done
node score_ht.js "$SET" ${LIST:+--list}
