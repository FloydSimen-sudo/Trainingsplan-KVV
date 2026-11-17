# -*- coding: utf-8 -*-
"""Dauer-Fallback aus 'Standardwoche SPOGY.xlsx' (Floyd, Stand 16.11.2026) fuer Einzelathleten.
Prioritaet in der App: Zeit in der Excel-Zelle > Dauer aus Uebungssammlung Gesamt > Standardwoche (hier, durSrc='std').
Nur fuer Inhalte ohne eigene Dauer. Nichts wird erfunden: ohne Eintrag in der Standardwoche bleibt die Dauer leer ('-')."""
import re
from datetime import date

# Block-Minuten je Wochentag (0=Mo ... 6=So), gelesen aus Standardwoche SPOGY.xlsx
BLOCK = {
    'bb':      {0: 30, 1: 75, 3: 30, 4: 90, 6: 120},   # Technik Taktik 1 (BB frei/WK/Farbboulder/offen)
    'physis':  {0: 90, 1: 60, 3: 30, 4: 60, 6: 30},    # Physis Klettern 1 (Wand)
    'lead':    {3: 180, 6: 120},                       # Technik Taktik 2 (Lead), Session 2
    'warm':    {1: 30, 3: 30},                         # Aufwaermen
    'theorie': {1: 15, 2: 60, 3: 5},                   # Theorie / Input
}
# Athletik-Einzelinhalte: (Regex, Minuten oder {Wochentag: Minuten})
ATH = [
    (r'jule', 90),
    (r'mobi\s*andr|mobility\s*\(?andr', 60),
    (r'jogg', 30),
    (r'passives dehnen|dehnen', {1: 5, 6: 15, 'x': 15}),
    (r'aktive mobility|mobility|mobi', {'x': 15}),
    (r'^finger|finger \d|individuell finger|long max|max hang|tendon|pinch|zangen|aufleger', {'x': 30}),
    (r'ziehen|athletik|klimmzug|rudern|campus|hangeln|stütz|core|handgelenk|curl|beweglichkeit', {4: 30, 'x': 30}),
]
# Typischer Standardwert, wenn der Wochentag in der Standardwoche keinen Block hat (Floyd, 16.11.: immer an Standardwoche orientieren)
TYPICAL = {'bb': 75, 'physis': 60, 'lead': 180, 'warm': 30, 'theorie': 15}
WALL = ('bb', 'physis', 'lead')  # Blocks an der Wand
USE_ITEM_STD = False  # Floyd 16.11.: Inhalte ohne Dauer in Excel/Uebungssammlung bleiben ohne Dauer ('-')
STD_DAY = {0: 120, 1: 285, 2: 150, 3: 305, 4: 195, 5: 30, 6: 165}  # Summe je Wochentag laut Standardwoche SPOGY
EXPL = re.compile(r'(\d+(?:[.,]\d+)?)\s*(h|std|stunden?|min)\b', re.I)


def _known(it, parse_dauer):
    e = str(it.get('explicitTime') or '')
    m = EXPL.search(e)
    if m:
        v = float(m.group(1).replace(',', '.'))
        return round(v * 60) if m.group(2).lower() != 'min' else round(v)
    mm = it.get('match') or {}
    v = mm.get('min')
    if v not in (None, '', 'x'):
        p = parse_dauer(v)
        if p:
            return round(p)
    return None


def apply(plans, parse_dauer):
    n_set = 0
    for key, weeks in plans.items():
        if not key.startswith(('a:', 'g:')):
            continue
        for w in weeks.values():
            for day in w.get('days', []):
                try:
                    wd = date.fromisoformat(day['date']).weekday()
                except Exception:
                    continue
                groups = {}
                wall = any(c['name'] in ('Technik/Taktik', 'Physis Klettern') and any(not i.get('pause') for i in c.get('items', []))
                           for se_ in day.get('sessions', []) for c in se_.get('cats', []))
                for si, s in enumerate(day.get('sessions', [])):
                    for c in s.get('cats', []):
                        for it in c.get('items', []):
                            it.pop('dur', None); it.pop('durSrc', None)
                            if re.search(r'jongl', str(it.get('ex') or ''), re.I):
                                it['par'] = True   # Floyd 16.11.: Jonglieren laeuft immer mit, keine Standarddauer
                                continue
                            if it.get('par'):
                                continue
                            if it.get('pause'):
                                it['dur'] = 10; it['durSrc'] = 'excel'
                                continue
                            k = _known(it, parse_dauer)
                            if k:
                                it['dur'] = k
                                it['durSrc'] = 'excel' if it.get('explicitTime') else 'sammlung'
                            g = None
                            if c['name'] == 'Aufwärmen':
                                g = 'warm'
                            elif c['name'] == 'Theorie':
                                g = 'theorie'
                            elif c['name'] == 'Technik/Taktik':
                                g = 'lead' if si >= 1 else 'bb'
                            elif c['name'] == 'Physis Klettern':
                                g = 'lead' if si >= 1 else 'physis'
                            elif USE_ITEM_STD and c['name'] == 'Athletik + Mentales' and not k:
                                t = str(it.get('ex') or '').lower()
                                for rx, mins in ATH:
                                    if re.search(rx, t):
                                        v = (mins.get(wd, mins.get('x')) if isinstance(mins, dict) else mins)
                                        if v:
                                            it['dur'] = v; it['durSrc'] = 'std'; n_set += 1
                                        break
                            if g:
                                groups.setdefault(g, []).append((it, k))
                for g, lst in (groups.items() if USE_ITEM_STD else []):
                    tot = BLOCK[g].get(wd)
                    if not tot and g == 'warm' and not wall:
                        continue   # kein Wandtraining an diesem Tag: kein Standard-Warm-Up erfinden
                    if not tot:
                        tot = TYPICAL[g]
                    known = sum(k for _, k in lst if k)
                    unk = [it for it, k in lst if not k]
                    rem = tot - known
                    if not unk or rem <= 0:
                        continue
                    each = max(5, int(round(rem / len(unk) / 5.0)) * 5)
                    for it in unk:
                        it['dur'] = each; it['durSrc'] = 'std'; n_set += 1
    return n_set


def apply_diff(plans):
    """Floyd 16.11.2026: Inhalte ohne Zeit in der Excel und ohne Dauer in der Uebungssammlung bekommen die Differenz zur
    geplanten Gesamtdauer der Session (aus dem Google Kalender). Aufteilung nach Standardwoche-Gewichten, sonst gleichmaessig."""
    n = 0
    for key, weeks in plans.items():
        if not key.startswith(('a:', 'g:')):
            continue
        for w in weeks.values():
            for day in w.get('days', []):
                for s in day.get('sessions', []):
                    D = s.get('dur')
                    if not D:
                        continue
                    items = [it for c in s.get('cats', []) for it in c.get('items', [])]
                    known = sum(it.get('dur') or 0 for it in items if it.get('durSrc') in ('excel', 'sammlung') or it.get('pause'))
                    unk = [it for it in items if not it.get('par') and not it.get('pause') and it.get('durSrc') not in ('excel', 'sammlung')]
                    rem = D - known
                    if not unk or rem < 5:
                        continue
                    wts = [it.get('dur') if it.get('durSrc') == 'std' and it.get('dur') else None for it in unk]
                    have = [x for x in wts if x]
                    mean = (sum(have) / len(have)) if have else 1
                    wts = [x if x else mean for x in wts]
                    tot = float(sum(wts))
                    for it, wt in zip(unk, wts):
                        it['dur'] = max(5, int(round(rem * wt / tot / 5.0)) * 5)
                        it['durSrc'] = 'diff'
                        n += 1
    return n


def apply_total(plans):
    """Gesamte Trainingszeit je Tag: Summe der Kalender-Sessions, sonst Summe der Standardwoche SPOGY (day['totMin'], day['totSrc'])."""
    n = 0
    for key, weeks in plans.items():
        if not key.startswith(('a:', 'g:')):
            continue
        for w in weeks.values():
            for day in w.get('days', []):
                day.pop('totMin', None); day.pop('totSrc', None)
                if not day.get('sessions'):
                    continue
                iv = []
                for s_ in day['sessions']:
                    try:
                        a = [int(x) for x in str(s_.get('time')).split(':')[:2]]; b = [int(x) for x in str(s_.get('end')).split(':')[:2]]
                        if s_.get('dur'):
                            iv.append((a[0] * 60 + a[1], b[0] * 60 + b[1]))
                    except Exception:
                        pass
                iv.sort(); cal = 0; cur = None
                for a_, b_ in iv:   # Vereinigung, damit sich ueberlappende Termine nicht doppelt zaehlen
                    if cur and a_ <= cur[1]:
                        cur = (cur[0], max(cur[1], b_))
                    else:
                        if cur: cal += cur[1] - cur[0]
                        cur = (a_, b_)
                if cur: cal += cur[1] - cur[0]
                if cal:
                    day['totMin'] = cal; day['totSrc'] = 'Kalender'
                else:
                    if not key.startswith('a:'):
                        continue   # Standardwoche SPOGY gilt nur fuer Einzelathleten
                    try:
                        wd = date.fromisoformat(day['date']).weekday()
                    except Exception:
                        continue
                    if STD_DAY.get(wd):
                        day['totMin'] = STD_DAY[wd]; day['totSrc'] = 'Standardwoche'
                if day.get('totMin'):
                    n += 1
    return n
