// Aktualisiert NUR eine Gruppe (env GKEY z.B. 'g:U15 II') auf Basis des letzten committeten Live-Stands (HEAD).
const fs=require('fs'),crypto=require('crypto');
const H=process.env.TP_TMP+'/', GKEYS=process.env.GKEY.split('|');
const raw=fs.readFileSync(H+'prev.enc.js','utf8');
const u=JSON.parse(raw.slice(raw.indexOf('{'),raw.lastIndexOf('}')+1));
const key=crypto.pbkdf2Sync(process.env.TP_PASSWORD,Buffer.from(u.salt,'base64'),u.iterations,32,'sha256');
const ct=Buffer.from(u.ct,'base64');
const dc=crypto.createDecipheriv('aes-256-gcm',key,Buffer.from(u.iv,'base64'));dc.setAuthTag(ct.slice(-16));
const prev=JSON.parse(Buffer.concat([dc.update(ct.slice(0,-16)),dc.final()]).toString('utf8'));
const cur=JSON.parse(fs.readFileSync(H+'tp-data.gruppe.js','utf8').trim().slice('window.TPDATA = '.length).replace(/;\s*$/,''));
const TODAY=new Date().toISOString().slice(0,10);
let setN=0,clrN=0;
for(const GKEY of GKEYS){ const GID=GKEY.slice(2);
const take=(f,k)=>{ if(cur[f]&&cur[f][k]!==undefined){ prev[f]=prev[f]||{}; prev[f][k]=cur[f][k]; } };
for(const f of ['PLANS','CATS_BY_VIEW','SOURCE_INFO','JAHRESPLAN2027','PLANS2027_INFO']) take(f,GKEY);
for(const f of ['JAHRESPLAN_GROUP','JAHRESPLAN_GROUP_SOURCE']) take(f,GID);
for(const sn of Object.keys(cur.SEASON_STATS||{})){ if(cur.SEASON_STATS[sn][GKEY]!==undefined){ prev.SEASON_STATS[sn]=prev.SEASON_STATS[sn]||{}; prev.SEASON_STATS[sn][GKEY]=cur.SEASON_STATS[sn][GKEY]; } }
// Trainingsorte laut Google Kalender
const ok=JSON.parse(fs.readFileSync('build/ort_kalender.json','utf8')); const ORT={Bouldern:'SB Dornbirn',Lead:'K1'};
const all=Object.values(ok).flatMap(o=>Object.keys(o)).sort(); const HORIZON=all[all.length-1];
const P=prev.PLANS[GKEY]||{}; if(ok[GID]) for(const w of Object.values(P)) for(const d of (w.days||[])){
  if(d.date<TODAY||d.date>HORIZON) continue;
  const t=ok[GID][d.date];
  if(t){ if(d.ort!==ORT[t]||d.ortType!==t) setN++; d.ort=ORT[t]; d.ortType=t; }
  else if(d.ort||d.ortType){ d.ort=null; d.ortType=null; clrN++; }
}
}
prev.EXHOW=Object.assign(prev.EXHOW||{},cur.EXHOW||{});
const _p=n=>String(n).padStart(2,'0');
{const f=new Intl.DateTimeFormat('de-AT',{timeZone:'Europe/Vienna',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).formatToParts(new Date()).reduce((o,x)=>(o[x.type]=x.value,o),{});
prev.GENERATED=f.day+'.'+f.month+'.'+f.year+', '+f.hour+':'+f.minute;}
fs.writeFileSync('tp-data.js','window.TPDATA = '+JSON.stringify(prev)+';\n');
console.log('Gruppen',GKEYS.join(','),'aktualisiert; Orte aus Kalender gesetzt',setN,'geleert',clrN);
