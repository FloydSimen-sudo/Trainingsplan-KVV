#!/bin/bash
# Aktualisiert NUR die Einzelathleten (Plaene + Jahresplan) auf Basis des letzten committeten Live-Stands.
# Gruppen, Doku, Routen usw. bleiben unveraendert. Aufruf im Repo-Hauptordner: TP_PASSWORD=... bash build/update_einzel.sh
set -e
export TP_TMP=$(mktemp -d "$HOME/tpupd.XXXXXX")
git show HEAD:tp-data.enc.js > "$TP_TMP/prev.enc.js"
(cd build && for i in 1 2 3; do python3 build_tpdata_v2.py >/dev/null 2>&1 && break; sleep 10; done)
cp tp-data.js "$TP_TMP/tp-data.einzel.js"
node build/merge_einzel.js
node build/encrypt_tpdata.js | tail -1
node build/build_beta.js | tail -1
node build/test.js 2>&1 | grep "^FAIL" || echo "Tests ohne FAIL"
