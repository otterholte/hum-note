#!/bin/bash
# Scores one app variant on every test: the 38-clip benchmark, the 8 listening clips, and the user's corrected take.
# usage: try_all.sh <variant.html> [vib]   (vib: AI pitch only in vibrato stretches)
cd "$(dirname "$0")"; H=$1; M=${2:+vib}
B=$(SWMODE=$M USE_SWIFT=1 nice -n 19 bash run_bench.sh bench "$H" | tail -1 | sed 's/AVERAGE //;s/ over 38//')
C=$(SWMODE=$M USE_SWIFT=1 nice -n 19 bash run_bench.sh clips "$H" | tail -1 | sed 's/AVERAGE //;s/ over 8//')
KEY="C3 D3 E3 D3 C3 D3 C3 A2 C3  C3 D3 E3 D3 C3 D3 C3 A2 D3  C3 D3 E3 G3 D3 E3 D3 C3 A2 C3  E3 F3 F3 E3"
P=../pitch-compare; SWMODE=$M SWIFT=$PWD/$P/take_swift DRIFT=1 node $P/app_dump.js "$H" ../../recordings/hum_2026-11-24_015826.wav /tmp/ak_$$.json >/dev/null
T=$(node $P/answer_key.js /tmp/ak_$$.json "$KEY" | head -1 | sed 's/.*differences: //')
echo "$(basename "$H" .html)${M:+ [vib-only AI]}: bench $B || clips $C || your take: $T differences"
