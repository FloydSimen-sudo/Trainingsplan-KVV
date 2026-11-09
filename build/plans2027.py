# -*- coding: utf-8 -*-
"""
Leser fuer die neuen Jahresplaene 2027 (eine Excel je Athlet:in / Gruppe).

Excel wird NUR GELESEN (openpyxl, kein save). Pfade stehen in
build/plans2027_config.json (konfigurierbar, mehrere Wurzeln werden der Reihe nach
probiert -- z.B. spaeter "Trainingspläne 2027" / "Trainingspläne 2026" eine Ebene
unter "Trainingsplanung Live").

Blatt "Jahresplanung": A-C Labels, D typische Wochentage, ab Spalte E eine Spalte je
Kalenderwoche (E = KW37/2026). Zeilen 4-12 Tracks (WK, Testung, Fels, Ferien, Phase,
Kraftausdauer, Deload), ab 13 Inhaltszeilen nach Kategorie. Zusammengefuehrte Zellen
= Block ueber mehrere Wochen. Ausgeblendete Zeilen werden uebersprungen.

Blatt "Einheitenplanung": Wochenansicht Mo-So, je Tag Session 1/2, Athletik-Details,
DOKU-Block. Zeilen werden ueber die Beschriftung in Spalte A gefunden (nicht ueber
feste Zeilennummern).
"""
import glob
import unicodedata
import json
import os
import re
from datetime import date, datetime, timedelta

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, 'plans2027_config.json')

DEFAULT_CONFIG = {
    # Ordner unter "Trainingsplanung Live"; {year} wird ersetzt. Ohne "current_year" nimmt der Build
    # automatisch das hoechste vorhandene Jahr ("Trainingspläne 2028" wird ohne Codeaenderung erkannt),
    # die Saison davor ist der Ordner fuer die alten Plaene ("old_year" ueberschreibt das).
    'plans_dir': 'Trainingspläne {year}',
    'current_year': None,
    'old_year': None,
    'subdirs': ['Einzelpläne', 'Gruppenpläne', ''],
    'file_pattern': '{name} {year}.xlsx',
    # Solange der Ordner "Trainingspläne <Jahr>" noch nicht existiert: Ausweichorte (Jahr fuer den Dateinamen)
    'fallback_roots': ['Projekt Jahresplanung/Jahresplanung 2027/Neue Pläne'],
    'fallback_year': 2027,
    # Start der Jahresplanung (Spalte E = Montag dieser Woche = KW37/2026)
    'jahresplan_start': '2026-09-07',
    # new_wins : neue Excel ueberschreibt Tage, an denen sie Inhalt hat (Doku/Zeit/Trainer bleiben)
    # fill_gaps: nur leere Tage werden gefuellt
    # off      : Einheitenplanung der neuen Excel wird nicht gelesen
    'einheiten_policy': 'new_wins',
}


def real_dir(base, name):
    """Tatsaechlicher Ordnername (tolerant gegen NFD/NFC-Umlaute, z.B. aus iCloud/OneDrive)."""
    try:
        for d in os.listdir(base):
            if unicodedata.normalize('NFC', d) == unicodedata.normalize('NFC', name):
                return d
    except OSError:
        pass
    return name


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding='utf-8') as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        pass
    env_root = os.environ.get('TP_PLANS_YEAR')
    if env_root:
        cfg['current_year'] = int(env_root)
    return cfg


def detect_years(base, cfg):
    """Alle vorhandenen Jahre der Ordner 'plans_dir' (absteigend)."""
    pat = re.escape(cfg['plans_dir']).replace(re.escape('{year}'), r'(\d{4})')
    years = []
    try:
        for d in os.listdir(base):
            m = re.fullmatch(pat, unicodedata.normalize('NFC', d))
            if m and os.path.isdir(os.path.join(base, d)):
                years.append(int(m.group(1)))
    except OSError:
        pass
    return sorted(set(years), reverse=True)


def current_year(base, cfg):
    if cfg.get('current_year'):
        return int(cfg['current_year'])
    ys = detect_years(base, cfg)
    return ys[0] if ys else None


def old_root(base, cfg=None):
    """Relativer Ordner der alten Plaene ('Trainingspläne 2026/') oder '' (alter Ort direkt unter Live)."""
    cfg = cfg or load_config()
    old = cfg.get('old_year')
    if not old:
        cur = current_year(base, cfg)
        ys = [y for y in detect_years(base, cfg) if cur is None or y < cur]
        old = ys[0] if ys else None
    if old:
        d = real_dir(base, cfg['plans_dir'].format(year=old))
        if os.path.isdir(os.path.join(base, d)):
            return d + '/'
    return ''


def resolve_plan_file(base, name, cfg=None):
    """Sucht '<root>/<sub>/<name>/<name> <Jahr>.xlsx' bzw. '<root>/<sub>/<name> <Jahr>.xlsx'.
    Erst 'Trainingspläne <aktuelles Jahr>', dann die Ausweichorte. Gibt abs. Pfad oder None."""
    cfg = cfg or load_config()
    cands = []
    cur = current_year(base, cfg)
    if cur:
        cands.append((real_dir(base, cfg['plans_dir'].format(year=cur)), cur))
    for fr in cfg.get('fallback_roots', []):
        cands.append((fr, cfg.get('fallback_year') or cur))
    for root, year in cands:
        rdir = root if os.path.isabs(root) else os.path.join(base, root)
        if not os.path.isdir(rdir):
            continue
        fname = cfg['file_pattern'].format(name=name, year=year)
        for sub in cfg['subdirs']:
            for cand in (os.path.join(rdir, sub, name, fname), os.path.join(rdir, sub, fname)):
                if os.path.isfile(cand):
                    return cand
    return None


# ------------------------------------------------------------ Hilfsfunktionen
def _fill_hex(cell):
    try:
        fg = cell.fill.fgColor
        rgb = fg.rgb if fg else None
    except Exception:
        rgb = None
    if not isinstance(rgb, str) or len(rgb) != 8 or rgb[:2] == '00':
        return None
    if cell.fill.patternType not in (None, 'solid'):
        return '#' + rgb[2:]
    return '#' + rgb[2:] if cell.fill.patternType == 'solid' else None


def _is_red_font(cell):
    try:
        c = cell.font.color if cell.font else None
        rgb = c.rgb if (c is not None and c.type == 'rgb') else None
    except Exception:
        rgb = None
    return isinstance(rgb, str) and len(rgb) == 8 and rgb[-6:].upper() == 'FF0000'


def _txt(v):
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def _merge_map(ws):
    """(row, col) -> (min_row, min_col, max_row, max_col) fuer jede Zelle in einem Merge."""
    mm = {}
    for m in ws.merged_cells.ranges:
        box = (m.min_row, m.min_col, m.max_row, m.max_col)
        for r in range(m.min_row, m.max_row + 1):
            for c in range(m.min_col, m.max_col + 1):
                mm[(r, c)] = box
    return mm


def _val(ws, mm, r, c):
    """Zellwert; bei zusammengefuehrten Zellen der Wert der linken oberen Zelle."""
    box = mm.get((r, c))
    if box:
        return ws.cell(box[0], box[1]).value
    return ws.cell(r, c).value


# =========================================================== Jahresplanung ==
TRACKS = [  # (key, Label in Spalte A/B, Anzeigename)
    ('wkB', 'bouldern', 'WK Bouldern'),
    ('wkWC', 'world cups', 'World Cups'),
    ('wkL', 'lead', 'WK Lead'),
    ('test', 'testung', 'Testung'),
    ('fels', 'fels', 'Fels'),
    ('ferien', 'schulferien', 'Schulferien'),
    ('phase', 'phase allgemein', 'Phase'),
    ('ka', 'kraftausdauerphase', 'Kraftausdauer'),
    ('deload', 'deload', 'Deload'),
]
COALESCE_TRACKS = ('phase', 'ka')


def parse_jahresplanung(path, cfg=None):
    """-> dict {source, weeks[{y,kw,mon}], tracks{key:[block]}, rows[...]} oder None."""
    cfg = cfg or load_config()
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception:
        return None
    if 'Jahresplanung' not in wb.sheetnames:
        return None
    ws = wb['Jahresplanung']
    mm = _merge_map(ws)

    kw_row = None
    for r in range(1, 8):
        if _txt(ws.cell(r, 1).value).lower().startswith('kalenderwoche'):
            kw_row = r
            break
    if kw_row is None:
        return None
    first_col = 5  # Spalte E
    # Anzahl Wochen: letzte Spalte mit KW-Zahl/Monatsname in der KW-Zeile
    last_col = first_col
    for c in range(first_col, ws.max_column + 1):
        if ws.cell(kw_row, c).value not in (None, ''):
            last_col = c
    start = date.fromisoformat(cfg['jahresplan_start'])
    n_weeks = last_col - first_col + 1
    weeks = []
    for i in range(n_weeks):
        mon = start + timedelta(days=7 * i)
        y, kw, _ = mon.isocalendar()
        weeks.append({'y': y, 'kw': kw, 'mon': mon.isoformat()})

    hidden = {r for r, d in ws.row_dimensions.items() if d.hidden}

    def blocks_for_row(r, coalesce=False):
        out = []
        c = first_col
        while c <= last_col:
            box = mm.get((r, c))
            v = _val(ws, mm, r, c) if box else ws.cell(r, c).value
            t = _txt(v)
            span = 1
            if box:
                if box[1] < c:        # nicht linke obere Zelle -> schon behandelt
                    c += 1
                    continue
                span = min(box[3], last_col) - c + 1
            if t:
                cell = ws.cell(box[0], box[1]) if box else ws.cell(r, c)
                out.append({'s': c - first_col, 'n': span, 't': t, 'c': _fill_hex(cell)})
            c += span
        if coalesce:
            merged = []
            for b in out:
                if merged and merged[-1]['t'] == b['t'] and merged[-1]['s'] + merged[-1]['n'] == b['s']:
                    merged[-1]['n'] += b['n']
                else:
                    merged.append(dict(b))
            out = merged
        return out

    # Tracks (Zeilen vor der ersten Inhaltszeile 'Warm Up')
    tracks = {}
    content_start = None
    for r in range(kw_row + 2, ws.max_row + 1):
        a, b, c3 = (_txt(ws.cell(r, k).value).lower() for k in (1, 2, 3))
        if a.startswith('warm up') or c3.startswith('warm up'):
            content_start = r
            break
    if content_start is None:
        content_start = 13
    for r in range(kw_row + 2, content_start):
        if r in hidden:
            continue
        lab = (_txt(ws.cell(r, 1).value) + ' ' + _txt(ws.cell(r, 2).value)).strip().lower()
        for key, needle, _disp in TRACKS:
            if key in tracks:
                continue
            if lab == needle or lab.endswith(' ' + needle) or lab.startswith(needle):
                tracks[key] = blocks_for_row(r, coalesce=(key in COALESCE_TRACKS))
                break

    # Inhaltszeilen
    rows = []
    cat, sub = '', ''
    for r in range(content_start, ws.max_row + 1):
        a_box = mm.get((r, 1))
        a = _txt(ws.cell(a_box[0], 1).value) if a_box else _txt(ws.cell(r, 1).value)
        b_box = mm.get((r, 2))
        b = _txt(ws.cell(b_box[0], 2).value) if b_box else _txt(ws.cell(r, 2).value)
        c3 = _txt(ws.cell(r, 3).value)
        if a:
            cat = re.sub(r'\s+', ' ', a)
            sub = ''
        if b and (c3 or not a):
            sub = re.sub(r'\s+', ' ', b)
        label = c3 or (cat if (not c3 and a) else '')
        if not label:
            continue
        if r in hidden:
            continue
        blocks = blocks_for_row(r)
        if not blocks:
            continue
        rows.append({
            'cat': cat, 'sub': sub if c3 else '', 'label': label,
            'days': _txt(ws.cell(r, 4).value), 'blocks': blocks,
        })

    return {'source': os.path.basename(path), 'weeks': weeks, 'tracks': tracks, 'rows': rows,
            'wk': wk_list(weeks, tracks)}


WK_DATE_FULL_RE = re.compile(r'(\d{1,2})\.(\d{1,2})\.\s*[-–]\s*\d{1,2}\.\d{1,2}\.')
WK_DATE_RE = re.compile(r'(\d{1,2})(?:\s*[.\/,\-–]{1,3}\s*\d{1,2})*\.\s*(\d{1,2})\.')


def wk_list(weeks, tracks):
    """Wettkampfliste [{date, name, kind}] aus den WK-Zeilen. Datum = erstes Datum im Text
    (z.B. '21/22.11.' -> 21.11.); ohne lesbares Datum der Montag der Blockwoche (approx=True)."""
    out = []
    for key, kind in (('wkB', 'Bouldern'), ('wkWC', 'World Cup'), ('wkL', 'Lead')):
        for b in tracks.get(key, []):
            mon = date.fromisoformat(weeks[b['s']]['mon'])
            end = mon + timedelta(days=7 * b['n'] - 1)
            d, approx = None, True
            m = WK_DATE_FULL_RE.search(b['t']) or WK_DATE_RE.search(b['t'])
            if m:
                day, month = int(m.group(1)), int(m.group(2))
                for yr in (mon.year, mon.year + 1, mon.year - 1):
                    try:
                        cand = date(yr, month, day)
                    except ValueError:
                        continue
                    if mon - timedelta(days=7) <= cand <= end + timedelta(days=7):
                        d, approx = cand, False
                        break
            if d is None:
                d = mon
            out.append({'date': d.isoformat(), 'name': b['t'], 'kind': kind, 'approx': approx})
    out.sort(key=lambda x: (x['date'], x['name']))
    ded = []
    for x in out:
        if ded and ded[-1]['name'] == x['name'] and (ded[-1]['date'] == x['date'] or x['approx']):
            continue
        ded.append(x)
    return ded


def legacy_phase_weeks(jp):
    """Format der bisherigen Phasen-Leiste: [{year,kw,phase,phaseColor,phaseRaw}]."""
    n = len(jp['weeks'])
    per = [None] * n
    for b in jp['tracks'].get('phase', []):
        for i in range(b['s'], min(n, b['s'] + b['n'])):
            per[i] = b
    out = []
    for i, w in enumerate(jp['weeks']):
        b = per[i]
        out.append({
            'year': w['y'], 'kw': w['kw'],
            'phase': b['t'] if b else None,
            'phaseRaw': b['t'] if b else None,
            'phaseColor': (b['c'] if b else None),
        })
    return out


# ========================================================= Einheitenplanung ==
DOW = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
TIME_RE = re.compile(r'^\s*(\d{1,2})[:.](\d{2})(?:\s*[-–]\s*(\d{1,2})[:.](\d{2}))?')


def _norm(s):
    return re.sub(r'\s+', ' ', _txt(s)).strip().lower()


def _parse_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = _txt(v)
    for fmt in ('%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            pass
    return None


def parse_einheitenplanung(path, make_item):
    """-> {'YYYY-KW': {days, span, year, kw}} im Format der bisherigen Pläne.
    Nur Wochen/Tage mit mindestens einem Inhalt bekommen Sessions; leere Wochen werden
    NICHT ausgegeben (damit eine leere Vorlage nichts ueberschreibt).
    make_item(text, red) -> Item-Dict ({ex, match, explicitTime, red})."""
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception:
        return {}
    if 'Einheitenplanung' not in wb.sheetnames:
        return {}
    ws = wb['Einheitenplanung']
    mm = _merge_map(ws)

    # Zeilen ueber Spalte A
    rowlab = {r: _norm(ws.cell(r, 1).value) for r in range(1, ws.max_row + 1)}
    date_row = next((r for r, l in rowlab.items() if l == 'datum'), 4)
    sec = []  # (typ, nr, start_row)
    for r, l in rowlab.items():
        m = re.match(r'session\s*(\d+)', l)
        if m:
            sec.append(('session', int(m.group(1)), r))
        elif l.startswith('athletik-details'):
            sec.append(('details', 0, r))
        elif l == 'doku':
            sec.append(('doku', 0, r))
    sec.sort(key=lambda x: x[2])
    sections = {}
    for i, (typ, nr, r0) in enumerate(sec):
        r1 = (sec[i + 1][2] if i + 1 < len(sec) else ws.max_row + 1) - 1
        sections[(typ, nr)] = (r0 + 1, r1)

    def rows_of(block):
        r0, r1 = block
        return [(r, rowlab[r]) for r in range(r0, r1 + 1)]

    def cat_rows(block):
        """label -> [rows] (mehrfach vorkommende Labels, z.B. 'notizen', als Liste)."""
        d = {}
        for r, l in rows_of(block):
            d.setdefault(l, []).append(r)
        return d

    # Tagesspalten
    day_cols = []
    for c in range(2, ws.max_column + 1):
        d = _parse_date(ws.cell(date_row, c).value)
        if d:
            day_cols.append((c, d))

    def cell_items(r, c):
        v = _val(ws, mm, r, c)
        t = _txt(v)
        if not t:
            return []
        red = _is_red_font(ws.cell(r, c))
        return [make_item(p.strip(), red) for p in re.split(r'[\n;]+', t) if p.strip()]

    def cell_text(r, c):
        return _txt(_val(ws, mm, r, c))

    sess_blocks = {nr: blk for (typ, nr), blk in sections.items() if typ == 'session'}
    details_blk = sections.get(('details', 0))
    doku_blk = sections.get(('doku', 0))

    def pick(rowsd, *labels, startswith=None):
        for l in labels:
            if l in rowsd:
                return rowsd[l]
        if startswith:
            for l, rs in rowsd.items():
                if l.startswith(startswith):
                    return rs
        return []

    weeks = {}
    for c, d in day_cols:
        sessions = []
        sonst_parts = []
        athl_for_details = None
        for nr in sorted(sess_blocks):
            rd = cat_rows(sess_blocks[nr])
            r_sonst = pick(rd, 'sonstiges')
            r_ort = pick(rd, 'trainigsort', 'trainingsort')
            r_theo = pick(rd, '1 theorie')
            r_wu = pick(rd, '2 aufwärmen')
            r_mot = pick(rd, '3 motorik')
            r_tf = pick(rd, 'technikfokus')
            r_t1 = pick(rd, '4 technik taktik 1')
            r_t2 = pick(rd, '5 technik taktik 2')
            r_p1 = pick(rd, '6 physis klettern 1')
            r_p2 = pick(rd, '7 physis klettern 2')
            r_ath = pick(rd, startswith='8 athletik')
            r_spez = pick(rd, 'spezial')
            r_notiz = pick(rd, 'notizen')

            def grab(rs):
                out = []
                for r in rs:
                    out.extend(cell_items(r, c))
                return out

            sonst = ' · '.join(x for x in (cell_text(r, c) for r in r_sonst) if x)
            ort = ' · '.join(x for x in (cell_text(r, c) for r in r_ort) if x)
            ort_red = any(_is_red_font(ws.cell(r, c)) for r in r_ort if cell_text(r, c))
            cats = [
                {'name': 'Theorie', 'items': grab(r_theo)},
                {'name': 'Aufwärmen', 'items': grab(r_wu)},
                {'name': 'Motorik', 'items': grab(r_mot)},
                {'name': 'Technikfokus', 'items': grab(r_tf)},
                {'name': 'Technik/Taktik', 'items': grab(r_t1) + grab(r_t2)},
                {'name': 'Physis Klettern', 'items': grab(r_p1) + grab(r_p2)},
                {'name': 'Athletik + Mentales', 'items': grab(r_ath)},
                {'name': 'Spezial', 'items': grab(r_spez)},
            ]
            notiz_parts = [cell_text(r, c) for r in r_notiz]
            notiz = ' · '.join(p for p in notiz_parts if p) or None
            notiz_red = any(_is_red_font(ws.cell(r, c)) for r in r_notiz if cell_text(r, c))
            any_item = any(cat['items'] for cat in cats)
            if any_item and athl_for_details is None and cats[6]['items']:
                athl_for_details = cats[6]
            tm = TIME_RE.match(sonst) if sonst else None
            time = ''
            if tm:
                time = f'{int(tm.group(1)):02d}:{tm.group(2)}'
                if tm.group(3):
                    time += f'-{int(tm.group(3)):02d}:{tm.group(4)}'
            has_content = bool(ort or any_item or notiz)
            if sonst:
                rest = sonst[tm.end():].strip(' ·-–,') if tm else sonst
                part = rest if has_content else sonst   # leere Session: volle Angabe (inkl. Uhrzeit) in "Sonstiges"
                if part:
                    sonst_parts.append(part)
            if has_content:
                sessions.append({'name': f'Session {nr}', 'time': time, 'ort': ort or None, 'ortRed': ort_red,
                                 'cats': cats, 'notiz': notiz, 'notizRed': notiz_red, 'sonstiges': sonst or None})

        # Athletik-Details (pro Tag) -> als Items an die Athletik-Kategorie der ersten Session mit Athletik
        details = []
        if details_blk:
            for r, lab in rows_of(details_blk):
                t = cell_text(r, c)
                if t:
                    label = _txt(ws.cell(r, 1).value)
                    details.append((label, t, _is_red_font(ws.cell(r, c))))
        if details:
            target = athl_for_details
            if target is None:
                tgt_sess = sessions[0] if sessions else None
                if tgt_sess is None:
                    tgt_sess = {'name': 'Session 1', 'time': '', 'ort': None, 'ortRed': False,
                                'cats': [{'name': n, 'items': []} for n in
                                         ['Theorie', 'Aufwärmen', 'Motorik', 'Technikfokus', 'Technik/Taktik',
                                          'Physis Klettern', 'Athletik + Mentales', 'Spezial']],
                                'notiz': None, 'notizRed': False, 'sonstiges': None}
                    sessions.append(tgt_sess)
                target = tgt_sess['cats'][6]
            labels_l = [lb.lower() for lb, _t, _r in details]

            def _is_overview(text):
                # Uebersichtszelle wie "Finger, Campus, Hangeln, Core" -> durch die Details ersetzt
                parts = [x.strip().lower().rstrip('.…') for x in re.split(r'[,/+&]', text) if x.strip()]
                if len(parts) < 2:
                    return False
                hit = sum(1 for pt in parts if any(l.startswith(pt) or pt.startswith(l) for l in labels_l))
                return hit / len(parts) >= 0.6

            target['items'] = [it for it in target['items'] if not _is_overview(it['ex'])]
            have = {it['ex'].lower() for it in target['items']}
            for label, t, red in details:
                txt = t if label.lower() == t.lower() else f'{label}: {t}'
                if txt.lower() in have:
                    continue
                target['items'].append(make_item(txt, red))

        # DOKU (Excel-eigener Block); nur wenn etwas eingetragen
        doku = None
        if doku_blk:
            dv = {}
            for r, lab in rows_of(doku_blk):
                dv[lab] = _val(ws, mm, r, c)
            if any(_txt(v) for v in dv.values()):
                doku = {'raw': {k: _txt(v) for k, v in dv.items() if _txt(v)}}

        y, kw, wd = d.isocalendar()
        wk = weeks.setdefault(f'{y}-{kw}', {'days': {}, 'year': y, 'kw': kw})
        _day = {
            'dow': DOW[wd - 1], 'dom': d.strftime('%d.%m.'), 'date': d.isoformat(),
            'ort': next((s['ort'] for s in sessions if s.get('ort')), None),
            'sonstiges': ' · '.join(sonst_parts) or None,
            'sessions': sessions, 'doku': doku, 'notiz': None,
        }
        _split_sonst(_day)
        wk['days'][wd - 1] = _day

    out = {}
    for key, wk in weeks.items():
        has_content = any(day['sessions'] or day['sonstiges'] for day in wk['days'].values())
        if not has_content:
            continue
        mon = date.fromisocalendar(wk['year'], wk['kw'], 1)
        days = []
        for i in range(7):
            dd = wk['days'].get(i)
            if dd is None:
                dt = mon + timedelta(days=i)
                dd = {'dow': DOW[i], 'dom': dt.strftime('%d.%m.'), 'date': dt.isoformat(), 'ort': None,
                      'sonstiges': None, 'sessions': [], 'doku': None, 'notiz': None}
            days.append(dd)
        sun = mon + timedelta(days=6)
        out[key] = {'days': days, 'span': f'{mon.strftime("%d.%m.")} – {sun.strftime("%d.%m.%Y")}',
                    'year': wk['year'], 'kw': wk['kw']}
    return out


_TIME_LIKE = re.compile(r'^(\d{1,2}[:.]\d{2}(?::\d{2})?\s*[-–]\s*\d{1,2}[:.]\d{2}(?::\d{2})?|\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?\s*(?:h|std\.?|stunden?))$', re.I)

def _split_sonst(day):
    """Zelle 'Sonstiges' im Gruppenformat 'Zeit | Trainer' (z. B. '14:00-16:30 | Nemo', '| Hannah', '2-3h | Selbststaendig')
    -> day['zeit'] und day['trainer']; die Zelle selbst wird dann nicht mehr als Freitext angezeigt."""
    t = day.get('sonstiges')
    # Mehrere Zeitfenster in einer Zelle (z. B. Workshop 14:00-16:30 + Training 16:45-19:45):
    # jede Zeile 'Zeit | Wer' -> zeit-Anzeige mit allen Fenstern, Session-Zeit = letztes Fenster
    if t and '\n' in t.strip():
        slots = []
        _lines = [x.strip() for x in t.split('\n') if x.strip()]
        _z0 = day.get('zeit') or next((str(se['time']).strip() for se in day.get('sessions', []) if se.get('time') and _TIME_LIKE.match(str(se['time']).strip())), None)
        if _lines and _lines[0].startswith('|') and _z0:
            # erste Zeile hat ihre Zeit bereits an Session/Tag abgegeben ('| Wer')
            _lines[0] = _z0 + ' ' + _lines[0]
        for ln in _lines:
            if ln.count('|') != 1:
                slots = []
                break
            l, r = [x.strip() for x in ln.split('|', 1)]
            if not (l and r and _TIME_LIKE.match(l)):
                slots = []
                break
            slots.append((l, r))
        if len(slots) >= 2:
            day['zeit'] = ' · '.join('%s %s' % (l, r) for l, r in slots)
            day['trainer'] = None
            day['sonstiges'] = None
            for se in day.get('sessions', []):
                se['time'] = slots[-1][0]
            return
    if not day.get('zeit'):
        for se in day.get('sessions', []):
            if se.get('time') and _TIME_LIKE.match(str(se['time']).strip()):
                day['zeit'] = str(se['time']).strip()
                break
    if not t or t.count('|') != 1:
        return
    left, right = [x.strip() for x in t.split('|', 1)]
    if left and not _TIME_LIKE.match(left):
        return
    if left:
        day['zeit'] = left
        for se in day.get('sessions', []):
            if not se.get('time'):
                se['time'] = left
    if right:
        day['trainer'] = right
    day['sonstiges'] = None


def merge_weeks(old, new, policy):
    """Fuehrt bisherige Wochen (old) mit neuen (new) zusammen. Mutiert old und gibt
    eine Statistik {'filled':n,'replaced':n,'weeks_added':n} zurueck."""
    stat = {'filled': 0, 'replaced': 0, 'weeks_added': 0}
    if policy == 'off':
        return stat
    for key, nw in new.items():
        if key not in old or not old[key].get('days'):
            old[key] = nw
            stat['weeks_added'] += 1
            continue
        ow = old[key]
        by_date = {d['date']: i for i, d in enumerate(ow['days'])}
        for nd in nw['days']:
            if not nd['sessions'] and not nd.get('sonstiges'):
                continue
            i = by_date.get(nd['date'])
            if i is None:
                continue
            od = ow['days'][i]
            if not nd['sessions']:
                if nd.get('sonstiges') and not od.get('sonstiges') and not od.get('sessions'):
                    od['sonstiges'] = nd['sonstiges']
                    stat['filled'] += 1
                continue
            if od.get('sessions'):
                if policy == 'new_wins':
                    keep = {k: od.get(k) for k in ('zeit', 'trainer', 'zeitRed', 'trainerRed') if k in od and not nd.get(k)}
                    nd = dict(nd)
                    nd.update(keep)
                    nd['doku'] = od.get('doku') or nd.get('doku')
                    ow['days'][i] = nd
                    stat['replaced'] += 1
                continue
            od['sessions'] = nd['sessions']
            for _k in ('zeit', 'trainer'):
                if nd.get(_k):
                    od[_k] = nd[_k]
            if not od.get('ort'):
                od['ort'] = nd.get('ort')
            if nd.get('sonstiges') and not od.get('sonstiges'):
                od['sonstiges'] = nd['sonstiges']
            stat['filled'] += 1
    return stat
