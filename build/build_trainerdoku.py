#!/usr/bin/env python3
"""Trainerspace: liest 'Trainer Doku.xlsx' (Forms-Antworten der Trainer:innen) und
schreibt build/trainer-plain.json (Klartext, .gitignored). Danach:
  TP_PASSWORD_DUMMY= node build/encrypt_trainerdoku.js  -> trainer-data.enc.js (wird committet)

Zugaenge: build/trainer_access.local.json (.gitignored, enthaelt die Klartext-Passwoerter!).
Wird beim ersten Lauf automatisch erzeugt (Trainer:innen + ihre Gruppen aus tp-data.js,
Floyd Simen = alle Gruppen). Danach von Hand pflegbar (Passwoerter/Gruppen aendern)."""
import json, os, re, secrets, sys, openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BASE = os.environ.get('TP_BASE') or os.path.expanduser('~/mnt/Trainingsplanung Live/')
SRC = os.path.join(BASE, 'Trainer Doku.xlsx')
ACCESS = os.path.join(HERE, 'trainer_access.local.json')
PLAIN = os.path.join(HERE, 'trainer-plain.json')

raw = open(os.path.join(REPO, 'tp-data.js'), encoding='utf-8').read().strip()
tp = json.loads(raw[len('window.TPDATA = '):].rstrip(';'))
GROUPS = tp['GROUPS']
def norm(s): return re.sub(r'\s+', '', str(s or '')).upper()
GID_BY_NORM = {norm(g['id']): g['id'] for g in GROUPS}
GID_BY_NORM['SPOGY'] = 'SPOGY Gruppe'
LABEL = {'U11I':'U11 I','U11II':'U11 II','U13 I':'U13 I','U13II':'U13 II','U15I':'U15 I','U15 II':'U15 II','SPOGY Gruppe':'SPOGY','U9':'U9'}

def password():
    C, V = 'bdfgklmnprstvz', 'aeiou'
    syl = lambda: ''.join(secrets.choice(C) + secrets.choice(V) for _ in range(2)).capitalize()
    return '-'.join(syl() for _ in range(3)) + '-' + str(secrets.randbelow(90) + 10)

def split_names(s): return [n.strip() for n in str(s or '').split('+') if n.strip()]

# --- Zugaenge
if os.path.exists(ACCESS):
    access = json.load(open(ACCESS, encoding='utf-8'))
else:
    by_trainer = {}
    for g in GROUPS:
        for n in split_names(g.get('coaches')):
            by_trainer.setdefault(n, []).append(g['id'])
    by_trainer['Floyd Simen'] = [g['id'] for g in GROUPS]
    access = {'users': [{'name': n, 'password': password(), 'groups': gs} for n, gs in by_trainer.items()]}
    json.dump(access, open(ACCESS, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('Zugaenge neu erzeugt:', ACCESS)
pws = [u['password'] for u in access['users']]
assert len(set(pws)) == len(pws), 'doppelte Passwoerter'

# --- Eintraege
entries = {g['id']: [] for g in GROUPS}
unmatched = []
if os.path.exists(SRC):
    ws = openpyxl.load_workbook(SRC, data_only=True).worksheets[0]
    hdr = [str(c.value or '') for c in ws[1]]
    def col(*needles):
        for i, h in enumerate(hdr):
            if all(n in h.lower() for n in needles): return i
    c_ts, c_g, c_fok, c_day, c_um, c_not = col('startzeit'), col('gruppe'), col('fokus'), col('anderen tag'), col('umgesetzt'), col('notizen')
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or r[c_g] is None: continue
        gid = GID_BY_NORM.get(norm(r[c_g]))
        if not gid: unmatched.append(str(r[c_g])); continue
        ts = r[c_ts]; day = r[c_day] or ts
        um = str(r[c_um] or '').strip().lower()
        entries[gid].append({
            'date': day.date().isoformat() if hasattr(day, 'date') else None,
            'fokus': (str(r[c_fok]).strip() if r[c_fok] else None),
            'umsetzung': True if um == 'ja' else (False if um == 'nein' else None),
            'notiz': (str(r[c_not]).strip() if r[c_not] else None),
            'ts': ts.isoformat() if hasattr(ts, 'isoformat') else None,
        })
for g in entries.values(): g.sort(key=lambda e: (e['date'] or '', e['ts'] or ''), reverse=True)

out = {'groups': [{'id': g['id'], 'label': LABEL.get(g['id'], g['id'])} for g in GROUPS],
       'entries': entries, 'access': [{'name': u['name'], 'password': u['password'], 'groups': u['groups']} for u in access['users']]}
json.dump(out, open(PLAIN, 'w', encoding='utf-8'), ensure_ascii=False)
print('Trainer-Doku:', sum(len(v) for v in entries.values()), 'Eintraege; Zugaenge:', len(access['users']), '; unzugeordnet:', unmatched)
