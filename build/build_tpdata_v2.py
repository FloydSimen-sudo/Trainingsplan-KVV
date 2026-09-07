#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trainingsplan KVV — Excel -> tp-data.js  (Version 2, Neuaufbau)
Liest alle echten Quelldateien aus dem Testspace-Ordner und baut eine
tp-data.js im Schema, das die App (index.html) erwartet.

Kein Wert wird erfunden: fehlt eine Angabe in Excel, wird null geschrieben
und die App zeigt "-" an.
"""
import openpyxl, json, re, subprocess, sys, glob, os
from datetime import date, timedelta

BASE = "/sessions/rcw-0151s7tv8hxkojd4a1uavrle/mnt/Testspace/"
OUT = "/sessions/rcw-0151s7tv8hxkojd4a1uavrle/mnt/Trainingsplan-KVV/tp-data.js"

def resolve_file(*candidates):
    """Nimmt den ersten existierenden Pfad; wenn ein Kandidat nicht exakt
    existiert, wird VOR dem nächsten Kandidaten erst per Glob nach einer
    OneDrive-Konfliktkopie im selben Ordner gesucht (z.B. 'Name 2.xlsx').
    Wichtig: das muss pro Kandidat passieren (nicht erst ganz am Ende),
    sonst gewinnt ein veralteter Fallback-Pfad (z.B. eine liegen gebliebene
    Kopie im alten Wurzelordner) fälschlich gegen eine Konfliktkopie im
    eigentlich richtigen, neueren Ordner (Bug bei Jakob Burtscher 28./30.08.:
    root-Datei 'Jakob Burtscher 26_27.xlsx' war ein alter Stand ohne die
    neuen Trainingsinhalte, wurde aber vor der echten Konfliktkopie in
    Einzelpläne/ gefunden)."""
    for cand in candidates:
        if os.path.exists(cand):
            return cand
        base_dir = os.path.dirname(cand)
        stem = os.path.splitext(os.path.basename(cand))[0]
        prefix = re.sub(r'\s*\d*$', '', stem).strip()
        hits = glob.glob(os.path.join(base_dir, prefix + '*.xlsx')) if os.path.isdir(base_dir) else []
        if hits:
            return hits[0]
    return candidates[0]

# ---------------------------------------------------------------- Kader ----

KADER_FILE = BASE + 'Zusatzinfos/Kaderaufstellung – Kopie.xlsx'

def norm(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower()) if s else ''

def load_kader():
    wb = openpyxl.load_workbook(KADER_FILE, data_only=True)
    ws = wb['Tabelle1']
    groups = []          # [{id, coaches, athletes:[{n,wk}]}]
    cur = None
    for r in range(4, ws.max_row + 1):
        vor = ws.cell(row=r, column=2).value
        nach = ws.cell(row=r, column=3).value
        wk27 = ws.cell(row=r, column=5).value
        grp = ws.cell(row=r, column=6).value
        trainer = ws.cell(row=r, column=7).value
        if not vor or str(vor).strip() in ('', '\xa0'):
            continue
        name = f"{str(vor).strip()} {str(nach).strip()}"
        if grp and str(grp).strip():
            gid = str(grp).strip()
            cur = {'id': gid, 'coaches': (str(trainer).strip() if trainer else ''), 'athletes': []}
            groups.append(cur)
        if cur is not None:
            cur['athletes'].append({'n': name, 'wk': str(wk27).strip() if wk27 else None})
    return groups

# --------------------------------------------------------- Übungssammlung --

def load_ex():
    wb = openpyxl.load_workbook(BASE + 'Zusatzinfos/Übungssammlung.xlsx', data_only=True)
    ws = wb['Tabelle1']
    ex = {}
    for r in range(2, ws.max_row + 1):
        name = ws.cell(row=r, column=3).value
        if not name:
            continue
        ex[str(name).strip()] = {
            'min': ws.cell(row=r, column=4).value,
            'sets': ws.cell(row=r, column=5).value,
            'vol': ws.cell(row=r, column=6).value,
            'pause': ws.cell(row=r, column=7).value,
            'how': ws.cell(row=r, column=8).value,
        }
    return ex

CATALOG = None

def build_catalog(ex):
    cat = []
    for name, v in ex.items():
        if isinstance(v.get('min'), (int, float)):
            cat.append((name, v['min']))
    return cat

def words(s):
    return [w for w in re.findall(r'[a-zäöüß]+', str(s).lower()) if len(w) >= 3]

def fuzzy_match(text, catalog, ex_full):
    """Findet den ähnlichsten Katalogeintrag (>=50% Wortüberdeckung) und
    liefert dessen komplette Übungssammlung-Zeile (min/sets/vol/pause)."""
    tw = words(text)
    if not tw:
        return None
    best, best_score = None, 0
    for name, _dauer in catalog:
        cw = words(name)
        if not cw:
            continue
        hits = sum(1 for c in cw if any(c in t or t in c for t in tw))
        score = hits / len(cw)
        if score > best_score:
            best_score, best = score, name
    if best_score >= 0.5 and best in ex_full:
        rec = ex_full[best]
        return {'name': best, 'min': rec.get('min'), 'sets': rec.get('sets'), 'vol': rec.get('vol'), 'pause': rec.get('pause')}
    return None

# --------------------------------------------------------------- Content --
# Feste Kategorien laut Floyd (immer alle 8, unabhängig von Einzel-/Gruppenplan):
CAT_ORDER = ['Theorie', 'Aufwärmen', 'Motorik', 'Technikfokus', 'Technik/Taktik', 'Physis Klettern', 'Athletik + Mentales', 'Spezial']

# Individuelle Einheitenplanung: Zeilen-Offsets relativ zum Session-Basiswert
# (base=4 für Session 1, base=19 für Session 2) — siehe Kopfzeilen-Dump.
IND_CAT_ROWS = {
    'Theorie': [3], 'Aufwärmen': [4], 'Motorik': [5], 'Technikfokus': [6],
    'Technik/Taktik': [7, 8], 'Physis Klettern': [9, 10], 'Athletik + Mentales': [11],
    'Spezial': [13],
}
IND_NOTIZ_OFFSETS = [12, 14]

# 30.08.: Übergangs-Fallback fürs alte Einzel-Sheet "Einheitenplanung" (ohne
# "26_27"). Floyd befüllt manche Wochen (z.B. KW36) noch dort statt im neuen
# Sheet — für Tage, die im neuen Sheet komplett leer sind, wird der Inhalt
# automatisch aus dem alten Sheet nachgezogen (1 Session statt 2, gleiche
# 8 Kategorien, Skill->Technik/Taktik, Physis Wand->Physis Klettern,
# Physis Boden->Athletik + Mentales, Besprechung->Theorie — Mapping wie beim
# Statistik-Saison-Parser für Gruppen bereits etabliert).
OLD_IND_CAT_ROWS = {
    'Theorie': [6], 'Aufwärmen': [7, 8], 'Motorik': [], 'Technikfokus': [9],
    'Technik/Taktik': [10, 11, 12], 'Physis Klettern': [13, 14, 15],
    'Athletik + Mentales': [16, 17, 18, 19, 20], 'Spezial': [21, 22, 23],
}
OLD_IND_NOTIZ_ROWS = [27]
OLD_IND_ORT_ROW = 5

def build_old_individual_index(wb):
    if 'Einheitenplanung' not in wb.sheetnames:
        return None
    ws = wb['Einheitenplanung']
    date_col = {}
    for col in range(2, ws.max_column + 1):
        dt = ws.cell(row=3, column=col).value
        if dt:
            date_col[dt.date()] = col
    return (ws, date_col)

def old_individual_day_session(old_idx, dt, catalog, ex, cats_counter):
    if not old_idx or not dt or dt not in old_idx[1]:
        return None
    ws_old, date_col = old_idx
    col = date_col[dt]
    ort = ws_old.cell(row=OLD_IND_ORT_ROW, column=col).value
    cats = []
    any_item = False
    for cat_name in CAT_ORDER:
        items = []
        for r in OLD_IND_CAT_ROWS[cat_name]:
            val = ws_old.cell(row=r, column=col).value
            if val:
                m = fuzzy_match(str(val), catalog, ex) if cat_name != 'Technikfokus' else None
                items.append({'ex': str(val), 'match': m})
                any_item = True
                cats_counter[cat_name] = cats_counter.get(cat_name, 0) + 1
        cats.append({'name': cat_name, 'items': items})
    notiz_parts = [str(ws_old.cell(row=r, column=col).value).strip()
                   for r in OLD_IND_NOTIZ_ROWS if ws_old.cell(row=r, column=col).value]
    notiz = ' / '.join(notiz_parts) if notiz_parts else None
    if not (ort or any_item or notiz):
        return None
    return {'name': 'Session 1', 'time': '', 'ort': ort, 'cats': cats, 'notiz': notiz}

# Gruppen-Einheitenplanung: absolute Zeilen (siehe Kopfzeilen-Dump U9).
# Korrektur 27.08.: "Physis Wand" (14,15) und "Physis Boden" (16,17) sind laut
# Floyd getrennte Kategorien (Physis Wand -> Physis Klettern, Physis Boden ->
# Athletik + Mentales) — vorher fälschlich beide in Physis Klettern zusammengefasst,
# wodurch Athletik + Mentales bei Gruppen immer leer war. Motorik gibt es in der
# Gruppenplanung nicht -> immer "-".
# Dieses Raster gilt für das ALTE "Einheitenplanung"-Sheet (Saison 25/26).
GRP_CAT_ROWS_OLD = {
    'Theorie': [8], 'Aufwärmen': [9, 10], 'Motorik': [], 'Technikfokus': [11],
    'Technik/Taktik': [12, 13], 'Physis Klettern': [14, 15], 'Athletik + Mentales': [16, 17],
    'Spezial': [18, 19],
}
GRP_NOTIZ_ROWS_OLD = [21, 22]
GRP_HEADER_ROWS_OLD = {'trainer': 5, 'zeit': 6, 'ort': 7}

# 28.08.: Floyd hat "Einheitenplanung 26_27" für Gruppen neu strukturiert -
# Uhrzeit/Trainer-Zeilen ergänzt und das Kategorienraster an die Einzelpläne
# angeglichen (jetzt inkl. echter Motorik-Zeile, Athletik nur noch 1 Zeile).
# Dadurch verschieben sich ALLE Zeilennummern gegenüber dem alten Sheet.
GRP_CAT_ROWS_NEW = {
    'Theorie': [9], 'Aufwärmen': [10], 'Motorik': [11], 'Technikfokus': [12],
    'Technik/Taktik': [13, 14], 'Physis Klettern': [15, 16], 'Athletik + Mentales': [17],
    'Spezial': [19],
}
GRP_NOTIZ_ROWS_NEW = [18, 20]
GRP_HEADER_ROWS_NEW = {'trainer': 7, 'zeit': 6, 'ort': 8}

# Rückwärtskompatible Aliase (Default = altes Raster, falls irgendwo ohne
# Schema-Auswahl referenziert).
GRP_CAT_ROWS = GRP_CAT_ROWS_OLD
GRP_NOTIZ_ROWS = GRP_NOTIZ_ROWS_OLD

# ------------------------------------------- Saison-Statistik (25/26 + 26/27) -
# Eigene Sheets ("Einheitenplanung" ohne 26_27-Zusatz) mit eigenem Zeilenraster
# (Skill/Physis Wand/Physis Boden statt Technikfokus/Technik-Taktik/Physis Klettern
# etc.) — das ist die abgeschlossene Saison 25/26, getrennt vom laufenden Live-Plan.
# Die Statistik kann zwischen Saison 25/26 (abgeschlossen) und 26/27 (laufend/
# kommend) umgeschaltet werden — Woche/Jahr/Benchmarks bleiben davon unberührt
# und zeigen weiterhin fortlaufend den Live-Stand ohne Saison-Umbruch.
SEASON_LABEL = '25/26'
SEASONS = ['25/26', '26/27']
SEASON_WEEKS = set([(2025, k) for k in range(38, 53)] + [(2026, k) for k in range(1, 38)])
SEASON_WEEKS_2627 = set([(2026, k) for k in range(38, 53)] + [(2027, k) for k in range(1, 38)])

IND_SEASON_CAT_ROWS = {
    'Theorie': [6], 'Aufwärmen': [7, 8], 'Motorik': [], 'Technikfokus': [9],
    'Technik/Taktik': [10, 11, 12], 'Physis Klettern': [13, 14, 15],
    'Athletik + Mentales': [16, 17, 18, 19, 20], 'Spezial': [21, 22, 23],
}
GRP_SEASON_CAT_ROWS = GRP_CAT_ROWS_OLD  # Saison 25/26 liest das alte Sheet/Raster

# Gruppen tracken keine echte Trainingsdauer (kein Dauer-Feld in der Gruppenplanung).
# Floyds Vorgabe: für die Statistik pauschal 2,75h pro echtem Trainingstag annehmen.
# Ein Trainingstag = mindestens eine der Kategorie-Zeilen unterhalb "Trainingsort"
# hat an dem Tag einen Eintrag (Notizen zählen nicht). Klar als Schätzung ausgewiesen,
# nicht als gemessene Dauer.
GROUP_EST_HOURS_PER_DAY = 2.75

# ------------------------------------------------------- Einheitenplanung --

def _next_iso_week(year, kw):
    """(year,kw) der unmittelbar folgenden ISO-Kalenderwoche - korrekt auch über
    Jahresgrenzen mit 52 vs. 53 Wochen hinweg (date.fromisocalendar statt naivem +1)."""
    d = date.fromisocalendar(year, kw, 1) + timedelta(days=7)
    c = d.isocalendar()
    return c[0], c[1]

def iso(d):
    if not d:
        return None
    c = d.isocalendar()
    return (c[0], c[1])

def norm_name(s):
    return re.sub(r'\s+', ' ', str(s or '').strip()).lower()

def load_forms_doku(path, valid_names):
    """Liest die Microsoft-Forms-Antworten-Excel 'Trainingsdoku KVV.xlsx'.
    Eine Zeile = eine Selbstauskunft (Athlet:in + Datum + Session). Namen
    werden auf die echte Kaderliste normalisiert (Groß/Kleinschreibung,
    doppelte Leerzeichen) gematcht; nicht zuordenbare Namen werden NICHT
    verworfen, sondern unter 'unmatched' zurückgegeben (kein Erfinden,
    aber auch kein stillschweigendes Verlieren von Daten)."""
    name_lookup = {norm_name(n): n for n in valid_names}
    by_name = {}
    unmatched = []
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception:
        return {}, ['<Datei nicht lesbar: ' + path + '>']
    ws = wb[wb.sheetnames[0]]
    headers = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    def col_idx(*needles):
        for i, h in enumerate(headers, start=1):
            if h and all(n.lower() in str(h).lower() for n in needles):
                return i
        return None
    c_name = col_idx('dein name')
    c_datum = col_idx('datum')
    c_sess = col_idx('session heute')
    c_dauer = col_idx('dauer der session')
    c_mot = col_idx('motivation')
    c_eb = col_idx('erschöpfung beginn')
    c_ee = col_idx('erschöpfung ende')
    c_fit = col_idx('fitness nach gefühl')
    c_um = col_idx('umgesetzt')
    c_notiz = col_idx('notizen')
    if not (c_name and c_datum):
        return {}, ['<Erwartete Spalten nicht gefunden in ' + path + '>']
    def parse_num(v):
        # Forms liefert Dezimalzahlen z.T. als String mit Komma (deutsches Format)
        if v is None or v == '':
            return None
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(str(v).strip().replace(',', '.'))
        except (ValueError, TypeError):
            return None
    for row in ws.iter_rows(min_row=2, values_only=True):
        raw_name = row[c_name - 1] if c_name else None
        dt = row[c_datum - 1] if c_datum else None
        if not raw_name or not dt:
            continue
        key = norm_name(raw_name)
        real_name = name_lookup.get(key)
        if not real_name:
            if str(raw_name).strip() not in unmatched:
                unmatched.append(str(raw_name).strip())
            continue
        dt_date = dt.date() if hasattr(dt, 'date') else dt
        sess_raw = row[c_sess - 1] if c_sess else None
        session = 1 if (sess_raw and '1' in str(sess_raw)) else (2 if (sess_raw and '2' in str(sess_raw)) else None)
        um_raw = row[c_um - 1] if c_um else None
        umsetzung = True if (um_raw and str(um_raw).strip().lower() == 'ja') else (False if (um_raw and str(um_raw).strip().lower() == 'nein') else None)
        rec = {
            'date': dt_date.isoformat(), 'session': session,
            'dur': parse_num(row[c_dauer - 1]) if c_dauer else None,
            'mot': row[c_mot - 1] if c_mot else None,
            'eb': row[c_eb - 1] if c_eb else None,
            'ee': row[c_ee - 1] if c_ee else None,
            'fitness': row[c_fit - 1] if c_fit else None,
            'umsetzung': umsetzung,
            'notiz': row[c_notiz - 1] if c_notiz else None,
        }
        by_name.setdefault(real_name, []).append(rec)
    return by_name, unmatched

def aggregate_doku_records(records):
    """Aus einer flachen Liste von Doku-Records (Forms und/oder Excel-Tage,
    jeweils mit optionalem dur=Trainingsdauer in h) die Kennzahlen fürs
    Statistik-Tab berechnen. Nichts wird erfunden: fehlende Werte fließen
    nicht in den jeweiligen Durchschnitt ein."""
    if not records:
        return None
    dur_recs = [r for r in records if r.get('dur') is not None]
    hrs = sum(r['dur'] for r in dur_recs)
    load_recs = [r for r in records if r.get('ee') is not None and r.get('dur') is not None]
    load_sum = sum(r['ee'] * r['dur'] for r in load_recs)
    dates_with_doku = set(r['date'] for r in records if r.get('date'))
    mot_vals = [r['mot'] for r in records if r.get('mot') is not None]
    eb_vals = [r['eb'] for r in records if r.get('eb') is not None]
    fit_vals = [r['fitness'] for r in records if r.get('fitness') is not None]
    um_yes = sum(1 for r in records if r.get('umsetzung') is True)
    um_no = sum(1 for r in records if r.get('umsetzung') is False)
    return {
        'hrsSaison': round(hrs, 2) if dur_recs else None,
        'dokuDays': len(dates_with_doku),
        'loadSaison': round(load_sum, 1) if load_recs else None,
        'avgLoad': round(load_sum / len(load_recs), 2) if load_recs else None,
        'avgMotivation': round(sum(mot_vals) / len(mot_vals), 2) if mot_vals else None,
        'avgErschoepfungBeginn': round(sum(eb_vals) / len(eb_vals), 2) if eb_vals else None,
        'avgFitness': round(sum(fit_vals) / len(fit_vals), 2) if fit_vals else None,
        'pctUmsetzung': round(100 * um_yes / (um_yes + um_no), 1) if (um_yes + um_no) > 0 else None,
    }

def aggregate_group_doku_season(athlete_names, forms_by_athlete):
    """Gruppen-Statistik (Saison) aus den rohen Forms-Records aller Athlet:innen
    einer Gruppe. Trainingsdauer/Load bleiben None, solange die Forms keine
    Trainingsdauer erfassen (kein Erfinden) - das gilt aktuell für alle Gruppen,
    da es für U15 I/II auch keine Einzelplan-Excel mit Dauer-Zellen gibt."""
    recs = []
    for n in athlete_names:
        recs.extend(forms_by_athlete.get(n, []))
    if not recs:
        return None
    dur_recs = [r for r in recs if r.get('dur') is not None]
    load_recs = [r for r in recs if r.get('ee') is not None and r.get('dur') is not None]
    mot_vals = [r['mot'] for r in recs if r.get('mot') is not None]
    return {
        'avgMotivation': round(sum(mot_vals) / len(mot_vals), 2) if mot_vals else None,
        'avgTrainingsdauer': round(sum(r['dur'] for r in dur_recs) / len(dur_recs), 2) if dur_recs else None,
        'avgLoad': round(sum(r['ee'] * r['dur'] for r in load_recs) / len(load_recs), 2) if load_recs else None,
        'nAthletesWithDoku': len(set(n for n in athlete_names if forms_by_athlete.get(n))),
    }

def aggregate_group_doku_weeks(athlete_names, forms_by_athlete):
    """Wie aggregate_group_doku_season, aber pro (year,kw) Woche gebucketed -
    für 'Woche Kompakt' bei Gruppenplänen. Liefert {(year,kw): {...}}."""
    by_week = {}
    for n in athlete_names:
        for r in forms_by_athlete.get(n, []):
            dt = r.get('date')
            if not dt:
                continue
            try:
                yk = iso(date.fromisoformat(dt))
            except Exception:
                continue
            if not yk:
                continue
            by_week.setdefault(yk, []).append(r)
    out = {}
    for yk, recs in by_week.items():
        dur_recs = [r for r in recs if r.get('dur') is not None]
        load_recs = [r for r in recs if r.get('ee') is not None and r.get('dur') is not None]
        mot_vals = [r['mot'] for r in recs if r.get('mot') is not None]
        out[yk] = {
            'avgMotivation': round(sum(mot_vals) / len(mot_vals), 2) if mot_vals else None,
            'avgTrainingsdauer': round(sum(r['dur'] for r in dur_recs) / len(dur_recs), 2) if dur_recs else None,
            'avgLoad': round(sum(r['ee'] * r['dur'] for r in load_recs) / len(load_recs), 2) if load_recs else None,
        }
    return out

def parse_individual(path, athlete_name, catalog, ex, cats_counter, forms_records=None):
    wb = openpyxl.load_workbook(path, data_only=True)
    sheetname = None
    for cand in ['Einheitenplanung 26_27']:
        if cand in wb.sheetnames:
            sheetname = cand
            break
    if not sheetname:
        return {}, None
    ws = wb[sheetname]
    maxc = ws.max_column
    row_labels = {r: ws.cell(row=r, column=1).value for r in range(1, 41)}
    weeks = {}   # (year,kw) -> {days:[...], span, source}
    week_stats = {}  # (year,kw) -> accumulate load/hrs/rpe/eb/mot/fit/umsetzung/days/planDays
    old_idx = build_old_individual_index(wb)
    forms_by_date = {}
    for r in (forms_records or []):
        forms_by_date.setdefault(r['date'], []).append(r)
    all_doku_records = []

    c = 2
    while c <= maxc:
        kw_val = ws.cell(row=1, column=c).value
        if not isinstance(kw_val, (int, float)):
            c += 1
            continue
        block_dates = []
        for i in range(7):
            dt = ws.cell(row=3, column=c + i).value
            block_dates.append(dt.date() if dt else None)
        first_dt = next((d for d in block_dates if d), None)
        if not first_dt:
            c += 7
            continue
        yk = iso(first_dt)
        days = []
        for i in range(7):
            col = c + i
            dow = ws.cell(row=2, column=col).value
            dt = block_dates[i]
            sessions = []
            for sess_num, base in [(1, 4), (2, 19)]:
                ort = ws.cell(row=base + 2, column=col).value
                cats = []
                any_item = False
                for cat_name in CAT_ORDER:
                    items = []
                    for off in IND_CAT_ROWS[cat_name]:
                        val = ws.cell(row=base + off, column=col).value
                        if val:
                            m = fuzzy_match(str(val), catalog, ex) if cat_name != 'Technikfokus' else None
                            items.append({'ex': str(val), 'match': m})
                            any_item = True
                            cats_counter[cat_name] = cats_counter.get(cat_name, 0) + 1
                    cats.append({'name': cat_name, 'items': items})
                notiz_parts = [str(ws.cell(row=base + off, column=col).value).strip()
                               for off in IND_NOTIZ_OFFSETS if ws.cell(row=base + off, column=col).value]
                notiz = ' / '.join(notiz_parts) if notiz_parts else None
                if ort or any_item or notiz:
                    sessions.append({'name': f'Session {sess_num}', 'time': '', 'ort': ort, 'cats': cats, 'notiz': notiz})
            if not sessions:
                fallback = old_individual_day_session(old_idx, dt, catalog, ex, cats_counter)
                if fallback:
                    sessions.append(fallback)
            mot_x = ws.cell(row=35, column=col).value
            eb_x = ws.cell(row=36, column=col).value
            ee_x = ws.cell(row=37, column=col).value
            d1 = ws.cell(row=38, column=col).value
            d2 = ws.cell(row=39, column=col).value
            um_x = ws.cell(row=40, column=col).value
            um_x_bool = True if (um_x and str(um_x).strip().lower() == 'ja') else (False if (um_x and str(um_x).strip().lower() == 'nein') else None)
            d1n = float(d1) if isinstance(d1, (int, float)) else None
            d2n = float(d2) if isinstance(d2, (int, float)) else None
            date_str = dt.isoformat() if dt else None
            day_forms = forms_by_date.get(date_str, []) if date_str else []

            day_records = []  # merged Doku-Records fuer diesen Tag (Forms bevorzugt, sonst Excel)
            if day_forms:
                for fr in day_forms:
                    # Trainingsdauer: bevorzugt direkt aus dem Forms (seit 04.09. abgefragt),
                    # sonst Fallback auf die Excel-Zellen Dauer S1/S2 (kein Erfinden).
                    dur_excel = d1n if fr.get('session') == 1 else (d2n if fr.get('session') == 2 else None)
                    dur = fr.get('dur') if fr.get('dur') is not None else dur_excel
                    day_records.append({**fr, 'dur': dur, 'source': 'forms'})
            elif any(v is not None for v in (mot_x, eb_x, ee_x, d1, d2, um_x)):
                dur = (d1n or 0) + (d2n or 0)
                day_records.append({
                    'date': date_str, 'session': None, 'mot': mot_x, 'eb': eb_x, 'ee': ee_x,
                    'fitness': None, 'umsetzung': um_x_bool, 'notiz': None,
                    'dur': dur if dur else None, 'source': 'excel',
                })

            doku = None
            if day_records:
                mots = [r['mot'] for r in day_records if r.get('mot') is not None]
                ebs = [r['eb'] for r in day_records if r.get('eb') is not None]
                ees = [r['ee'] for r in day_records if r.get('ee') is not None]
                fits = [r['fitness'] for r in day_records if r.get('fitness') is not None]
                notizen = [str(r['notiz']).strip() for r in day_records if r.get('notiz')]
                ums = [r['umsetzung'] for r in day_records if r.get('umsetzung') is not None]
                doku = {
                    'mot': round(sum(mots) / len(mots), 1) if mots else None,
                    'eb': round(sum(ebs) / len(ebs), 1) if ebs else None,
                    'ee': round(sum(ees) / len(ees), 1) if ees else None,
                    'fitness': round(sum(fits) / len(fits), 1) if fits else None,
                    'd1': d1, 'd2': d2,
                    'umsetzung': (False if False in ums else (True if ums else None)),
                    'notiz': ' / '.join(notizen) if notizen else None,
                    'sessions': [{'session': r.get('session'), 'mot': r.get('mot'), 'eb': r.get('eb'),
                                  'ee': r.get('ee'), 'fitness': r.get('fitness'), 'umsetzung': r.get('umsetzung'),
                                  'notiz': r.get('notiz'), 'source': r.get('source')} for r in day_records],
                }
                all_doku_records.extend(day_records)
                stat = week_stats.setdefault(yk, {'load': 0, 'hrs': 0, 'rpe_sum': 0, 'rpe_n': 0, 'mot_sum': 0, 'mot_n': 0,
                                                   'eb_sum': 0, 'eb_n': 0, 'fit_sum': 0, 'fit_n': 0, 'um_yes': 0, 'um_n': 0,
                                                   'days': 0, 'planDays': 0})
                for r in day_records:
                    if r.get('dur') is not None:
                        stat['hrs'] += r['dur']
                        if r.get('ee') is not None:
                            stat['load'] += r['ee'] * r['dur']
                    if r.get('ee') is not None:
                        stat['rpe_sum'] += r['ee']; stat['rpe_n'] += 1
                    if r.get('mot') is not None:
                        stat['mot_sum'] += r['mot']; stat['mot_n'] += 1
                    if r.get('eb') is not None:
                        stat['eb_sum'] += r['eb']; stat['eb_n'] += 1
                    if r.get('fitness') is not None:
                        stat['fit_sum'] += r['fitness']; stat['fit_n'] += 1
                    if r.get('umsetzung') is True:
                        stat['um_yes'] += 1; stat['um_n'] += 1
                    elif r.get('umsetzung') is False:
                        stat['um_n'] += 1
                stat['days'] += 1
            if sessions:
                stat = week_stats.setdefault(yk, {'load': 0, 'hrs': 0, 'rpe_sum': 0, 'rpe_n': 0, 'mot_sum': 0, 'mot_n': 0,
                                                   'eb_sum': 0, 'eb_n': 0, 'fit_sum': 0, 'fit_n': 0, 'um_yes': 0, 'um_n': 0,
                                                   'days': 0, 'planDays': 0})
                stat['planDays'] += 1
            days.append({
                'dow': dow, 'dom': dt.strftime('%d.%m.') if dt else '?', 'date': date_str,
                'ort': next((s['ort'] for s in sessions if s.get('ort')), None),
                'sessions': sessions, 'doku': doku, 'notiz': None,
            })
        span = f"{block_dates[0].strftime('%d.%m.')} – {block_dates[-1].strftime('%d.%m.%Y')}" if block_dates[0] and block_dates[-1] else ''
        weeks[f'{yk[0]}-{yk[1]}'] = {'days': days, 'span': span, 'year': yk[0], 'kw': yk[1]}
        c += 7

    weeks_out = []
    for yk, st in sorted(week_stats.items()):
        weeks_out.append({
            'year': yk[0], 'kw': yk[1],
            'load': round(st['load'], 1), 'hrs': round(st['hrs'], 2),
            'rpe': round(st['rpe_sum'] / st['rpe_n'], 2) if st['rpe_n'] else None,
            'mot': round(st['mot_sum'] / st['mot_n'], 2) if st['mot_n'] else None,
            'eb': round(st['eb_sum'] / st['eb_n'], 2) if st['eb_n'] else None,
            'fit': round(st['fit_sum'] / st['fit_n'], 2) if st['fit_n'] else None,
            'umPct': round(100 * st['um_yes'] / st['um_n'], 1) if st['um_n'] else None,
            'days': st['days'],
            'planDays': st['planDays'],
        })
    doku_stats = aggregate_doku_records(all_doku_records)
    if doku_stats is not None:
        doku_stats['planDaysSaison'] = sum(w['planDays'] for w in weeks_out)
    return weeks, weeks_out, doku_stats

# Trainingsort-Zellfarbe -> Sessionsart, 1:1 wie von Floyd vorgegeben (dieselben
# Farbcodes wie im Gruppen-Jahresplan "Fokus": Grün=Lead, Blau=Bouldern,
# Gelb=Speed). Kein Erfinden: fehlt die Farbe, bleibt ortType None.
ORT_COLOR_MAP = {'#92D050': 'Lead', '#00B0F0': 'Bouldern', '#FFFF00': 'Speed'}

def parse_group(path, sheet_candidates, catalog, ex, cats_counter):
    wb = openpyxl.load_workbook(path, data_only=True)
    sheetname = None
    for cand in sheet_candidates:
        for sn in wb.sheetnames:
            if sn.strip() == cand:
                sheetname = sn
                break
        if sheetname:
            break
    if not sheetname:
        return {}, sheetname
    ws = wb[sheetname]
    maxc = ws.max_column
    # 28.08.: Floyd hat "Einheitenplanung 26_27" umgebaut (Uhrzeit/Trainer neu,
    # Kategorienraster verschoben) - Zeilenraster hängt daher vom Sheet ab.
    is_new = sheetname.strip() == 'Einheitenplanung 26_27'
    cat_rows = GRP_CAT_ROWS_NEW if is_new else GRP_CAT_ROWS_OLD
    notiz_rows = GRP_NOTIZ_ROWS_NEW if is_new else GRP_NOTIZ_ROWS_OLD
    hdr = GRP_HEADER_ROWS_NEW if is_new else GRP_HEADER_ROWS_OLD
    weeks = {}
    col = 2
    while col <= maxc:
        dt_cell = ws.cell(row=3, column=col).value
        if not dt_cell:
            col += 1
            continue
        dt = dt_cell.date() if hasattr(dt_cell, 'date') else None
        if not dt:
            col += 1
            continue
        yk = iso(dt)
        key = f'{yk[0]}-{yk[1]}'
        wk_entry = weeks.setdefault(key, {'days': [], 'year': yk[0], 'kw': yk[1]})
        dow = ws.cell(row=2, column=col).value
        trainer = ws.cell(row=hdr['trainer'], column=col).value
        zeit = ws.cell(row=hdr['zeit'], column=col).value
        ort_cell = ws.cell(row=hdr['ort'], column=col)
        ort = ort_cell.value
        ort_color = get_fill_hex(ort_cell)
        ort_type = ORT_COLOR_MAP.get(ort_color) if ort_color else None
        cats = []
        any_item = False
        for cat_name in CAT_ORDER:
            items = []
            for r in cat_rows[cat_name]:
                val = ws.cell(row=r, column=col).value
                if val:
                    m = fuzzy_match(str(val), catalog, ex) if cat_name != 'Technikfokus' else None
                    items.append({'ex': str(val), 'match': m})
                    any_item = True
                    cats_counter[cat_name] = cats_counter.get(cat_name, 0) + 1
            cats.append({'name': cat_name, 'items': items})
        notiz_parts = [str(ws.cell(row=r, column=col).value).strip() for r in notiz_rows if ws.cell(row=r, column=col).value]
        notiz = ' / '.join(notiz_parts) if notiz_parts else None
        sessions = []
        if ort or trainer or any_item or notiz:
            sessions.append({'name': 'Einheit', 'time': str(zeit) if zeit else '', 'trainer': trainer, 'ort': ort, 'cats': cats, 'notiz': notiz})
        wk_entry['days'].append({
            'dow': dow, 'dom': dt.strftime('%d.%m.'), 'date': dt.isoformat(),
            'ort': ort, 'ortType': ort_type, 'trainer': trainer, 'zeit': str(zeit) if zeit else None,
            'sessions': sessions, 'doku': None, 'notiz': None,
        })
        col += 1
    for key, wk_entry in weeks.items():
        ds = [d['date'] for d in wk_entry['days'] if d['date']]
        if ds:
            a, b = min(ds), max(ds)
            wk_entry['span'] = f"{date.fromisoformat(a).strftime('%d.%m.')} – {date.fromisoformat(b).strftime('%d.%m.%Y')}"
        else:
            wk_entry['span'] = ''
    return weeks, sheetname

def _find_season_sheet(wb, base_name):
    for cand in [base_name, base_name + ' ', base_name.strip()]:
        if cand in wb.sheetnames:
            return cand
    for sn in wb.sheetnames:
        if sn.strip().lower() == base_name.lower():
            return sn
    return None

def parse_season_individual(path, season_weeks=None):
    """Saison 25/26 aus dem alten (nicht-26_27) Einheitenplanung-Sheet:
    eigenes Zeilenraster (Skill/Physis Wand/Physis Boden), zählt nur echte
    Zelleneinträge pro Kategorie, plus Load/RPE/Dauer/Fitness pro Woche
    (nur dort wo die Zellen wirklich gefüllt sind — kein Erfinden)."""
    season_weeks = season_weeks if season_weeks is not None else SEASON_WEEKS
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception:
        return None
    sheetname = _find_season_sheet(wb, 'Einheitenplanung')
    if not sheetname:
        return None
    ws = wb[sheetname]
    maxc = ws.max_column
    cat_counts = {c: 0 for c in CAT_ORDER}
    week_stats = {}
    col = 2
    while col <= maxc:
        kw_val = ws.cell(row=1, column=col).value
        if not isinstance(kw_val, (int, float)):
            col += 1
            continue
        kw = int(kw_val)
        stat = {'load': 0.0, 'hrs': 0.0, 'rpe_sum': 0.0, 'rpe_n': 0, 'fit_sum': 0.0, 'fit_n': 0, 'days': 0,
                'um_yes': 0, 'um_n': 0, 'planDays': 0}
        week_year = None
        any_real_day = False
        for i in range(7):
            c = col + i
            dt_cell = ws.cell(row=3, column=c).value
            dt = dt_cell.date() if hasattr(dt_cell, 'date') else None
            if not dt:
                continue
            yk = iso(dt)
            if yk not in season_weeks:
                continue
            week_year = yk[0]
            notiz = ws.cell(row=27, column=c).value
            is_example = bool(notiz) and 'beispiel' in str(notiz).lower()
            if is_example:
                continue
            any_real_day = True
            day_has_content = False
            for cat_name, rows in IND_SEASON_CAT_ROWS.items():
                for r in rows:
                    if ws.cell(row=r, column=c).value:
                        cat_counts[cat_name] += 1
                        day_has_content = True
            if day_has_content:
                stat['planDays'] += 1
            rpe = ws.cell(row=25, column=c).value
            dauer = ws.cell(row=26, column=c).value
            fit = ws.cell(row=28, column=c).value
            load = ws.cell(row=32, column=c).value
            done = ws.cell(row=24, column=c).value
            done_bool = True if (done and str(done).strip().lower() in ('ja', 'yes', 'true', '1')) else (
                False if (done and str(done).strip().lower() in ('nein', 'no', 'false', '0')) else None)
            if isinstance(dauer, (int, float)):
                stat['hrs'] += dauer
            if isinstance(load, (int, float)):
                stat['load'] += load
            elif isinstance(rpe, (int, float)) and isinstance(dauer, (int, float)):
                stat['load'] += rpe * dauer
            if isinstance(rpe, (int, float)):
                stat['rpe_sum'] += rpe
                stat['rpe_n'] += 1
            if isinstance(fit, (int, float)):
                stat['fit_sum'] += fit
                stat['fit_n'] += 1
            if done_bool is True:
                stat['um_yes'] += 1; stat['um_n'] += 1
            elif done_bool is False:
                stat['um_n'] += 1
            if done or isinstance(rpe, (int, float)) or isinstance(dauer, (int, float)):
                stat['days'] += 1
        if any_real_day and week_year is not None:
            week_stats[(week_year, kw)] = stat
        col += 7

    weeks_out = []
    for (y, kw), st in sorted(week_stats.items()):
        weeks_out.append({
            'year': y, 'kw': kw,
            'load': round(st['load'], 1) if st['load'] else (0 if st['days'] else None),
            'hrs': round(st['hrs'], 2),
            'rpe': round(st['rpe_sum'] / st['rpe_n'], 2) if st['rpe_n'] else None,
            'mot': None, 'eb': None,
            'fit': round(st['fit_sum'] / st['fit_n'], 2) if st['fit_n'] else None,
            'umPct': round(100 * st['um_yes'] / st['um_n'], 1) if st['um_n'] else None,
            'days': st['days'],
            'planDays': st['planDays'],
        })
    hrs_sum = sum(w['hrs'] for w in weeks_out)
    load_vals = [w['load'] for w in weeks_out if w.get('load') is not None]
    fit_vals = [w['fit'] for w in weeks_out if w.get('fit') is not None]
    dokudays_sum = sum(w['days'] for w in weeks_out)
    um_yes_total = sum(st['um_yes'] for st in week_stats.values())
    um_n_total = sum(st['um_n'] for st in week_stats.values())
    doku_stats = {
        'hrsSaison': round(hrs_sum, 2) if weeks_out else None,
        'dokuDays': dokudays_sum,
        'planDaysSaison': sum(w['planDays'] for w in weeks_out),
        'loadSaison': round(sum(load_vals), 1) if load_vals else None,
        'avgLoad': round(sum(load_vals) / dokudays_sum, 2) if (load_vals and dokudays_sum) else None,
        'avgMotivation': None,  # in der alten Saison 25/26 nicht erfasst
        'avgErschoepfungBeginn': None,  # dito
        'avgFitness': round(sum(fit_vals) / len(fit_vals), 2) if fit_vals else None,
        'pctUmsetzung': round(100 * um_yes_total / um_n_total, 1) if um_n_total else None,
    } if weeks_out else None
    return {
        'catCounts': [{'name': c, 'count': cat_counts[c]} for c in CAT_ORDER],
        'weeks': weeks_out,
        'sheet': sheetname,
        'doku': doku_stats,
    }

def build_group_season_stats_from_weeks(weeks, season_weeks, sheet_label):
    """Saison 26/27 für Gruppen: direkt aus den bereits per parse_group()
    geparsten Einheitenplanung-26_27-Daten (neues Zeilenraster inkl. Motorik)
    aggregiert, statt nochmal mit dem alten Sheet/Raster zu parsen."""
    cat_counts = {c: 0 for c in CAT_ORDER}
    training_days = 0
    for wk in weeks.values():
        if (wk.get('year'), wk.get('kw')) not in season_weeks:
            continue
        for day in wk.get('days', []):
            day_has_entry = False
            for sess in day.get('sessions', []):
                for cat in sess.get('cats', []):
                    n = len(cat.get('items') or [])
                    if n:
                        cat_counts[cat['name']] = cat_counts.get(cat['name'], 0) + n
                        day_has_entry = True
            if day_has_entry:
                training_days += 1
    if training_days == 0 and all(v == 0 for v in cat_counts.values()):
        return None
    return {
        'catCounts': [{'name': c, 'count': cat_counts.get(c, 0)} for c in CAT_ORDER],
        'weeks': [],
        'sheet': sheet_label,
        'trainingDays': training_days,
        'estHoursPerDay': GROUP_EST_HOURS_PER_DAY,
        'estHours': round(training_days * GROUP_EST_HOURS_PER_DAY, 1),
    }

def parse_season_group(path, season_weeks=None):
    """Saison für Gruppen: dasselbe Sheet wie der Live-Plan (Gruppen haben
    kein separates 26_27-Sheet), nur auf die jeweilige Saison gefiltert.
    Kein Load möglich (keine RPE/Dauer-Zeilen in der Gruppenplanung)."""
    season_weeks = season_weeks if season_weeks is not None else SEASON_WEEKS
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception:
        return None
    sheetname = _find_season_sheet(wb, 'Einheitenplanung')
    if not sheetname:
        return None
    ws = wb[sheetname]
    maxc = ws.max_column
    cat_counts = {c: 0 for c in CAT_ORDER}
    training_days = 0
    all_cat_rows = sorted(set(r for rows in GRP_SEASON_CAT_ROWS.values() for r in rows))
    for col in range(2, maxc + 1):
        dt_cell = ws.cell(row=3, column=col).value
        dt = dt_cell.date() if hasattr(dt_cell, 'date') else None
        if not dt:
            continue
        if iso(dt) not in season_weeks:
            continue
        day_has_entry = False
        for cat_name, rows in GRP_SEASON_CAT_ROWS.items():
            for r in rows:
                if ws.cell(row=r, column=col).value:
                    cat_counts[cat_name] += 1
        for r in all_cat_rows:
            if ws.cell(row=r, column=col).value:
                day_has_entry = True
                break
        if day_has_entry:
            training_days += 1
    return {
        'catCounts': [{'name': c, 'count': cat_counts[c]} for c in CAT_ORDER],
        'weeks': [],
        'sheet': sheetname,
        'trainingDays': training_days,
        'estHoursPerDay': GROUP_EST_HOURS_PER_DAY,
        'estHours': round(training_days * GROUP_EST_HOURS_PER_DAY, 1),
    }

# -------------------------------------------------------------- Benchmarks --

BENCH_STRUCTURE = [
    ('Technik+Taktik', 'mitlaufend', [
        'Rotpunkt K1', 'Onsight K1', 'Rotpunkt Fels', 'Onsight Fels',
        'Kilterboard Max', 'Kilterboard Flash',
    ]),
    ('Physisches Klettertraining', 'mitlaufend', ['Anzahl Aufbauboulder Sessions']),
]
# Weitere Rubriken/Items (Kilterboard Base, Steinblock DB Max, Motorik, Athletik)
# sind bewusst ausgeblendet (Floyd, 07.09.) — kommen erst nach und nach zurück,
# sobald echte Werte da sind und er sie für sinnvoll hält.

def load_bench_source():
    """Liest die alte Einzeldatei Zusatzinfos/Benchmarks.xlsx (nur Adrian, historisch
    gepflegt) als Fallback für Items, zu denen das neue Forms noch keinen Wert hat."""
    try:
        wb = openpyxl.load_workbook(BASE + 'Zusatzinfos/Benchmarks.xlsx', data_only=True)
    except Exception:
        return {}
    ws = wb['Tabelle1']
    vals = {}
    for r in range(2, ws.max_row + 1):
        item = ws.cell(row=r, column=3).value
        v = ws.cell(row=r, column=4).value
        if item:
            key = norm(re.sub(r'^[-\d.\s]+', '', str(item)))
            vals[key] = v
    return vals

def load_bench_source_forms(path, valid_names):
    """Liest die Microsoft-Forms-Antworten-Excel 'Benchmark Update.xlsx'. Eine Zeile
    = eine Selbstauskunft (Athlet:in + Datum, meist nur wenige Felder ausgefüllt —
    alles andere bleibt leer). Pro Athlet:in/Item wird der Wert aus der Zeile mit dem
    NEUESTEN Datum übernommen (leere Zellen zählen nicht, überschreiben also keinen
    älteren echten Wert). Namen werden wie bei der Doku auf die Kaderliste gematcht;
    nicht zuordenbare Namen gehen nicht verloren, sondern kommen in 'unmatched'."""
    name_lookup = {norm_name(n): n for n in valid_names}
    by_athlete = {}  # name -> {item_key: (date, value)}
    unmatched = []
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception:
        return {}, ['<Datei nicht lesbar: ' + path + '>']
    ws = wb[wb.sheetnames[0]]
    headers = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    def col_idx(*needles):
        for i, h in enumerate(headers, start=1):
            if h and all(n.lower() in str(h).lower() for n in needles):
                return i
        return None
    c_name = col_idx('dein name')
    c_datum = col_idx('datum')
    if not (c_name and c_datum):
        return {}, ['<Erwartete Spalten nicht gefunden in ' + path + '>']
    # Item-Spalten: alle BENCH_STRUCTURE-Items (auch ausgeblendete) gegen die
    # Forms-Überschriften matchen, damit später wieder eingeblendete Items
    # rückwirkend die schon gesammelten Werte haben.
    all_items = ['Rotpunkt K1', 'Onsight K1', 'Rotpunkt Fels', 'Onsight Fels', 'Kilterboard Max',
                 'Kilterboard Flash', 'Kilterboard Base', 'Steinblock DB Max', 'Anzahl Bälle Jonglieren',
                 'Alternate Wall Toss', 'Doppellänge Max', '90° Block Einarmig', 'Half Crimp langer Arm',
                 'PinchPower', 'Einarmer Ja/Nein', 'Klimmzug Kraftausdauer', 'Spagat Seite Abstand Wand',
                 'Jump and Reach Test', 'Handstand frei in Sekunden']
    item_cols = {}
    for it in all_items:
        idx = col_idx(it.lower())
        if idx:
            item_cols[it] = idx
    for row in ws.iter_rows(min_row=2, values_only=True):
        raw_name = row[c_name - 1] if c_name else None
        dt = row[c_datum - 1] if c_datum else None
        if not raw_name or not dt:
            continue
        key = norm_name(raw_name)
        real_name = name_lookup.get(key)
        if not real_name:
            if str(raw_name).strip() not in unmatched:
                unmatched.append(str(raw_name).strip())
            continue
        dt_date = dt.date() if hasattr(dt, 'date') else dt
        athlete_vals = by_athlete.setdefault(real_name, {})
        for it, idx in item_cols.items():
            v = row[idx - 1]
            if v is None or str(v).strip() == '':
                continue
            prev = athlete_vals.get(norm(it))
            if prev is None or dt_date >= prev[0]:
                athlete_vals[norm(it)] = (dt_date, v)
    # auf reine {item_key: value} verkürzen
    out = {name: {k: v[1] for k, v in items.items()} for name, items in by_athlete.items()}
    return out, unmatched

def build_bench_for(athlete_name, forms_vals, legacy_vals, aufbau_count=None):
    cats_out = []
    any_val = False
    for cat_name, rhythm, items in BENCH_STRUCTURE:
        its = []
        for it in items:
            auto = 'Sessions' in it
            if auto:
                v = aufbau_count
            else:
                v = (forms_vals or {}).get(norm(it))
                if v is None:
                    v = (legacy_vals or {}).get(norm(it))
            if v is not None:
                any_val = True
            its.append({'k': it, 'v': v if v is not None else None, 'p': None, 't': 0, 'auto': auto})
        cats_out.append({'name': cat_name, 'rhythm': rhythm, 'items': its})
    if not any_val:
        return None
    return {'stand': date.today().strftime('%d.%m.%Y'), 'cats': cats_out}

def count_aufbau_sessions(weeks):
    """Zählt reale Vorkommen von 'Aufbau Boulder'-Übungen (gematcht über die
    Übungssammlung) über alle Wochen einer Athletin/eines Athleten."""
    n = 0
    for wk in weeks.values():
        for day in wk['days']:
            for sess in day['sessions']:
                for cat in sess.get('cats', []):
                    for it in cat['items']:
                        m = it.get('match')
                        if m and str(m.get('name', '')).startswith('Aufbau Boulder'):
                            n += 1
    return n

# ---------------------------------------------------------------- Kalender --

AGE_CLASSES = ['U9', 'U11', 'U13', 'U15', 'U17', 'U19']

def load_gk():
    wb = openpyxl.load_workbook(BASE + 'Zusatzinfos/Gesamtkalender 2025_2026 – aktuell.xlsx', data_only=True)
    ws = wb['MOAP']
    rows = []
    for r in range(3, 17):
        label = ws.cell(row=r, column=1).value
        if label:
            rows.append((r, str(label)))
    weeks_range = {}
    for c in range(4, ws.max_column + 1):
        rng = ws.cell(row=2, column=c).value
        if not rng:
            continue
        weeks_range[c] = str(rng)

    def parse_start_date(rng, ref_year):
        m = re.findall(r'(\d+)\.(\d+)?\.?', rng.split('-')[0])
        try:
            day = int(re.search(r'^(\d+)\.', rng).group(1))
            monthmatch = re.search(r'\.(\d+)\.', rng.split('-')[0])
            month = int(monthmatch.group(1)) if monthmatch else None
            return day, month
        except Exception:
            return None, None

    gk = {a: {} for a in AGE_CLASSES}
    cur_year = 2025
    last_month = 8
    for c, rng in weeks_range.items():
        day, month = parse_start_date(rng, cur_year)
        if month is not None:
            if month < last_month - 6:
                cur_year += 1
            last_month = month
        try:
            dt = date(cur_year, month, day) if month and day else None
        except Exception:
            dt = None
        yk = iso(dt) if dt else None
        for (r, label) in rows:
            val = ws.cell(row=r, column=c).value
            if not val:
                continue
            m = re.findall(r'U(9|11|13|15|17|19)', label)
            classes = [f'U{x}' for x in m] if m else AGE_CLASSES[:]
            for cl in classes:
                if yk:
                    key = f'{yk[0]}-{yk[1]}'
                    entry = gk[cl].setdefault(key, {'d': rng, 'items': []})
                    entry['items'].append({'c': label, 't': str(val)})
    return gk

# ------------------------------------------------------------ Jahresplanung --

# Bekannte kurze Phasen-Schlagworte -> normalisierte Kategorie (nur diese werden
# im Phasen-Ribbon eingefärbt; lange Freitext-Beschreibungen bleiben unfarbig
# und werden nur als Text angezeigt, statt sie zu erraten / zu erfinden).
def normalize_phase(raw):
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    low = s.lower()
    if low.startswith('max/sk') or low.startswith('max / sk'):
        return 'Max/SK'
    if low.startswith('fels + basis') or low.startswith('fels+basis'):
        return 'Fels + Basis'
    if low.startswith('frei/pause') or low.startswith('frei / pause') or low == 'pause':
        return 'Pause'
    if low.startswith('basis'):
        return 'Basis'
    if low.startswith('aufbau'):
        return 'Aufbau'
    if low.startswith('skill'):
        return 'Skill'
    if low.startswith('fels'):
        return 'Fels'
    if low.startswith('max'):
        return 'Max'
    if low == 'sk':
        return 'SK'
    if low == 'ka':
        return 'KA'
    if low == 'wk':
        return 'WK'
    return None

def get_fill_hex(cell):
    """Echte Zellfarbe (ARGB) als '#rrggbb' oder None (keine/transparente Füllung)."""
    try:
        fg = cell.fill.fgColor
        rgb = fg.rgb if fg else None
    except Exception:
        rgb = None
    if not isinstance(rgb, str) or len(rgb) != 8:
        return None
    if rgb[:2] == '00':
        return None
    return '#' + rgb[2:]

def parse_jahresplanung(path):
    """Liest den echten Jahresplan (Phase/Trainingsumfang/WK-Termine Boulder+Lead/
    Fels/Schulferien/Sonstiges) aus dem Reiter 'Jahresplanung' einer Athlet:innen-
    Excel. Zeilen-Offsets variieren leicht pro Datei, daher werden sie über die
    Beschriftung in Spalte A gefunden statt über feste Zeilennummern."""
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception:
        return None
    if 'Jahresplanung' not in wb.sheetnames:
        return None
    ws = wb['Jahresplanung']

    kw_row = None
    for r in range(1, 10):
        v = ws.cell(row=r, column=1).value
        if v and str(v).strip().lower().startswith('kalenderwoche'):
            kw_row = r
            break
    if kw_row is None:
        return None
    phase_row = kw_row + 1
    umfang_row = kw_row + 2

    wk_row = None
    for r in range(umfang_row + 1, umfang_row + 8):
        v = ws.cell(row=r, column=1).value
        if v and str(v).strip().lower().startswith('wk termine'):
            wk_row = r
            break
    if wk_row is None:
        return None
    bouldern_row = wk_row
    lead_row = wk_row + 1
    fels_row = lead_row + 1
    ferien_row = fels_row + 1
    sonstiges_row = ferien_row + 1
    note_rows = list(range(umfang_row + 1, wk_row))

    title = str(ws.cell(row=1, column=3).value or '')
    m = re.search(r'(20\d{2})', title)
    start_year = int(m.group(1)) if m else date.today().year

    def cellstr(row, col):
        v = ws.cell(row=row, column=col).value
        if v is None:
            return None
        s = str(v).strip()
        return s if s and s.lower() != 'leer' else None

    # Farbe->Label-Zuordnung über ALLE Spalten vorab lernen (auch die reinen
    # Monats-Trennspalten ohne numerische KW) - Floyd trägt die Phasen-
    # Bezeichnung manchmal genau auf so einer Trennspalte ein, während die
    # Farbe sich schon auf die folgenden echten KW-Spalten fortsetzt.
    color_label_map = {}
    for c in range(3, ws.max_column + 1):
        praw = cellstr(phase_row, c)
        pnorm = normalize_phase(praw)
        pcolor = get_fill_hex(ws.cell(row=phase_row, column=c))
        if pnorm and pcolor:
            color_label_map[pcolor] = pnorm

    weeks = []
    year = start_year
    prev_kw = None
    for c in range(3, ws.max_column + 1):
        v = ws.cell(row=kw_row, column=c).value
        if isinstance(v, (int, float)):
            kw = int(v)
            if prev_kw is not None and kw < prev_kw - 5:
                year += 1
            prev_kw = kw
        else:
            # Monats-Trennspalte ohne eigene KW-Nummer: sitzt in Floyds Excel exakt
            # auf der dazwischenliegenden, sonst übersprungenen Kalenderwoche (z.B.
            # "Nov" zwischen KW43 und KW45 = KW44) - Phase/Notizen dort NICHT
            # verwerfen, sondern der errechneten KW zuordnen (04.09. Fix: vorher
            # gingen so ganze Wochen samt Phase/Notiz verloren).
            if prev_kw is None:
                continue
            year, kw = _next_iso_week(year, prev_kw)
            prev_kw = kw
        phase_raw = cellstr(phase_row, c)
        phase_color = get_fill_hex(ws.cell(row=phase_row, column=c))
        phase_norm = normalize_phase(phase_raw)
        if phase_norm and phase_color:
            color_label_map[phase_color] = phase_norm
        # Farbe nur für WIRKLICH leere Zellen (keine eigene Beschriftung)
        # von einer anderen Woche gleicher Farbe übernehmen. Steht in der
        # Zelle bereits eigener (auch unbekannter/freitextiger) Text, wird
        # der nie durch eine geratene Kurzphase ersetzt.
        if phase_raw:
            resolved_phase = phase_norm
        else:
            resolved_phase = color_label_map.get(phase_color) if phase_color else None
        umfang = cellstr(umfang_row, c)
        notes = []
        for nr in note_rows:
            label = str(ws.cell(row=nr, column=1).value or '').strip().rstrip(':') or 'Notiz'
            txt = cellstr(nr, c)
            if txt:
                notes.append({'label': label, 'text': txt})
        weeks.append({
            'year': year, 'kw': kw,
            'phase': resolved_phase,
            'phaseRaw': phase_raw,
            'phaseColor': phase_color,
            'reduziert': bool(umfang and umfang.lower().startswith('red')),
            'boulder': cellstr(bouldern_row, c),
            'lead': cellstr(lead_row, c),
            'fels': cellstr(fels_row, c),
            'ferien': cellstr(ferien_row, c),
            'sonstiges': cellstr(sonstiges_row, c),
            'notes': notes,
        })
    return weeks or None

def parse_group_jahresplanung(path):
    """Liest den echten Fokus-Verlauf (Lead/Bouldern/Speed, farbcodiert) aus dem
    Reiter 'Jahresplan <Gruppe>.xlsx'. Analog zu parse_jahresplanung, aber mit
    dem einfacheren Gruppen-Zeilenraster (nur 'Fokus'-Zeile statt 'Phase')."""
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception:
        return None
    ws = wb[wb.sheetnames[0]]

    kw_row = None
    for r in range(1, 10):
        v = ws.cell(row=r, column=1).value
        if v and str(v).strip().lower().startswith('kalenderwoche'):
            kw_row = r
            break
    if kw_row is None:
        return None

    # Es kann mehrere "Fokus..."-Zeilen geben (z.B. "Fokus Stand 08.2025" und
    # "Fokus Stand 01.2026") - die mit den meisten echten Einträgen gewinnt.
    fokus_candidates = []
    for r in range(kw_row + 1, kw_row + 5):
        v = ws.cell(row=r, column=1).value
        if v and str(v).strip().lower().startswith('fokus'):
            fokus_candidates.append(r)
    if not fokus_candidates:
        return None

    def cellstr(row, col):
        v = ws.cell(row=row, column=col).value
        if v is None:
            return None
        s = str(v).strip()
        return s if s and s.lower() != 'leer' else None

    def count_filled(r):
        return sum(1 for c in range(3, ws.max_column + 1) if cellstr(r, c))
    phase_row = max(fokus_candidates, key=count_filled)

    start_year = 2025
    for c in range(1, 10):
        v = ws.cell(row=1, column=c).value
        if v:
            m = re.search(r'(20\d{2})', str(v))
            if m:
                start_year = int(m.group(1))
                break

    # Farbe->Label über ALLE Spalten vorab lernen (auch Monats-Trennspalten
    # ohne numerische KW, auf denen das Label manchmal allein sitzt).
    color_label_map = {}
    for c in range(3, ws.max_column + 1):
        praw = cellstr(phase_row, c)
        pcolor = get_fill_hex(ws.cell(row=phase_row, column=c))
        if praw and pcolor:
            color_label_map[pcolor] = praw

    weeks = []
    year = start_year
    prev_kw = None
    for c in range(3, ws.max_column + 1):
        v = ws.cell(row=kw_row, column=c).value
        if isinstance(v, (int, float)):
            kw = int(v)
            if prev_kw is not None and kw < prev_kw - 5:
                year += 1
            prev_kw = kw
        else:
            # Monats-Trennspalte = dazwischenliegende, sonst übersprungene KW
            # (siehe parse_jahresplanung) - nicht verwerfen, sondern zuordnen.
            if prev_kw is None:
                continue
            year, kw = _next_iso_week(year, prev_kw)
            prev_kw = kw
        phase_raw = cellstr(phase_row, c)
        phase_color = get_fill_hex(ws.cell(row=phase_row, column=c))
        resolved_phase = phase_raw or (color_label_map.get(phase_color) if phase_color else None)
        weeks.append({
            'year': year, 'kw': kw,
            'phase': resolved_phase,
            'phaseRaw': phase_raw,
            'phaseColor': phase_color,
        })
    return weeks or None

# ----------------------------------------------------------------- Coaches --

COACHES_EXTRA = [
    {'n': 'Matteo', 'r': 'Coach', 'note': 'Athletik → U13/U15'},
    {'n': 'Naima', 'r': 'Coach', 'note': 'Springerin'},
]
HEADCOACHES = {'Floyd Simen', 'Mark Amann'}

def build_coaches(groups):
    seen = {}
    for g in groups:
        names = re.split(r'\s*\+\s*', g['coaches']) if g['coaches'] else []
        for n in names:
            n = n.strip()
            if not n:
                continue
            seen[n] = 'Headcoach' if n in HEADCOACHES else 'Coach'
    coaches = [{'n': n, 'r': r} for n, r in seen.items()]
    for extra in COACHES_EXTRA:
        if extra['n'] not in [c['n'] for c in coaches]:
            coaches.append({'n': extra['n'], 'r': 'Coach'})
    return coaches

# =============================================================== MAIN =====

def main():
    ex = load_ex()
    catalog = build_catalog(ex)
    groups_kader = load_kader()
    coaches = build_coaches(groups_kader)
    bench_src = load_bench_source()

    INDIVIDUAL_FILES = {
        'Adrian Kathan': 'Adrian Kathan 26_27.xlsx',
        'Mariella Vierhauser': 'Mariella Vierhauser 26_27.xlsx',
        'Raphael Hubmann': 'Raphael Hubmann 26_27.xlsx',
        'Jakob Burtscher': 'Jakob Burtscher 26_27.xlsx',
        'Linus Pfleger': 'Linus Pfleger 26_27.xlsx',
        'Sophie Bickel': 'Sophie Bickel 26_27.xlsx',
        'Matthäus Kathan': 'Matthäus Kathan 26_27.xlsx',
        'Levi Strolz': 'Levi Strolz 26_27.xlsx',
    }
    # Individuen liegen jetzt im Unterordner "Einzelpläne/" (Floyd hat den
    # Testspace-Ordner neu strukturiert); resolve_file fällt bei Bedarf auf
    # den alten Wurzelpfad zurück und toleriert OneDrive-Konfliktkopien
    # (z.B. "Name 2.xlsx").
    INDIVIDUAL_PATHS = {
        name: resolve_file(BASE + 'Einzelpläne/' + fname, BASE + fname)
        for name, fname in INDIVIDUAL_FILES.items()
    }
    GROUP_FILES = {
        'U9': ('Gruppenpläne/U9/Einheitenplanung U9.xlsx', ['Einheitenplanung 26_27', 'Einheitenplanung']),
        'U11I': ('Gruppenpläne/U11 I/Einheitenplanung U11 I.xlsx', ['Einheitenplanung 26_27', 'Einheitenplanung']),
        'U11II': ('Gruppenpläne/U11 II/Einheitenplanung U11 II.xlsx', ['Einheitenplanung 26_27', 'Einheitenplanung']),
        'U13 I': ('Gruppenpläne/U13 I/Einheitenplanung U13 I.xlsx', ['Einheitenplanung 26_27', 'Einheitenplanung']),
        'U13II': ('Gruppenpläne/U13 II/Einheitenplanung U13 II.xlsx', ['Einheitenplanung 26_27', 'Einheitenplanung']),
        'U15I': ('Gruppenpläne/U15 I/EINHEITENPLANUNG U15 I.xlsx', ['Einheitenplanung 26_27', 'Einheitenplanung']),
        'U15 II': ('Gruppenpläne/U15 II/EINHEITENPLANUNG U15 II.xlsx', ['Einheitenplanung 26_27', 'Einheitenplanung']),
    }
    GROUP_JAHRESPLAN_FILES = {
        'U9': 'Gruppenpläne/U9/Jahresplan U9.xlsx',
        'U11I': 'Gruppenpläne/U11 I/Jahresplan U11 I.xlsx',
        'U11II': 'Gruppenpläne/U11 II/Jahresplan U11 II.xlsx',
        'U13 I': 'Gruppenpläne/U13 I/Jahresplan U13 I.xlsx',
        'U13II': 'Gruppenpläne/U13 II/Jahresplan U13 II.xlsx',
        'U15I': 'Gruppenpläne/U15 I/Jahresplanung U15.xlsx',
        'U15 II': 'Gruppenpläne/U15 II/Jahresplanung U15.xlsx',
    }

    PLANS = {}
    WEEKS_BY_ATHLETE = {}
    CATS_BY_ATHLETE = {}
    BENCH = {}
    SOURCE_INFO = {}
    JAHRESPLAN = {}
    JAHRESPLAN_SOURCE = {}
    JAHRESPLAN_GROUP = {}
    JAHRESPLAN_GROUP_SOURCE = {}
    SEASON_STATS = {'25/26': {}, '26/27': {}}

    # Trainingsdoku (Forms) - einmal für alle Athlet:innen laden, gegen die
    # komplette Kaderliste (aus load_kader()) matchen. Kein Erfinden: Namen,
    # die nicht zugeordnet werden können, landen in DOKU_UNMATCHED statt
    # stillschweigend zu verschwinden.
    ALL_ROSTER_NAMES = sorted(set(a['n'] for g in groups_kader for a in g['athletes']))
    FORMS_BY_ATHLETE, DOKU_UNMATCHED = load_forms_doku(BASE + 'Trainingsdoku KVV.xlsx', ALL_ROSTER_NAMES)
    BENCH_FORMS_BY_ATHLETE, BENCH_UNMATCHED = load_bench_source_forms(BASE + 'Benchmark Update.xlsx', ALL_ROSTER_NAMES)

    for name, fname in INDIVIDUAL_FILES.items():
        fpath = INDIVIDUAL_PATHS[name]
        cats_counter = {}
        weeks, weeks_out, doku_stats = parse_individual(
            fpath, name, catalog, ex, cats_counter, forms_records=FORMS_BY_ATHLETE.get(name))
        PLANS['a:' + name] = weeks
        WEEKS_BY_ATHLETE[name] = weeks_out
        CATS_BY_ATHLETE['a:' + name] = cats_counter
        SOURCE_INFO['a:' + name] = 'Einheitenplanung 26_27 · ' + os.path.basename(fpath)
        aufbau_n = count_aufbau_sessions(weeks)
        b = build_bench_for(name, BENCH_FORMS_BY_ATHLETE.get(name),
                             bench_src if name == 'Adrian Kathan' else None, aufbau_count=(aufbau_n or None))
        if b:
            BENCH[name] = b
        jp = parse_jahresplanung(fpath)
        if jp:
            JAHRESPLAN[name] = jp
            JAHRESPLAN_SOURCE[name] = 'Jahresplanung · ' + os.path.basename(fpath)
        ss = parse_season_individual(fpath)
        if ss:
            SEASON_STATS['25/26']['a:' + name] = ss
        # Saison 26/27: direkt aus den bereits geparsten Einheitenplanung-26_27-Daten
        # (parse_season_individual liest das alte alte Schema und ist für 26/27 nicht gültig)
        if cats_counter or weeks_out:
            SEASON_STATS['26/27']['a:' + name] = {
                'catCounts': [{'name': c, 'count': cats_counter.get(c, 0)} for c in CAT_ORDER],
                'weeks': weeks_out,
                'sheet': 'Einheitenplanung 26_27',
                'doku': doku_stats,
            }

    for gid, (relpath, sheet_cands) in GROUP_FILES.items():
        cats_counter = {}
        weeks, sheetname = parse_group(BASE + relpath, sheet_cands, catalog, ex, cats_counter)
        PLANS['g:' + gid] = weeks
        CATS_BY_ATHLETE['g:' + gid] = cats_counter
        SOURCE_INFO['g:' + gid] = f'{sheetname or "?"} · {relpath.split("/")[-1]}'
        ss = parse_season_group(BASE + relpath, SEASON_WEEKS)
        if ss:
            SEASON_STATS['25/26']['g:' + gid] = ss
        ss27 = build_group_season_stats_from_weeks(weeks, SEASON_WEEKS_2627, sheetname or 'Einheitenplanung 26_27')
        # Gruppen-Doku (26/27 = aktuelle/laufende Saison): Motivation/Trainingsdauer/Load
        # über alle Athlet:innen der Gruppe, aus allen Forms-Antworten - bewusst NICHT
        # auf SEASON_WEEKS_2627 (KW38+) gefiltert, da Live-Doku (wie bei den Einzelplänen)
        # unabhängig vom Kalender-Saisonstart gezählt wird (sonst fehlen z.B. Testeinträge
        # von vor KW38 komplett, obwohl sie real und aktuell sind).
        group_names = [a['n'] for a in next((g['athletes'] for g in groups_kader if g['id'] == gid), [])]
        forms_2627 = {n: FORMS_BY_ATHLETE[n] for n in group_names if FORMS_BY_ATHLETE.get(n)}
        group_doku_season = aggregate_group_doku_season(group_names, forms_2627)
        group_doku_weeks = aggregate_group_doku_weeks(group_names, forms_2627)
        if ss27:
            ss27['doku'] = group_doku_season
            SEASON_STATS['26/27']['g:' + gid] = ss27
        elif group_doku_season:
            SEASON_STATS['26/27']['g:' + gid] = {
                'catCounts': [{'name': c, 'count': cats_counter.get(c, 0)} for c in CAT_ORDER],
                'weeks': [], 'sheet': sheetname or 'Einheitenplanung 26_27', 'doku': group_doku_season,
            }
        for wk_key, wk_entry in weeks.items():
            yk = (wk_entry.get('year'), wk_entry.get('kw'))
            wk_entry['doku'] = group_doku_weeks.get(yk)
        jp_path = GROUP_JAHRESPLAN_FILES.get(gid)
        if jp_path:
            jpg = parse_group_jahresplanung(BASE + jp_path)
            if jpg:
                JAHRESPLAN_GROUP[gid] = jpg
                JAHRESPLAN_GROUP_SOURCE[gid] = 'Jahresplan · ' + jp_path.split('/')[-1]

    # Missing sources -> explicit empty markers (kein Erfinden)
    for missing in ['Levi Strolz']:
        if ('a:' + missing) not in PLANS:
            PLANS['a:' + missing] = {}
            SOURCE_INFO['a:' + missing] = 'Keine Excel-Datei im Testspace-Ordner hinterlegt'
    if 'g:SPOGY Gruppe' not in PLANS:
        PLANS['g:SPOGY Gruppe'] = {}
        SOURCE_INFO['g:SPOGY Gruppe'] = 'Keine Gruppen-Excel für SPOGY im Testspace-Ordner hinterlegt (Athlet:innen haben Einzelpläne)'

    gk = load_gk()

    data = {
        'GENERATED': '2026-08-27',
        'GROUPS': groups_kader,
        'COACHES': coaches,
        'EX': ex,
        'PLANS': PLANS,
        'CATS_BY_VIEW': {k: [{'name': c, 'count': v.get(c, 0)} for c in CAT_ORDER] for k, v in CATS_BY_ATHLETE.items()},
        'WEEKS_BY_ATHLETE': WEEKS_BY_ATHLETE,
        'BENCH': BENCH,
        'GK': gk,
        'SOURCE_INFO': SOURCE_INFO,
        'JAHRESPLAN': JAHRESPLAN,
        'JAHRESPLAN_SOURCE': JAHRESPLAN_SOURCE,
        'JAHRESPLAN_GROUP': JAHRESPLAN_GROUP,
        'JAHRESPLAN_GROUP_SOURCE': JAHRESPLAN_GROUP_SOURCE,
        'SEASON_STATS': SEASON_STATS,
        'SEASON_LABEL': SEASON_LABEL,
        'SEASONS': SEASONS,
    }

    js = 'window.TPDATA = ' + json.dumps(data, ensure_ascii=False, default=str) + ';\n'
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(js)
    print('wrote', OUT, len(js), 'bytes')
    print('athletes with plans:', {k: len(v) for k, v in PLANS.items() if k.startswith('a:')})
    print('groups with plans:', {k: len(v) for k, v in PLANS.items() if k.startswith('g:')})
    print('bench:', list(BENCH.keys()))
    print('doku: athletes with forms-daten:', sorted(FORMS_BY_ATHLETE.keys()))
    if DOKU_UNMATCHED:
        print('doku: NICHT zugeordnete Namen in Trainingsdoku KVV.xlsx:', DOKU_UNMATCHED)

if __name__ == '__main__':
    main()
