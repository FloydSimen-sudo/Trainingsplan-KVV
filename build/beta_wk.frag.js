// ---- Wettkaempfe aus der Jahresplanung (JAHRESPLAN2027[key].wk, Quelle: WK-Zeilen der Trainingsplanung) ----
const BT_WK_PREFIX = ['Wild Cartd A-Cup','Wild Card A-Cup Lead','Wild Card A-Cup','A-Cup Lead','A-Cup L','A-Cup S','A-Cup','EYCH L','EYCH','EYC L','EYC','EC L','EC','WC','WM','OQ','ÖSTM Lead','ÖSTM','ÖM L','ÖM','LM','West Cup','Kids House MS','House MS','Talents Cup','Arge Alp','Jugend-WM','WYCH'];
const BT_DISC = {B:'Bouldern', L:'Lead', S:'Speed'};
function btParseWk(text, kind){
  const parts = String(text||'').split(/\s+\/\s+(?=[A-Za-zÖ])/);
  return parts.map(p=>{
    let range = null, m;
    if((m = /(\d{1,2})\.(\d{1,2})\.\s*[-–\/]\s*(\d{1,2})\.(\d{1,2})\./.exec(p))) range = [(+m[2])*100+(+m[1]), (+m[4])*100+(+m[3])];
    else if((m = /(\d{1,2})\.?\s*[-–\/]+\s*(\d{1,2})\.(\d{1,2})\./.exec(p))) range = [(+m[3])*100+(+m[1]), (+m[3])*100+(+m[2])];
    else if((m = /(\d{1,2})\.(\d{1,2})\./.exec(p))) range = [(+m[2])*100+(+m[1]), (+m[2])*100+(+m[1])];
    let c = p.replace(/\b\d{1,2}\.\s*oder\b/g,' ').replace(/[\d.\/\-–]*\d\.\d{1,2}\.+/g,' ').replace(/\((?:TBC|AK\?|Ort TBC)\)|\?/g,' ').replace(/\s+/g,' ').trim();
    let name = c, ort = '', disc = '';
    const pref = BT_WK_PREFIX.find(x=>c===x || c.indexOf(x+' ')===0);
    if(pref){
      name = pref.replace(/ (L|Lead|S)$/,'').replace('Wild Cartd','Wild Card'); ort = c.slice(pref.length).trim();
      if(/ (L|Lead)$/.test(pref)) disc = 'Lead'; else if(/ S$/.test(pref)) disc = 'Speed';
    }
    const dm = /(?:^|\s)([BLS](?:\/[BLS])*)$/.exec(ort);
    if(dm){ disc = dm[1].split('/').map(x=>BT_DISC[x]).join('/'); ort = ort.slice(0, ort.length-dm[0].length).trim(); }
    ort = ort.replace(/^(?:L|Lead)\s+/,'').trim();
    if(!disc && (kind==='Bouldern' || kind==='Lead')) disc = kind;
    return {name:name, ort:ort||'-', disc:disc||'-', range:range, raw:p};
  });
}
function btDayNum(ds){ const m = /(\d{4})-(\d{2})-(\d{2})/.exec(ds||''); return m ? [new Date(ds+'T00:00:00Z').getTime(), (+m[2])*100+(+m[3])] : null; }
function btWkDay(key, ds, field){
  const J = (D.JAHRESPLAN2027||{})[key]; const dn = btDayNum(ds); field = field || 'wk';
  if(!J || !J[field] || !dn) return [];
  const out = [], seen = {};
  J[field].forEach(w=>{
    const wd = btDayNum(w.date); if(!wd || Math.abs(wd[0]-dn[0]) > 12*86400000) return;
    btParseWk(w.name, w.kind).forEach(e=>{
      if(!e.range || dn[1] < e.range[0] || dn[1] > e.range[1]) return;
      const k = e.name+'|'+e.ort; if(seen[k]) return; seen[k] = 1; out.push(e);
    });
  });
  return out;
}
function btWkOpen(key, days, field){
  field = field || 'wk';
  const J = (D.JAHRESPLAN2027||{})[key]; if(!J || !J[field] || !days.length) return [];
  const a = btDayNum(days[0].date), b = btDayNum(days[days.length-1].date); if(!a || !b) return [];
  const out = [];
  J[field].forEach(w=>{
    const wd = btDayNum(w.date); if(!wd || wd[0] < a[0] || wd[0] > b[0]) return;
    btParseWk(w.name, w.kind).forEach(e=>{ if(!e.range) out.push(e); });
  });
  return out;
}
function btWkCard(e){
  return '<div class="btWk"><div class="h">Wettkampf</div><div class="n">'+esc(e.name)+'</div><div class="m"><span>Ort: '+esc(e.ort)+'</span><span>Disziplin: '+esc(e.disc)+'</span></div></div>';
}
function btSonstCard(e){
  return '<div class="btWk" style="border-color:#E8A33D"><div class="h" style="color:#b9770e">Termin</div><div class="n">'+esc(e.name)+'</div></div>';
}
function btBlockAt(bl, i){ return (bl||[]).find(b=>i>=b.s && i<b.s+b.n) || null; }
function btPhasePills(key){
  const J = (D.JAHRESPLAN2027||{})[key]; if(!J) return '';
  const i = (J.weeks||[]).findIndex(w=>w.y===state.year && w.kw===state.kw);
  const t = (bl)=>{ const b = i>=0 ? btBlockAt(bl, i) : null; return b ? b.t : '-'; };
  return '<div class="btPills"><span class="btPill"><b>Phase</b> '+esc(t((J.tracks||{}).phase))+'</span><span class="btPill"><b>Kraftausdauer</b> '+esc(t((J.tracks||{}).ka))+'</span></div>';
}
