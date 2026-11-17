#!/bin/bash
# Aktualisiert NUR eine Gruppe. Aufruf im Repo-Hauptordner: TP_PASSWORD=... bash build/update_gruppe.sh "g:U15 II"
set -e
export GKEY="$1"
export TP_TMP=$(mktemp -d "$HOME/tpupd.XXXXXX")
git show HEAD:tp-data.enc.js > "$TP_TMP/prev.enc.js"
(cd build && for i in 1 2 3; do python3 build_tpdata_v2.py >/dev/null 2>&1 && break; sleep 10; done)
cp tp-data.js "$TP_TMP/tp-data.gruppe.js"
node build/merge_gruppe.js
node build/encrypt_tpdata.js | tail -1
node build/build_beta.js | tail -1
node build/test.js 2>&1 | grep "^FAIL" || echo "Tests ohne FAIL"
