const fs=require('fs'),crypto=require('crypto');
const H=process.env.TP_TMP+'/';
const raw=fs.readFileSync(H+'prev.enc.js','utf8');
const u=JSON.parse(raw.slice(raw.indexOf('{'),raw.lastIndexOf('}')+1));
const key=crypto.pbkdf2Sync(process.env.TP_PASSWORD,Buffer.from(u.salt,'base64'),u.iterations,32,'sha256');
const ct=Buffer.from(u.ct,'base64');
const dc=crypto.createDecipheriv('aes-256-gcm',key,Buffer.from(u.iv,'base64'));dc.setAuthTag(ct.slice(-16));
const prev=JSON.parse(Buffer.concat([dc.update(ct.slice(0,-16)),dc.final()]).toString('utf8'));
const cur=JSON.parse(fs.readFileSync(H+'tp-data.einzel.js','utf8').trim().slice('window.TPDATA = '.length).replace(/;\s*$/,''));
const TODAY=new Date().toISOString().slice(0,10), START='2026-11-02';
const MAIN=['Technik/Taktik','Physis Klettern','Aufwärmen'];
const hasMain=d=>(d.sessions||[]).some(s=>s.cats.some(c=>MAIN.includes(c.name)&&c.items.length));
let keptPast=0,newDays=0;
for(const k of Object.keys(cur.PLANS).filter(k=>k.startsWith('a:'))){
  const pp=prev.PLANS[k]||{}, np=cur.PLANS[k], out={};
  for(const wk of new Set([...Object.keys(pp),...Object.keys(np)])){
    const pw=pp[wk], nw=np[wk];
    if(!nw){out[wk]=pw;continue}
    if(!pw){out[wk]=nw;continue}
    const w=JSON.parse(JSON.stringify(nw));
    w.days=nw.days.map((nd,i)=>{
      const pd=pw.days[i];
      if(nd.date<START) return pd||nd;
      if(pd&&nd.date<TODAY&&hasMain(pd)){
        keptPast++;
        const d=JSON.parse(JSON.stringify(pd));
        for(const f of ['zeit','trainer','ortType','ort','notiz','notizRed']) if(nd[f]!==undefined&&nd[f]!==null) d[f]=nd[f];
        (d.sessions||[]).forEach((s,j)=>{const n=(nd.sessions||[])[j]; if(n) for(const f of ['time','end','dur','trainer']) if(n[f]) s[f]=n[f]});
        return d;
      }
      newDays++;
      if(pd&&pd.doku&&!nd.doku) nd.doku=pd.doku;
      return nd;
    });
    out[wk]=w;
  }
  // Mobi Andre ist immer mittwochs: an anderen Tagen entfernen, in der Woche am Mittwoch ergaenzen
  const isMobi=it=>/mobi\s*andr/i.test(it.ex||'');
  for(const wk of Object.keys(out)){
    const w=out[wk]; if(!w||!w.days) continue;
    let moved=null;
    w.days.forEach((d,i)=>{ if(i===2) return;
      (d.sessions||[]).forEach(s=>s.cats.forEach(c=>{ const keep=c.items.filter(it=>!isMobi(it)); if(keep.length!==c.items.length){ moved=moved||c.items.find(isMobi); c.items=keep; } })); });
    const wed=w.days[2];
    if(moved&&wed){
      const has=(wed.sessions||[]).some(s=>s.cats.some(c=>c.items.some(isMobi)));
      if(!has&&wed.sessions&&wed.sessions.length){
        const c=wed.sessions[0].cats.find(c=>c.name==='Athletik + Mentales'); if(c) c.items.push(moved);
      }
    }
  }
  prev.PLANS[k]=out;
  for(const f of ['JAHRESPLAN2027','PLANS2027_INFO']) if(cur[f]&&cur[f][k]!==undefined){prev[f]=prev[f]||{};prev[f][k]=cur[f][k];}
  const nm=k.slice(2);
  for(const f of ['JAHRESPLAN','JAHRESPLAN_SOURCE']) if(cur[f]&&cur[f][nm]!==undefined){prev[f]=prev[f]||{};prev[f][nm]=cur[f][nm];}
}
// Jahresplanung der Gruppen (nur Jahresplan, keine Einheiten) ebenfalls aktualisieren
for(const k of Object.keys(cur.JAHRESPLAN2027||{}).filter(k=>k.startsWith('g:'))){prev.JAHRESPLAN2027=prev.JAHRESPLAN2027||{};prev.JAHRESPLAN2027[k]=cur.JAHRESPLAN2027[k];}
for(const f of ['JAHRESPLAN_GROUP','JAHRESPLAN_GROUP_SOURCE']) if(cur[f]){prev[f]=prev[f]||{};for(const g of Object.keys(cur[f])) prev[f][g]=cur[f][g];}
// Trainingsorte der Gruppen laut Google Kalender "KVV Gesamt" (build/ort_kalender.json: Farbe 7 = Bouldern/SB Dornbirn, 10 = Lead/K1).
// Kalender gewinnt: Ort+Typ werden gesetzt; Tage ohne Termin der Gruppe im gefaerbten Zeitraum verlieren den Ort. Inhalte bleiben unveraendert.
{
  const ok=JSON.parse(fs.readFileSync('build/ort_kalender.json','utf8'));
  const ORT={Bouldern:'SB Dornbirn',Lead:'K1'};
  const all=Object.values(ok).flatMap(o=>Object.keys(o)).sort(); const HORIZON=all[all.length-1];
  let setN=0,clrN=0;
  for(const gid of Object.keys(ok)){
    const P=prev.PLANS['g:'+gid]; if(!P) continue;
    for(const w of Object.values(P)) for(const d of (w.days||[])){
      if(d.date<TODAY||d.date>HORIZON) continue;
      const t=ok[gid][d.date];
      if(t){ if(d.ort!==ORT[t]||d.ortType!==t){setN++;} d.ort=ORT[t]; d.ortType=t; }
      else if(d.ort||d.ortType){ d.ort=null; d.ortType=null; clrN++; }
    }
  }
  console.log('Gruppen-Orte aus Kalender: gesetzt/geaendert',setN,' geleert (kein Termin im Kalender)',clrN,' bis',HORIZON);
}
prev.EXHOW=Object.assign(prev.EXHOW||{},cur.EXHOW||{});
fs.writeFileSync('tp-data.js','window.TPDATA = '+JSON.stringify(prev)+';\n');
console.log('Vergangene Tage mit altem Inhalt:',keptPast,' neu zusammengesetzte Tage:',newDays);
