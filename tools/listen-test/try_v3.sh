#!/bin/bash
# Scores a v3 build on everything. usage: try_v3.sh <name> opt=val ...
cd "$(dirname "$0")"; N=$1; shift; python build_v3.py variants/$N.html "$@" >/dev/null || exit 1
A=$(bash try_all.sh variants/$N.html vib | sed 's/^[^:]*: //'); H=$(bash run_ht.sh ht variants/$N.html vib | sed 's/ over.*//;s/AVERAGE //')
echo "$N: $A || humming(ht) $H"
