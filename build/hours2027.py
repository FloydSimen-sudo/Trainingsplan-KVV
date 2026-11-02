# -*- coding: utf-8 -*-
"""Exakte Trainingsstunden (Floyd, 02.11.2026).
Regel je Einheit (Session):
  1. Hat der/die Athlet:in fuer genau diese Einheit/den Tag die Zeit selbst dokumentiert -> gilt das.
  2. Sonst Floyds eigene Zeitangabe (Zeit-Bereich wie 16:30-19:00 oder Zeit direkt in einer Inhaltszelle, z. B. "30 min").
  3. Sonst Summe aller geplanten Inhalte mit den Durchschnittszeiten aus "Uebungssammlung Gesamt.xlsx"
     (Bereiche wie 60-90 -> Mittelwert). Inhalte ohne Dauer in der Liste zaehlen 0 und werden gemeldet.
"""
import os, re, json, openpyxl

EXPL_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s*(minuten|minute|min\.?|stunden|stunde|std\.?|h)\b', re.I)
RANGE_RE = re.compile(r'(\d{1,2})[:.](\d{2})(?::\d{2})?\s*[-–]\s*(\d{1,2})[:.](\d{2})(?::\d{2})?')
H_RE = re.compile(r'^\s*(\d+(?:[.,]\d+)?)(?:\s*[-–]\s*(\d+(?:[.,]\d+)?))?\s*(?:h|std\.?|stunden?)\s*$', re.I)

# Kurzformen aus den Plaenen -> Name in der Uebungsliste
ALIASES = {'bb': 'bewegungsbouldern', 'bb offen': 'bewegungsbouldern', 'andere bb': 'bewegungsbouldern',
           'routine': 'warm up routine',
           'spray max': 'max boulder', 'spray aufbau': 'aufbau boulder'}

def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^0-9a-zäöüß ]', ' ', str(s).lower())).strip()

def parse_dauer(v):
    """'60' -> 60 | '60-90' -> 75 | '10 bis 30' -> 20 | '45 +45' -> 90 | '60(-180)' -> 60 | '<120','x' -> None"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) if v > 0 else None
    s = str(v).strip().lower()
    if not s or s == 'x' or s.startswith('<') or s.startswith('>'):
        return None
    m = re.match(r'^(\d+(?:[.,]\d+)?)\s*\+\s*(\d+(?:[.,]\d+)?)$', s)
    if m:
        return float(m.group(1).replace(',', '.')) + float(m.group(2).replace(',', '.'))
    m = re.match(r'^(\d+(?:[.,]\d+)?)\s*(?:-|–|bis)\s*(\d+(?:[.,]\d+)?)$', s)
    if m:
        return (float(m.group(1).replace(',', '.')) + float(m.group(2).replace(',', '.'))) / 2
    m = re.match(r'^(\d+(?:[.,]\d+)?)\s*\(', s)
    if m:
        return float(m.group(1).replace(',', '.'))
    m = re.match(r'^(\d+(?:[.,]\d+)?)$', s)
    return float(m.group(1).replace(',', '.')) if m else None

def load_duration_catalog(path):
    """{normalisierter Name: Minuten} aus Uebungssammlung Gesamt (erste Zeile mit Dauer gewinnt)."""
    cat = {}
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb['Übungssammlung Gesamt'] if 'Übungssammlung Gesamt' in wb.sheetnames else wb.worksheets[0]
        for r in ws.iter_rows(min_row=2, values_only=True):
            if r[2] is None:
                continue
            d = parse_dauer(r[3])
            if d:
                cat.setdefault(norm(r[2]), d)
    except Exception as e:
        print('hours2027: Uebungsliste nicht lesbar:', e)
    # Eigene Ergaenzungen/Korrekturen von Floyd: build/dauer_overrides.json  {"Jule": 60, "Mobi Andree": 20}
    try:
        import json
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dauer_overrides.json'), encoding='utf-8') as f:
            for k, v in json.load(f).items():
                d = parse_dauer(v)
                if d:
                    cat[norm(k)] = d
    except FileNotFoundError:
        pass
    except Exception as e:
        print('hours2027: dauer_overrides.json nicht lesbar:', e)
    return cat

def zeit_hours(z):
    if not z:
        return None
    z = str(z)
    m = RANGE_RE.search(z)
    if m:
        a = int(m.group(1)) + int(m.group(2)) / 60.0
        b = int(m.group(3)) + int(m.group(4)) / 60.0
        return round(b - a, 2) if b > a else None
    m = H_RE.match(z)
    if m:
        lo = float(m.group(1).replace(',', '.')); hi = float(m.group(2).replace(',', '.')) if m.group(2) else lo
        return round((lo + hi) / 2, 2)
    return None

def item_minutes(it, cat):
    """-> (Minuten, Quelle) Quelle: 'explicit' | 'liste' | None"""
    et = it.get('explicitTime')
    if et:
        m = EXPL_RE.search(str(et))
        if m:
            n = float(m.group(1).replace(',', '.'))
            return (n * 60 if m.group(2).lower().startswith(('h', 'std', 'stunde')) else n), 'explicit'
    name = norm(it.get('ex') or '')
    if not name:
        return 0.0, None
    mt = it.get('match')
    if mt and mt.get('min') not in (None, ''):
        d = parse_dauer(mt.get('min'))
        if d:
            return d, 'liste'
    if name in cat:
        return cat[name], 'liste'
    al = ALIASES.get(name)
    if al and al in cat:
        return cat[al], 'liste'
    # Listenname im Text enthalten (nur sinnvolle Namen), laengster Treffer
    best = None
    for k, v in cat.items():
        if len(k) >= 6 and re.search(r'(?<![a-zäöüß])' + re.escape(k) + r'(?![a-zäöüß])', name):
            if not best or len(k) > len(best[0]):
                best = (k, v)
    if best:
        return best[1], 'liste'
    return 0.0, None

def session_planned(sess, cat, missing=None):
    """Geplante Stunden einer Einheit: eigene Zeit > Summe der Inhalte. -> (Stunden, Quelle)"""
    z = zeit_hours(sess.get('time'))
    if z:
        return z, 'zeit'
    mins = 0.0
    for c in sess.get('cats', []):
        for it in c.get('items', []):
            m, src = item_minutes(it, cat)
            mins += m
            if src is None and missing is not None and norm(it.get('ex') or ''):
                missing[it.get('ex').strip()] = missing.get(it.get('ex').strip(), 0) + 1
    return (round(mins / 60.0, 2), 'inhalt') if mins > 0 else (0.0, None)

def individual_day(day, cat, missing=None):
    """-> dict(h, dok, plan) fuer Einzelplaene. Doku der Einheit/des Tages schlaegt Plan."""
    dk = day.get('doku') or {}
    recs = dk.get('sessions') or []
    per = {}; day_doc = 0.0
    for r in recs:
        d = r.get('dur')
        if d is None:
            continue
        if r.get('session') in (1, 2, 3):
            per[r['session']] = per.get(r['session'], 0.0) + d
        else:
            day_doc += d
    sessions = day.get('sessions') or []
    dok = plan = 0.0
    if day_doc > 0 and not per:
        return {'h': round(day_doc, 2), 'dok': round(day_doc, 2), 'plan': 0.0}
    used = set()
    for i, s in enumerate(sessions, 1):
        if per.get(i, 0) > 0:
            dok += per[i]; used.add(i)
        else:
            h, _ = session_planned(s, cat, missing)
            plan += h
    for i, d in per.items():           # dokumentierte Einheit ohne Plan-Session
        if i not in used and d > 0:
            dok += d
    return {'h': round(dok + plan, 2), 'dok': round(dok, 2), 'plan': round(plan, 2)}

def group_day(day, cat, doc_h=None, cal_h=None, fallback=None, missing=None):
    """Gruppen: Doku (Mittel der Athlet:innen) > eigene Zeit (Kalender/Zeit-Feld) > Summe Inhalte > Schaetzung."""
    if doc_h:
        return {'h': round(doc_h, 2), 'src': 'dok'}
    if cal_h:
        return {'h': round(cal_h, 2), 'src': 'zeit'}
    z = zeit_hours(day.get('zeit'))
    if z:
        return {'h': z, 'src': 'zeit'}
    tot = 0.0; src = None
    for s in day.get('sessions', []):
        h, sr = session_planned(s, cat, missing)
        tot += h
        if sr == 'zeit': src = 'zeit' if src in (None, 'zeit') else src
        elif sr: src = 'inhalt'
    if tot > 0:
        return {'h': round(tot, 2), 'src': src or 'inhalt'}
    return {'h': fallback or 0.0, 'src': 'fallback' if fallback else None}


# ---- Standardangaben + Kurzbeschreibung aus "Uebungssammlung Gesamt" (Floyd, 02.11.2026) ----
def _clean(v):
    return None if v is None or str(v).strip().lower() in ('', 'x') else v

def how_bullets(text, maxlen=170):
    """Bis zu zwei Stichpunkte, WOERTLICH aus der Spalte 'Ausfuehrung' (ganze Saetze, nur bei Bedarf am Wortende gekuerzt)."""
    if not text:
        return []
    t = re.sub(r'\s+', ' ', str(text)).strip()
    raw = [p.strip() for p in re.split(r'(?<=[.!?])\s+(?=[A-ZÄÖÜ„"(])', t) if p.strip()]
    parts = []
    for p in raw:                      # Abkuerzungen (ca., z.B., max. ...) nicht als Satzende werten
        if parts and re.search(r'(?:\b(?:ca|bzw|ggf|max|min|Min|Sek|z\.B|d\.h|evtl|inkl|usw|u\.a|vgl)\.)$', parts[-1]):
            parts[-1] += ' ' + p
        else:
            parts.append(p)
    out = []
    for p in parts[:2]:
        if len(p) > maxlen:
            cut = p[:maxlen].rsplit(' ', 1)[0].rstrip(',;:')
            p = cut + ' …'
        out.append(p)
    return out

def load_exercise_catalog(path):
    cat = {}
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb['Übungssammlung Gesamt'] if 'Übungssammlung Gesamt' in wb.sheetnames else wb.worksheets[0]
        for r in ws.iter_rows(min_row=2, values_only=True):
            if r[2] is None or not str(r[2]).strip():
                continue
            k = norm(r[2])
            e = {'name': str(r[2]).strip(), 'min': _clean(r[3]), 'sets': _clean(r[4]), 'vol': _clean(r[5]),
                 'pause': _clean(r[6]), 'how': how_bullets(r[7])}
            if k not in cat:
                cat[k] = e
            else:                      # fehlende Felder aus spaeteren Dubletten ergaenzen
                for f in ('min', 'sets', 'vol', 'pause'):
                    if cat[k][f] is None and e[f] is not None:
                        cat[k][f] = e[f]
                if not cat[k]['how'] and e['how']:
                    cat[k]['how'] = e['how']
    except Exception as ex:
        print('hours2027: Exercise-Katalog nicht lesbar:', ex)
    # Eigene Ergaenzungen von Floyd: build/uebung_overrides.json {"Blackroll": {"min": 10, "how": ["Regenerative Uebung."]}}
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uebung_overrides.json'), encoding='utf-8') as f:
            for nm, v in json.load(f).items():
                e = cat.setdefault(norm(nm), {'name': nm, 'min': None, 'sets': None, 'vol': None, 'pause': None, 'how': []})
                for fld in ('min', 'sets', 'vol', 'pause', 'how'):
                    if fld in v:
                        e[fld] = v[fld]
    except FileNotFoundError:
        pass
    return cat

def find_entry(name, excat):
    n = norm(name or '')
    if not n:
        return None
    al = ALIASES.get(n)
    if n in excat and not (excat[n]['min'] is None and al and al in excat and excat[al]['min'] is not None):
        return excat[n]
    if al and al in excat:
        return excat[al]
    best = None
    for k in excat:
        if len(k) >= 6 and re.search(r'(?<![a-zäöüß])' + re.escape(k) + r'(?![a-zäöüß])', n):
            if not best or len(k) > len(best):
                best = k
    return excat[best] if best else None


def find_latest_exercise_list(base):
    """Neueste 'Uebungssammlung Gesamt*.xlsx' im ganzen Ordner (nach Aenderungsdatum), ohne 'alte Versionen'/Temp-Dateien."""
    import unicodedata
    best = None
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if 'alte version' not in d.lower() and not d.startswith('.')]
        for fn in files:
            n = unicodedata.normalize('NFC', fn).lower()
            if fn.startswith('~') or not n.endswith('.xlsx'):
                continue
            if n.startswith('übungssammlung gesamt') and 'kopie' not in n:
                fp = os.path.join(root, fn)
                m = os.path.getmtime(fp)
                if best is None or m > best[0]:
                    best = (m, fp)
    return best[1] if best else None
