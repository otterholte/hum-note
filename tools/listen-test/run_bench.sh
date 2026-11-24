#!/bin/bash
# Runs Humnote's detection on every clip in a set and scores it. usage: run_bench.sh <set dir: bench|clips> [index.html]
cd "$(dirname "$0")"; SET=${1:-bench}; HTML=${2:-../../index.html}; mkdir -p "out_$SET"
for f in "$SET"/*.wav; do b=$(basename "$f" .wav); SWIFT=${USE_SWIFT:+$PWD/${SET}_swift} DRIFT=1 node ../pitch-compare/app_dump.js "$HTML" "$f" "out_$SET/$b.json" >/dev/null 2>&1 || echo "FAIL $b"; done
node score_set.js "$SET"
