#!/bin/bash
# Scores a v4 build on every set. usage: try_v4.sh <name> opt=val ...
cd "$(dirname "$0")"; N=$1; shift; python build_v4.py variants/$N.html "$@" >/dev/null || exit 1
A=$(bash try_all.sh variants/$N.html vib | sed 's/^[^:]*: //;s/  |  straight.*|| clips/|| clips/;s/  |  synthetic[^|]*//')
r(){ bash run_ht.sh $1 variants/$N.html vib | sed 's/AVERAGE //;s/ | F1 \([0-9.]*\).*/ F1 \1/'; }
echo "$N: $A || ht $(r ht) || csd $(r csd) || csdx $(r csdx) || htx $(r htx)"
