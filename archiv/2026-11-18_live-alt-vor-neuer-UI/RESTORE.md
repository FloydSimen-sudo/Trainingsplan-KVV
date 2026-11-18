# Wiederherstellung: Live-Stand vom 18.11.2026 (alte Oberfläche, vor Umstellung auf die neue UI)

Gesichert in drei Formen:
1. Git-Tag `live-2026-11-18-alt` (Commit mit altem index.html + tp-data.enc.js)
2. Dieser Ordner (Dateikopien, auch index-live.html, die nicht in Git liegt)
3. Alte Oberfläche bleibt zusätzlich unter `index-alt.html` erreichbar (liest die aktuellen Daten)

## Stufen (im Repo-Hauptordner ausführen, danach committen + pushen)
- Stufe 1, nur Oberfläche zurück (Daten bleiben aktuell):
  `cp archiv/2026-11-18_live-alt-vor-neuer-UI/index.html index.html`
- Stufe 2, nur Daten zurück (neue Oberfläche bleibt):
  `cp archiv/2026-11-18_live-alt-vor-neuer-UI/tp-data.enc.js tp-data.enc.js`
- Stufe 3, alles zurück:
  `cp archiv/2026-11-18_live-alt-vor-neuer-UI/{index.html,index-live.html,tp-data.enc.js,trainer-data.enc.js} .`
  (oder `git checkout live-2026-11-18-alt -- index.html tp-data.enc.js trainer-data.enc.js`)
- Stufe 4, einzelne Elemente der neuen UI: sie entstehen aus build/beta_ui.js, build/beta_wk.frag.js (Wettkämpfe, Phasen-Pillen, Stand),
  build/beta_jz.frag.js (Jahresplanung). Jede Datei ist ein Element; ältere Fassungen via `git log -- build/beta_wk.frag.js`
  und `git checkout <commit> -- <datei>`, dann `TP_PASSWORD=... node build/build_beta.js --promote`.
  Die Kopien der Bau-Dateien vom Umstellungstag liegen in `build/`.
