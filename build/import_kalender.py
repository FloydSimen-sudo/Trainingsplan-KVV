#!/usr/bin/env python3
"""Google-Kalender (KVV Gesamt) -> gruppen_kalender.json / ort_kalender.json / entfaellt_kalender.json.
Eingabe: cal_events_raw.json = [[YYYY-MM-DD, start, ende, colorId, titel], ...]. Ersetzt den Zeitraum ab START
fuer die 7 Gruppen. Abgesagte Trainings bleiben als Eintrag (x='entfällt') erhalten, damit der Tag als Kalendertag zaehlt."""
import json,re,sys
rows=json.load(open('cal_events_raw.json'))
g=json.load(open('gruppen_kalender.json'));o=json.load(open('ort_kalender.json'));ef=json.load(open('entfaellt_kalender.json'))
MAP={'U9':('U9','U9'),'U11 I':('U11 I','U11I'),'U11 II':('U11 II','U11II'),'U13 I':('U13 I','U13 I'),'U13 II':('U13 II','U13II'),'U15 I':('U15 I','U15I'),'U15 II':('U15 II','U15 II')}
GR=re.compile(r'^U(9|11|13|15)\s*(II|I)?(?=\s|$)')
START=sys.argv[1] if len(sys.argv)>1 else '2026-11-16'
END=max(r[0] for r in rows)
for f27,gid in MAP.values():
    g.setdefault(f27,{}); o.setdefault(gid,{})
    for d in [d for d in g[f27] if START<=d<=END]: del g[f27][d]
    for d in [d for d in o[gid] if START<=d<=END]: del o[gid][d]
col={'7':'Bouldern','10':'Lead'}
def add(key,d,ent,disc=None):
    f27,gid=MAP[key]
    g[f27].setdefault(d,[]).append(ent)
    if disc: o[gid][d]=disc
for d,s,e,c,t in rows:
    if d<START or t.startswith('U9-U13'): continue
    m=re.match(r'^U15\s*I\s*\+\s*U15\s*II\s*(.*)$',t)
    if m:
        rest=m.group(1)
        pm=re.search(r'\((.*)\)',rest); x=pm.group(1) if pm else ''
        who=re.sub(r'\(.*\)','',rest).strip()
        if 'entf' in t.lower():
            for k in ('U15 II','U15I'): ef.setdefault(k,{})[d]={'r':'Athletik OZ entfällt','p':1}
            continue
        for k in ('U15 I','U15 II'): add(k,d,{'s':s,'e':e,'t':who,'x':x,'c':''})
        continue
    m=GR.match(t)
    if not m: continue
    key='U%s%s'%(m.group(1),(' '+m.group(2)) if m.group(2) else '')
    if key not in MAP: continue
    rest=t[m.end():].strip()
    if 'entf' in rest.lower():
        r=re.sub(r'(?i)^.*?entf\w+\s*','',rest).strip()
        ef.setdefault(MAP[key][1],{})[d]={'r':r}
        add(key,d,{'s':s,'e':e,'t':'','x':'entfällt','c':''})
        continue
    pm=re.search(r'\((.*)\)',rest); x=pm.group(1) if pm else ''
    rest=re.sub(r'\(.*\)','',rest).strip()
    if 'Rotation' in rest: x=('Rotation'+(', '+x if x else '')); rest=rest.replace('Rotation','').strip()
    if 'selbst' in rest.lower(): x='selbstständig'; rest=''
    add(key,d,{'s':s,'e':e,'t':rest,'x':x,'c':c},col.get(c))
json.dump(g,open('gruppen_kalender.json','w'),ensure_ascii=False,indent=1)
json.dump(o,open('ort_kalender.json','w'),ensure_ascii=False,indent=1)
json.dump(ef,open('entfaellt_kalender.json','w'),ensure_ascii=False,indent=1)
print('ok',START,END)
