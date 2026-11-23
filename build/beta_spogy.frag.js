// ---- SPOGY-Board (Trainerreiter, PC-optimiert): Woche = Athlet x Tag, Tag = eine Spalte je Athlet ----
const SP_DOW = ['Mo','Di','Mi','Do','Fr','Sa','So'];
function spIsoKw(iso){ const d = new Date(iso+'T12:00:00Z'); d.setUTCDate(d.getUTCDate()+3-((d.getUTCDay()+6)%7)); const y = d.getUTCFullYear(); const w1 = new Date(Date.UTC(y,0,4)); return {kw:1+Math.round(((d-w1)/864e5-3+((w1.getUTCDay()+6)%7))/7), y:y}; }
function spNames(){ const sg = D.GROUPS.find(g=>g.id==='SPOGY Gruppe'); return sg ? sg.athletes.map(a=>a.n) : []; }
function spMonday(iso){ const d = new Date(iso+'T12:00:00'); const wd = (d.getDay()+6)%7; d.setDate(d.getDate()-wd); return trIso(d); }
function spDayMin(day){ let t = 0; (day && day.sessions || []).forEach(s=>(s.cats||[]).forEach(c=>(c.items||[]).forEach(it=>{ const m = tpItemMin(it); if(m) t += m; }))); return t; }
function spRest(day){
  const rest = [];
  (day && day.sessions || []).forEach(s=>(s.cats||[]).forEach(c=>(c.items||[]).forEach(it=>{
    const inMain = (BT_H1.indexOf(c.name)>=0 && !it.par) || BT_H2.indexOf(c.name)>=0;
    if(!inMain) rest.push({it:it, cat:(c.name==='Technik/Taktik'?'Taktik':c.name)});
  })));
  return rest;
}
function spNotes(day, wk){
  const notes = [];
  [day && day.sonstiges, day && day.notiz].concat(((day && day.sessions)||[]).map(s=>s.notiz)).forEach(t=>{
    t = String(t||'').trim();
    if(!t || t==='-' || notes.indexOf(t)>=0) return;
    if(/^mit\s/i.test(t)) return;
    if(day.zeit && t.replace(/\s/g,'').indexOf(day.zeit.replace(/\s/g,''))>=0) return;
    if(wk.some(e=>e.ort!=='-' && t.indexOf(e.ort)>=0)) return;
    notes.push(t);
  });
  return notes;
}
function spTag(wk, st){
  return wk.map(e=>'<span class="spTag wk">WK '+esc(e.ort!=='-'?e.ort:e.name)+(e.disc && e.disc!=='-' ? ' · '+esc(e.disc) : '')+'</span>').join('')
    + st.map(e=>'<span class="spTag st">'+esc(e.name)+'</span>').join('');
}
function spCompact(e){
  const it = e.it, m = it.match || {}, mins = tpItemMin(it);
  const has = v => v!=null && v!=='' && v!=='x';
  const sub = [];
  if(has(m.sets)) sub.push('Sätze '+m.sets);
  if(has(m.vol)) sub.push(m.vol);
  if(has(m.pause)) sub.push('Pause '+m.pause+(typeof m.pause==='number'?' min':''));
  return '<div class="spItem'+(it.red?' red':'')+'" style="background:'+(it.col?'#'+esc(it.col):'#fff')+'"><div class="n">'+esc(btName(it))+'</div>'
    + (mins || it.par ? '<div class="d">'+esc(mins ? btDur(mins) : 'nebenbei')+'</div>' : '')
    + (sub.length ? '<div class="s">'+sub.map(esc).join(' · ')+'</div>' : '') + '</div>';
}
function spDayCol(nm, iso){
  const key = 'a:'+nm, day = trFindDay(nm, iso);
  const col = (day && BT_COL[day.ortType]) || '#dfe5e9';
  const wk = btWkDay(key, iso), st = btWkDay(key, iso, 'sonst');
  const h1 = btItems(day, BT_H1), h2 = btItems(day, BT_H2), rest = spRest(day), notes = spNotes(day, wk);
  const total = spDayMin(day);
  const hasTr = day && day.sessions && day.sessions.length;
  const meta = day ? [day.zeit, day.trainer].filter(Boolean).join(' · ') : '';
  let b = '<div class="spCol"><div class="spHead" style="background:'+col+'"><b>'+esc(nm)+'</b><span class="o">'+esc((day && day.ort) || (hasTr ? 'Ort offen' : 'Trainingsfrei'))+'</span>'
    + (meta ? '<span class="m">'+esc(meta)+'</span>' : '') + (total ? '<span class="m">'+esc(btDur(total))+' geplant</span>' : '') + '</div>'
    + (wk.length || st.length ? '<div class="spTags">'+spTag(wk, st)+'</div>' : '');
  if(h1.length) b += '<div class="spSec">Hauptteil 1</div>' + h1.map(spCompact).join('');
  if(h2.length) b += '<div class="spSec">Hauptteil 2</div>' + h2.map(spCompact).join('');
  if(rest.length || notes.length){
    b += '<div class="spSec">Sonstige Inhalte</div>'
      + rest.map(e=>{ const mins = tpItemMin(e.it); return '<div class="spRow" style="background:'+(e.it.col?'#'+esc(e.it.col):'#fff')+'"><span class="c">'+esc(e.cat)+'</span><span class="n">'+esc(btName(e.it))+'</span><span class="d">'+(mins?esc(btDur(mins)):(e.it.par?'nebenbei':''))+'</span></div>'; }).join('')
      + notes.map(t=>'<div class="spNote">'+esc(t)+'</div>').join('');
  }
  if(!hasTr && !notes.length && !wk.length && !st.length) b += '<div class="spFree">Kein Training eingetragen</div>';
  return b + '</div>';
}
function spWeekCell(nm, iso){
  const key = 'a:'+nm, day = trFindDay(nm, iso);
  const wk = btWkDay(key, iso), st = btWkDay(key, iso, 'sonst');
  const hasTr = day && day.sessions && day.sessions.length;
  if(!day || (!hasTr && !wk.length && !st.length)) return '<div class="spCell free" data-spd="'+iso+'">–</div>';
  const col = BT_COL[day.ortType] || '#dfe5e9';
  const h1 = btItems(day, BT_H1), h2 = btItems(day, BT_H2), rest = spRest(day);
  const ln = (arr, cls)=>arr.map(e=>'<div class="spL '+cls+'">'+esc(btName(e.it))+(tpItemMin(e.it) ? ' <i>'+tpItemMin(e.it)+'′</i>' : '')+'</div>').join('');
  return '<div class="spCell" data-spd="'+iso+'"><div class="spCT" style="background:'+col+'"><b>'+esc(day.ort || (hasTr ? 'Ort offen' : ''))+'</b><span>'+esc(day.zeit || '')+'</span></div>'
    + (wk.length || st.length ? '<div class="spTags">'+spTag(wk, st)+'</div>' : '')
    + ln(h1, 'h1') + ln(h2, 'h2')
    + (rest.length ? '<div class="spL rest">'+rest.map(e=>esc(btName(e.it))).slice(0,6).join(' · ')+'</div>' : '') + '</div>';
}
function renderSpogyBoard(){
  const names = spNames();
  const iso = state.trainerDay || trIso(new Date());
  const mode = state.spogyMode === 'Tag' ? 'Tag' : 'Woche';
  const mon = spMonday(iso), days = [0,1,2,3,4,5,6].map(i=>trShift(mon, i));
  const today = trIso(new Date());
  const tabs = '<div class="spTabs"><button class="'+(mode==='Woche'?'sel':'')+'" data-spm="Woche">Woche</button><button class="'+(mode==='Tag'?'sel':'')+'" data-spm="Tag">Tag</button></div>';
  const step = mode==='Woche' ? 7 : 1;
  const title = mode==='Woche'
    ? 'KW '+(function(){ const k = spIsoKw(mon); return btKwLab(mon, k.kw, k.y).kw; })()+' · '+mon.slice(8,10)+'.'+mon.slice(5,7)+'. – '+days[6].slice(8,10)+'.'+days[6].slice(5,7)+'.'+days[6].slice(0,4)
    : trFmtDate(iso);
  const nav = '<div class="spNav"><button class="navBtn" data-trday="-'+step+'">‹</button><div class="spTitle">'+esc(title)+'</div><button class="navBtn" data-trday="'+step+'">›</button><button class="spToday" data-trday="0">Heute</button></div>';
  let body = '';
  if(mode==='Woche'){
    body = '<div class="spWeek"><div class="spCorner">SPOGY</div>'
      + days.map((d,i)=>'<div class="spDH'+(d===today?' today':'')+'" data-spd="'+d+'"><b>'+SP_DOW[i]+'</b><span>'+d.slice(8,10)+'.'+d.slice(5,7)+'.</span></div>').join('')
      + names.map(nm=>{
          let wt = 0; days.forEach(d=>{ wt += spDayMin(trFindDay(nm, d)); });
          return '<div class="spName"><b>'+esc(nm)+'</b><span>'+(wt ? esc(btDur(wt))+' Woche' : '–')+'</span></div>' + days.map(d=>spWeekCell(nm, d)).join('');
        }).join('') + '</div>';
  } else {
    body = '<div class="spDay" style="grid-template-columns:repeat('+Math.max(1,names.length)+',minmax(190px,1fr))">' + names.map(nm=>spDayCol(nm, iso)).join('') + '</div>';
  }
  return '<div class="spBoard"><div class="spBar"><span class="spTt">SPOGY · Übersicht Einzelathleten</span>'+tabs+nav+'</div><div class="spScroll">'+body+'</div></div>';
}
function btTrWide(){
  const ids = trainerSession.order; if(!ids.length) return false;
  let gid = state.trainerGroup; if(ids.indexOf(gid)<0) gid = ids[0];
  return gid === 'SPOGY Gruppe';
}
if(typeof document !== 'undefined' && document.addEventListener){
  document.addEventListener('click', ev=>{
    const t = ev.target && ev.target.closest ? ev.target : null; if(!t) return;
    const g = t.closest('[data-trg]'); if(g && g.getAttribute('data-trg')==='SPOGY Gruppe') setTimeout(()=>{ const b = document.querySelector('.spBoard'); if(b && b.scrollIntoView) b.scrollIntoView({block:'start'}); }, 80);
    const m = t.closest('[data-spm]'); if(m){ setState({spogyMode: m.getAttribute('data-spm')}); return; }
    const d = t.closest('[data-spd]'); if(d){ setState({spogyMode:'Tag', trainerDay: d.getAttribute('data-spd')}); }
  });
}
