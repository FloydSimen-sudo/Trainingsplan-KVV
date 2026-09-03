# Trainingsplan-App — Build-Werkzeuge

Dieser Ordner enthält die Werkzeuge, mit denen `tp-data.js` (die Datendatei der App) aus Floyds Excel-Dateien erzeugt wird, plus den automatisierten Test für `index.html`.

**Warum das hier im Repo liegt:** Diese Skripte sind bisher nur im Cowork-Arbeitsbereich (einer temporären Cloud-Umgebung) entstanden und existierten NIRGENDS dauerhaft — wäre der Chat verloren gegangen, wären sie mitsamt allem gesammelten Excel-Schema-Wissen weg gewesen. Ab jetzt liegen sie hier im Git-Repo und werden mit committet/gepusht wie alles andere.

Die ausführliche Prozess-Doku (wann/wie/warum) steht im Obsidian-Vault unter `KI-Assistenz Baselayer/Arbeitsweise/Trainerassistenz/Trainingsplan-App – Workflow für KI-Übergabe.md`. Dieses README ist nur die technische Kurzfassung.

## Dateien

- `build_tpdata_v2.py` — liest alle Excel-Quellen aus dem Testspace-Ordner und schreibt `tp-data.js`.
- `test.js` — Node-basierter Test für `index.html` (liest `index.html` + `tp-data.js`, führt alle Checks in einer `vm`-Sandbox aus). Mit `node test.js` ausführen (Node ohne npm-Pakete nötig).

## Voraussetzungen zum Ausführen von `build_tpdata_v2.py`

- Python 3 mit `openpyxl` (`pip install openpyxl --break-system-packages`, falls nicht vorhanden).
- Alle Excel-Quelldateien müssen lokal erreichbar sein (siehe unten `BASE`).

## Wichtig vor dem Ausführen: Pfade anpassen

Am Kopf der Datei stehen zwei Pfade, die auf die Cowork-Cloud-Umgebung zeigen und in einer neuen Umgebung angepasst werden müssen:

```python
BASE = '/mnt/user-data/uploads/Testspace/'   # wo die gestagten/kopierten Excel-Dateien liegen
OUT  = '/home/claude/tpapp/design/tp-data.js'  # wohin tp-data.js geschrieben wird
```

`BASE` muss auf eine lokale Kopie des OneDrive-Ordners `KVV Trainingsplanung/Testspace` zeigen (Unterordner `Einzelpläne/`, `Gruppenpläne/<Gruppe>/`, `Zusatzinfos/`). `OUT` sollte auf `tp-data.js` im Repo-Wurzelverzeichnis zeigen, damit die erzeugte Datei direkt an der richtigen Stelle landet.

## Ausführen

```bash
python3 build_tpdata_v2.py
node test.js   # danach: alle Tests müssen grün sein, bevor ausgeliefert wird
```

Details zu Datenschema, bekannten Excel-Eigenheiten und dem kompletten Ausliefer-Workflow: siehe die Obsidian-Notiz (Link oben).
