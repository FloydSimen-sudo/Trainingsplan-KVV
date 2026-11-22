# -*- coding: utf-8 -*-
"""Einzelathleten 2027: Einheit eines Tages wird aus Blatt 'Trainingsplanung' (Inhalte je Woche/Wochentag)
+ Blatt 'Notizen' (Tagesnotizen, haben Vorrang) + Google-Kalender (Zeit/Ort/Trainer, build/einzel_kalender.json)
zusammengesetzt. Nur lesen, nie in Excel schreiben."""
import re, json, os
from datetime import date, datetime, timedelta
import openpyxl
import plans2027

DOW = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
ABBR = {'mo': 0, 'di': 1, 'mi': 2, 'do': 3, 'fr': 4, 'sa': 5, 'so': 6}
CATS = ['Theorie', 'Aufwärmen', 'Motorik', 'Technikfokus', 'Technik/Taktik', 'Physis Klettern',
        'Athletik + Mentales', 'Spezial']
START_DATE = date(2026, 11, 2)
JP_START = date(2026, 9, 7)  # KW37/2026 = Spalte E

# (Label-Anfang klein, Kategorie, bevorzugte Session, Standardtag-Regel)
ROWMAP = [
    ('warm up', 'Aufwärmen', 1, 'allday'),
    ('bewegungsbouldern', 'Technik/Taktik', 1, 'bbday'),
    ('frei bouldern', 'Technik/Taktik', 1, None),
    ('technik boulder', 'Technik/Taktik', 1, None),
    ('technik lead', 'Technik/Taktik', 2, None),
    ('taktik 1', 'Theorie', 1, None),
    ('taktik 2', 'Technik/Taktik', 1, None),
    ('physis bouldern', 'Physis Klettern', 1, None),
    ('physis lead', 'Physis Klettern', 2, None),
    ('aerob', 'Physis Klettern', 1, None),
    ('jule', 'Athletik + Mentales', 2, None),
    ('selbst', 'Athletik + Mentales', 1, None),
    ('andré', 'Athletik + Mentales', 1, None),
    ('andre', 'Athletik + Mentales', 1, None),
    ('finger', 'Athletik + Mentales', 1, None),
    ('aufleger', 'Athletik + Mentales', 1, None),
    ('zangen', 'Athletik + Mentales', 1, None),
    ('ziehen', 'Athletik + Mentales', 1, None),
    ('campus', 'Athletik + Mentales', 1, None),
    ('hangeln', 'Athletik + Mentales', 1, None),
    ('stütz', 'Athletik + Mentales', 1, None),
    ('core', 'Athletik + Mentales', 1, None),
    ('handgelenk', 'Athletik + Mentales', 1, None),
    ('athletik', 'Athletik + Mentales', 1, None),
    ('beweglichkeit', 'Athletik + Mentales', 1, None),
    ('mental extern', 'Spezial', 1, 'every'),
    ('mental', 'Spezial', 1, 'every'),
    ('spezial', 'Spezial', 1, 'every'),
    ('ernährung', 'Spezial', 1, 'every'),
    ('gla', 'Athletik + Mentales', 1, None),
    # WK-Sim: nur zur Planung fuer Floyd, wird NICHT in die App uebernommen (Floyd, 16.11.2026)
]
DATE_RE = re.compile(r'(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{2,4})?')
PREFIX = re.compile(r'^\s*(Mo|Di|Mi|Do|Fr|Sa|So)\s*[:\-–]\s*(.+)$', re.S)
SKIP = {'x', '-', '–'}
TIME_RE = re.compile(r'(\d{1,2})[:.](\d{2})')


def _t(v):
    if v is None:
        return ''
    return str(v).strip()


def _mins(s, e):
    try:
        a = [int(x) for x in s.split(':')]; b = [int(x) for x in e.split(':')]
        return (b[0] * 60 + b[1]) - (a[0] * 60 + a[1])
    except Exception:
        return None


def load_calendar(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _find_week_cols(ws):
    """Spalte -> (Montag-Datum). KW-Zeile ('Kalenderwoche' in Spalte A), erste Wochenspalte E = KW37/2026."""
    kw_row = None
    for r in range(1, 8):
        if _t(ws.cell(r, 1).value).lower().startswith('kalenderwoche'):
            kw_row = r
            break
    if kw_row is None:
        return None, {}
    cols = {}
    c = 5
    if _t(ws.cell(kw_row + 1, 5).value).lower() == 'min':
        # Neues Layout: je Woche zwei Spalten (links Dauer "min", rechts Inhalt); cols[Inhaltsspalte] = Montag
        k = 0
        while c + 1 <= ws.max_column:
            if ws.cell(kw_row, c).value not in (None, ''):
                cols[c + 1] = JP_START + timedelta(days=7 * k)
            c += 2
            k += 1
        return kw_row, cols
    while c <= ws.max_column:
        if ws.cell(kw_row, c).value not in (None, ''):
            cols[c] = JP_START + timedelta(days=7 * (c - 5))
        c += 1
    return kw_row, cols


def _theme_colors(wb):
    try:
        xml = wb.loaded_theme.decode('utf-8') if isinstance(wb.loaded_theme, bytes) else str(wb.loaded_theme)
    except Exception:
        return {}
    names = ['lt1', 'dk1', 'lt2', 'dk2', 'accent1', 'accent2', 'accent3', 'accent4', 'accent5', 'accent6']
    out = {}
    for i, n in enumerate(names):
        m = re.search(r'<a:%s>.*?(?:val|lastClr)="([0-9A-Fa-f]{6})"' % n, xml, re.S)
        if m:
            out[i] = m.group(1)
    return out


def _fill_hex(cell, theme):
    """Fuellfarbe der Excel-Zelle als 'RRGGBB' oder None (ohne Alpha, Theme+Tint aufgeloest)."""
    f = cell.fill
    if f is None or f.fill_type is None:
        return None
    c = f.fgColor
    if c.type == 'rgb' and isinstance(c.rgb, str):
        return c.rgb[-6:].upper()
    if c.type == 'theme' and c.theme in theme:
        base = theme[c.theme]
        r, g, b = int(base[0:2], 16), int(base[2:4], 16), int(base[4:6], 16)
        t = c.tint or 0
        if t > 0:
            r, g, b = [round(x + (255 - x) * t) for x in (r, g, b)]
        elif t < 0:
            r, g, b = [round(x * (1 + t)) for x in (r, g, b)]
        return '%02X%02X%02X' % (r, g, b)
    return None


def _rows(ws, wb=None):
    """Inhaltszeilen ueber Beschriftung in Spalte C (nicht ueber feste Zeilennummern)."""
    out = []
    for r in range(1, ws.max_row + 1):
        lab = _t(ws.cell(r, 3).value)
        if not lab:
            continue
        l = lab.lower()
        if l.replace('-', ' ').startswith('wk sim'):
            continue
        for key, cat, pref, rule in ROWMAP:
            if l.startswith(key):
                dtxt = _t(ws.cell(r, 4).value).lower()[:2]
                out.append({'r': r, 'label': lab, 'cat': cat, 'pref': pref, 'rule': rule,
                            'col': _fill_hex(ws.cell(r, 3), _theme_colors(wb)) if wb is not None else None,
                            'day': None if rule == 'every' else ABBR.get(dtxt)})
                break
    return out


def _head_rows(ws):
    heads = {}
    for r in range(1, 14):
        a = _t(ws.cell(r, 1).value).lower(); b = _t(ws.cell(r, 2).value).lower()
        key = a or b
        if key.startswith('fels'):
            heads['fels'] = r
        elif key.startswith('deload'):
            heads['deload'] = r
        elif key.startswith('schulferien'):
            heads['ferien'] = r
        elif b.startswith('bouldern') or a.startswith('bouldern'):
            heads['wk_b'] = r
        elif b.startswith('world') or a.startswith('world'):
            heads['wk_wc'] = r
        elif b.startswith('lead') or a.startswith('lead'):
            heads['wk_l'] = r
    return heads


def _notizen(wb):
    """date -> {'s1_sonst','s1_ort','s1_notiz','s2_*', red-Flags}"""
    if 'Notizen' not in wb.sheetnames:
        return {}
    ws = wb['Notizen']
    mm = plans2027._merge_map(ws)
    lab = {}
    seq = {'sonstiges': [], 'trainigsort': [], 'trainingsort': [], 'notizen session 1': [], 'notizen session 2': [],
           'datum': []}
    for r in range(1, ws.max_row + 1):
        l = _t(ws.cell(r, 1).value).lower()
        if l in seq:
            seq[l].append(r)
        elif l.startswith('notizen session 1'):
            seq['notizen session 1'].append(r)
        elif l.startswith('notizen session 2'):
            seq['notizen session 2'].append(r)
    ort_rows = seq['trainigsort'] + seq['trainingsort']
    ort_rows.sort()
    dr = seq['datum'][0] if seq['datum'] else None
    if dr is None:
        return {}
    out = {}
    for c in range(2, ws.max_column + 1):
        v = ws.cell(dr, c).value
        d = plans2027._parse_date(v)
        if not d:
            continue

        def cell(rows, i):
            if i < len(rows):
                cc = ws.cell(rows[i], c)
                return _t(plans2027._val(ws, mm, rows[i], c)), plans2027._is_red_font(cc)
            return '', False
        rec = {}
        for i, sfx in ((0, '1'), (1, '2')):
            rec['sonst' + sfx], rec['sonst' + sfx + 'Red'] = cell(sorted(seq['sonstiges']), i)
            rec['ort' + sfx], rec['ort' + sfx + 'Red'] = cell(ort_rows, i)
        rec['notiz1'], rec['notiz1Red'] = cell(seq['notizen session 1'], 0)
        rec['notiz2'], rec['notiz2Red'] = cell(seq['notizen session 2'], 0)
        if any(v for k, v in rec.items() if not k.endswith('Red')):
            out[d.isoformat()] = rec
    return out


def compose(path, make_item, cal, today=None, pause=True, disc=None):
    """-> weeks dict {'YYYY-KW': {'days':[7], 'span','year','kw'}} ab START_DATE.
    disc: nur Gruppen -- {datum: 'Bouldern'|'Lead'} laut Google Kalender. Die Excel enthaelt je Woche Boulder- UND
    Lead-Inhalte; je Tag wird nur die Disziplin des Kalenders uebernommen, ohne Kalendereintrag keine von beiden."""
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception:
        return {}
    if 'Trainingsplanung' not in wb.sheetnames:
        return {}
    ws = wb['Trainingsplanung']
    kw_row, cols = _find_week_cols(ws)
    if not cols:
        return {}
    paired = _t(ws.cell(kw_row + 1, 5).value).lower() == 'min'
    rows = _rows(ws, wb)
    if disc is not None:   # Gruppen: eine Einheit pro Tag (zweite Session nur laut Kalender)
        for _rw in rows:
            _rw['pref'] = 1
    heads = _head_rows(ws)
    noti = _notizen(wb)

    # 1) Inhalte je Datum: items[date] = [(row, text, red)]
    items = {}
    durs = {}        # (Montag, Zeile, Text) -> Minuten aus der Dauer-Spalte ("min")
    disc_skipped = {}  # Datum -> Disziplin-Inhalte, die mangels Kalender-Disziplin nicht uebernommen wurden
    unspecific = []  # (monday, row, text, red) fuer Zeilen ohne Wochentag
    for c, mon in cols.items():
        if mon + timedelta(days=6) < START_DATE:
            continue
        for rw in rows:
            cc = ws.cell(rw['r'], c)
            raw = cc.value
            txt = _t(raw)
            if not txt or txt.lower() in SKIP:
                continue
            red = plans2027._is_red_font(cc)
            _mv = ws.cell(rw['r'], c - 1).value if paired else None
            try:
                dmin = float(str(_mv).replace(',', '.')) if _mv not in (None, '') else None
            except ValueError:
                dmin = None
            for pi, part in enumerate([p.strip() for p in txt.split('\n') if p.strip()]):
                if part.lower() in SKIP:
                    continue
                dow = rw['day']
                m = PREFIX.match(part)
                if rw['label'].lower().startswith(('andré', 'andre')):
                    # Mobi Andre ist immer mittwochs (Floyd, 16.11.2026)
                    dow = 2
                    if m:
                        part = m.group(2).strip()
                elif m:
                    dow = ABBR[m.group(1).lower()]
                    part = m.group(2).strip()
                    if not part:
                        continue
                if dow is None and rw['rule'] == 'every':
                    md = DATE_RE.search(part)
                    if md:
                        yy = int(md.group(3)) if md.group(3) else mon.year
                        yy = yy + 2000 if yy < 100 else yy
                        try:
                            d = date(yy, int(md.group(2)), int(md.group(1)))
                        except ValueError:
                            d = None
                        if d and d >= START_DATE:
                            items.setdefault(d.isoformat(), []).append((rw, part, red))
                            continue
                if dow is None:
                    unspecific.append((mon, rw, part, red))
                else:
                    d = mon + timedelta(days=dow)
                    if d >= START_DATE:
                        if disc is not None:
                            _dl = rw['label'].lower()
                            _isb = _dl.startswith(('technik boulder', 'physis bouldern', 'spezial bouldern'))
                            _isl = _dl.startswith(('technik lead', 'physis lead', 'spezial lead'))
                            if (_isb or _isl) and disc.get(d.isoformat()) != ('Bouldern' if _isb else 'Lead'):
                                if disc.get(d.isoformat()) is None:
                                    disc_skipped.setdefault(d.isoformat(), set()).add('Bouldern' if _isb else 'Lead')
                                continue
                        if dmin and dmin > 0 and pi == 0:
                            durs[(mon.isoformat(), rw['r'], part)] = dmin
                        items.setdefault(d.isoformat(), []).append((rw, part, red))

    # 2) Zeilen ohne Wochentag
    by_week = {}
    for mon, rw, part, red in unspecific:
        by_week.setdefault(mon, []).append((rw, part, red))
    for mon, lst in by_week.items():
        days_with = [(mon + timedelta(days=i)).isoformat() for i in range(7)
                     if (mon + timedelta(days=i)).isoformat() in items and
                     any(r['cat'] in ('Technik/Taktik', 'Physis Klettern', 'Athletik + Mentales')
                         for r, _, _ in items[(mon + timedelta(days=i)).isoformat()])]
        for rw, part, red in lst:
            rule = rw['rule']
            if rule == 'allday':
                targets = days_with
            elif rule == 'bbday':
                targets = [x for x in days_with
                           if any(r['label'].lower().startswith(('technik boulder', 'physis bouldern'))
                                  for r, _, _ in items[x])][:3]
            elif rule == 'every':
                # Spezial: jeder Trainingstag der Woche (Kalendertermin oder Trainingsinhalt), unabhaengig von Tag/Dauer
                targets = sorted(set(days_with) | {(mon + timedelta(days=i)).isoformat() for i in range(7)
                                                   if (mon + timedelta(days=i)).isoformat() in cal})
            else:  # firstday
                targets = days_with[:1]
            for x in targets:
                if date.fromisoformat(x) >= START_DATE:
                    items.setdefault(x, []).append((rw, part, red))

    # 3) Tage zusammenbauen
    alldays = set(items) | {k for k in noti if date.fromisoformat(k) >= START_DATE} | \
        {k for k in cal if date.fromisoformat(k) >= START_DATE}
    weeks = {}
    for iso in sorted(alldays):
        dt = date.fromisoformat(iso)
        y, kw, wd = dt.isocalendar()
        evs = list(cal.get(iso, []))
        nt = noti.get(iso, {})
        day_items = items.get(iso, [])
        need2 = any(rw['pref'] == 2 for rw, _, _ in day_items)
        has_content = bool(day_items)
        n_sess = max(len(evs), 2 if (need2 and has_content and (len(evs) >= 1 or True)) else (1 if has_content else 0))
        if nt.get('sonst2') or nt.get('notiz2') or nt.get('ort2'):
            n_sess = max(n_sess, 2)
        if n_sess == 0 and nt.get('notiz1'):
            n_sess = 1
        sessions = []
        for si in range(n_sess):
            ev = evs[si] if si < len(evs) else None
            s = {'name': 'Session %d' % (si + 1), 'time': ev['s'] if ev else '', 'ort': None, 'ortRed': False,
                 'cats': [{'name': n, 'items': []} for n in CATS], 'notiz': None, 'notizRed': False,
                 'sonstiges': None}
            if ev:
                s['end'] = ev['e']
                s['dur'] = _mins(ev['s'], ev['e'])
                s['trainer'] = ev['t'] + (' (%s)' % ev['x'] if ev.get('x') else '')
            sessions.append(s)
        # Inhalte verteilen
        for rw, part, red in day_items:
            si = 0
            if rw['pref'] == 2 and n_sess >= 2:
                si = 1
            cat = next(c for c in sessions[si]['cats'] if c['name'] == rw['cat'])
            lab_l = rw['label'].lower()
            text = part
            # Kopfzeilen-Namen nicht doppelt: bei Finger/Core usw. 'Label: Text' nur wenn Text kurz und anders
            it = make_item(text, red)
            if lab_l.startswith(('finger 2', 'aufleger', 'zangen', 'ziehen', 'campus', 'hangeln', 'stütz', 'core',
                                 'handgelenk', 'athletik', 'beweglichkeit')) and rw['cat'] == 'Athletik + Mentales':
                if text.lower() != rw['label'].lower() and not text.lower().startswith(rw['label'].lower()):
                    it = make_item('%s: %s' % (rw['label'], text), red)
            if rw.get('col'):
                it['col'] = rw['col']
            _dm = durs.get(((dt - timedelta(days=wd - 1)).isoformat(), rw['r'], part))
            if _dm:   # Dauer aus der "min"-Spalte hat Vorrang vor Zeitangaben im Text
                it['explicitTime'] = '%d min' % round(_dm)
                it['dur'] = round(_dm)
            if lab_l.startswith('taktik 2'):
                it['par'] = True   # Taktik 2 (mid Session) laeuft nebenher (Floyd 16.11.2026)
            cat['items'].append(it)
        # doppelte Items entfernen
        for s in sessions:
            for c in s['cats']:
                seen = set(); keep = []
                for it in c['items']:
                    k = it['ex'].lower()
                    if k in seen:
                        continue
                    seen.add(k); keep.append(it)
                c['items'] = keep
        # Essen/Trinken (Trinkpause): laut Standardwoche SPOGY fest am Dienstag, 10 min, nach Technik/Taktik und vor Physis (Session 1)
        if pause and wd == 2 and sessions and any(c['items'] for c in sessions[0]['cats'] if c['name'] in ('Technik/Taktik', 'Physis Klettern')):
            _tc = next(c for c in sessions[0]['cats'] if c['name'] == 'Technik/Taktik')
            _pi = make_item('Essen / Trinken', False)
            _pi['match'] = {}
            _pi['explicitTime'] = '10 min'
            _pi['col'] = 'DDEBF7'
            _pi['pause'] = True
            _tc['items'].append(_pi)
        # Notizen (haben Vorrang)
        for si, s in enumerate(sessions):
            sfx = str(si + 1)
            nz = nt.get('notiz' + sfx)
            if nz:
                s['notiz'] = nz; s['notizRed'] = bool(nt.get('notiz' + sfx + 'Red'))
            if nt.get('ort' + sfx):
                s['ort'] = nt['ort' + sfx]; s['ortRed'] = bool(nt.get('ort' + sfx + 'Red'))
        # Ort/Trainer/Zeit aus Kalender
        windows = [('%s-%s' % (e['s'], e['e'])) for e in evs if e.get('c') != '1' or True]
        trainers = []
        for e in evs:
            if e['t'] and e['t'] not in trainers:
                trainers.append(e['t'])
        ortType = None
        for e in evs:
            ot = {'7': 'Bouldern', '10': 'Lead', '5': 'Speed'}.get(str(e.get('c')))
            if ot:
                ortType = ot
                break
        ortname = {'Bouldern': 'SB Dornbirn', 'Lead': 'K1', 'Speed': None}.get(ortType)
        if 'Christian' in trainers:
            ortname = None
        day = {'dow': DOW[wd - 1], 'dom': dt.strftime('%d.%m.'), 'date': iso,
               'ort': ortname or next((s['ort'] for s in sessions if s.get('ort')), None),
               'sonstiges': None, 'sessions': sessions, 'doku': None, 'notiz': None}
        if ortType:
            day['ortType'] = ortType
        if evs:
            day['zeit'] = ' · '.join(windows)
            day['trainer'] = ' · '.join(trainers)
            day['sonstiges'] = 'mit ' + ' & '.join(trainers)
        # Notizen-'Sonstiges' (z. B. '18:00 mit Mark') nur als Fallback, wenn Kalender nichts hat
        sonst = ' · '.join(x for x in (nt.get('sonst1'), nt.get('sonst2')) if x)
        if sonst:
            if not evs:
                day['sonstiges'] = sonst
                day['sonstigesRed'] = bool(nt.get('sonst1Red') or nt.get('sonst2Red'))
                m = re.match(r'^\s*(\d{1,2})[:.](\d{2})\s*(?:mit\s+\w+)?\s*$', nt.get('sonst1') or '', re.I)
                if m and sessions:
                    sessions[0]['time'] = '%02d:%s' % (int(m.group(1)), m.group(2))
            else:
                extra = [x for x in (nt.get('sonst1'), nt.get('sonst2'))
                         if x and not TIME_RE.fullmatch(x.strip())
                         and not re.fullmatch(r'\d{1,2}[:.]\d{2}\s*(mit\s+\w+)?', x.strip(), re.I)]
                if extra:
                    day['notiz'] = ' · '.join(extra)
                    day['notizRed'] = bool(nt.get('sonst1Red') or nt.get('sonst2Red'))
        if iso in disc_skipped:
            _n = 'Bouldern/Lead laut Google Kalender noch offen – Technik-/Physis-Inhalte folgen'
            day['notiz'] = (day['notiz'] + ' · ' + _n) if day.get('notiz') else _n
        # Kopfzeilen: Fels / Deload / Ferien als Hinweis
        wk = weeks.setdefault('%d-%d' % (y, kw), {'days': {}, 'year': y, 'kw': kw})
        wk['days'][wd - 1] = day

    # Kopfzeilen-Hinweise je Woche (Fels, Deload) an den Tagen
    for c, mon in cols.items():
        for hk in ('fels', 'deload'):
            if hk in heads:
                v = _t(ws.cell(heads[hk], c - 1 if paired else c).value)
                if v:
                    y, kw, _ = mon.isocalendar()
                    wk = weeks.get('%d-%d' % (y, kw))
                    if wk:
                        for dd in wk['days'].values():
                            dd.setdefault('wochenhinweis', [])
                            tag = ('Fels: ' if hk == 'fels' else 'Deload: ') + v
                            if tag not in dd['wochenhinweis']:
                                dd['wochenhinweis'].append(tag)

    out = {}
    for key, wk in weeks.items():
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
        out[key] = {'days': days, 'span': '%s – %s' % (mon.strftime('%d.%m.'), sun.strftime('%d.%m.%Y')),
                    'year': wk['year'], 'kw': wk['kw']}
    return out
