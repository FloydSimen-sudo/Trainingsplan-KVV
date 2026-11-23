// Beta-Oberflaeche (nur beta.html): Startseite inkl. Trainer, im Plan nur Reiter "Einheit" (Ort-Banner, Hauptteil 1/2, Sonstiges).
// Wird von build_beta.js nur auf beta.html angewendet -- nie auf index.html.
const CSS = `
.btChips{display:flex;gap:5px}
.btChip{flex:1;min-width:0;display:flex;flex-direction:column;align-items:flex-start;gap:2px;padding:6px 5px 7px;border-radius:10px;border:2px solid transparent;cursor:pointer;color:#000;text-align:left;font-family:Archivo,sans-serif;overflow:hidden}
.btChip.sel{border-color:#000}
.btChip .dw{font:700 10px/1 'Roboto Mono',monospace}
.btChip .dm{font:800 13px/1.1 Archivo,sans-serif}
.btChip .ct{font:500 8.5px/1.2 Archivo,sans-serif;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:break-word;hyphens:auto}
.btUeb{display:block;text-align:center;padding:12px;border-radius:12px;background:#005A96;color:#fff;font:700 14px/1 Archivo,sans-serif;text-decoration:none}
.btChip .wk{margin-top:3px;padding:2px 4px;border-radius:5px;background:#000;color:#fff;font:700 8px/1.2 Archivo,sans-serif;overflow-wrap:anywhere}
.btWk{border-radius:14px;padding:12px 14px;background:#fff;border:3px solid #d20028;color:#000;display:flex;flex-direction:column;gap:4px}
.btWk .h{font:700 11px/1 'Roboto Mono',monospace;letter-spacing:.08em;text-transform:uppercase;color:#d20028}
.btWk .n{font:800 22px/1.1 Archivo,sans-serif}
.btWk .m{display:flex;flex-wrap:wrap;gap:4px 16px;font:700 14px/1.2 Archivo,sans-serif}
.btChip .wk.st{background:#E8A33D;color:#000}
.btPills{display:flex;flex-direction:column;gap:5px}
.btPill{display:block;width:100%;box-sizing:border-box;text-align:center;padding:5px 8px;border-radius:999px;background:#eef2f5;border:1px solid rgba(10,50,80,.12);font:600 11px/1.2 Archivo,sans-serif;color:#000}
.btPill b{font:700 9px/1 'Roboto Mono',monospace;text-transform:uppercase;letter-spacing:.05em;opacity:.7;margin-right:4px}
.btStand{margin:10px 18px 2px;padding:5px 10px;border-radius:999px;background:#f3f6f8;border:1px solid rgba(10,50,80,.12);display:flex;align-items:center;gap:7px}
.btStand .dot{width:7px;height:7px;border-radius:50%;background:#128089;flex:none}
.btStand .k{display:none}
.btStand .v{font:600 11px/1.2 Archivo,sans-serif;color:#33434d;white-space:nowrap}
.btStand .f{display:none}
.header{flex-wrap:wrap;row-gap:8px}
.header .headerBtn{flex:1 1 220px !important;min-width:0}
.header .headerLogo{order:2}
.header > :not(.brandMark):not(.headerBtn):not(.headerLogo){order:3;flex:1 1 28% !important;justify-content:center;background:#005A96 !important}
.jz{display:flex;flex-direction:column;gap:3px;padding-bottom:90px}
.jzHead,.jzRow{display:grid;grid-template-columns:58px 74px 74px 1fr;gap:4px}
.jzHead{background:#fff;padding:6px 0;font:700 9px/1 'Roboto Mono',monospace;text-transform:uppercase;letter-spacing:.06em;color:#4a5b66;border-bottom:1px solid rgba(10,50,80,.15)}
.jzYear{font:800 18px/1 Archivo,sans-serif;padding:8px 0 2px}
.jzRow{min-height:46px;align-items:stretch}
.jzRow.cur .jzW{outline:2px solid #d20028;border-radius:6px}
.jzW{display:flex;flex-direction:column;justify-content:center;padding:2px 4px}
.jzW b{font:800 12px/1.1 Archivo,sans-serif}
.jzW span{font:500 9px/1.2 'Roboto Mono',monospace;color:#4a5b66}
.jzC{display:flex;align-items:flex-start;justify-content:center;text-align:center;padding:4px 3px;font:700 10.5px/1.15 Archivo,sans-serif;overflow-wrap:anywhere;background:#f3f6f8;border-radius:0}
.jzE{display:flex;flex-direction:column;gap:3px;justify-content:center;padding:2px 0}
.jzEv{padding:4px 7px;border-radius:7px;border:1px solid rgba(10,50,80,.15);background:#fff;font:500 11px/1.25 Archivo,sans-serif;color:#000}
.jzEv b{font-weight:800}
.jzEv span{font-weight:600}
.jzEv i{font:600 10px/1 'Roboto Mono',monospace;font-style:normal;opacity:.75}
.jzEv.wk{border-left:5px solid #d20028}
.btBanner{border-radius:16px;padding:16px 16px 14px;color:#000;display:flex;flex-direction:column;gap:6px}
.btBanner .d{font:800 22px/1.1 Archivo,sans-serif}
.btBanner .o{font:800 34px/1.05 Archivo,sans-serif;word-break:break-word}
.btBanner .m{display:flex;flex-wrap:wrap;gap:6px 16px;font:700 16px/1.2 Archivo,sans-serif}
.btSec{display:flex;flex-direction:column;gap:8px}
.btSecH{font:700 11px/1 'Roboto Mono',monospace;letter-spacing:.08em;text-transform:uppercase;color:#4a5b66;padding-top:6px}
.btCard{border-radius:14px;padding:12px 14px;display:flex;flex-direction:column;gap:5px;border:1px solid rgba(10,50,80,.10)}
.btCard.red .n{color:#d20028}
.btCard .n{font:700 16px/1.25 Archivo,sans-serif}
.btCard .d{font:600 12px/1.2 'Roboto Mono',monospace}
.btCard .s{font:500 12px/1.3 Archivo,sans-serif;color:#33434d}
.btCard ul{margin:2px 0 0;padding-left:18px;font:400 12.5px/1.45 Archivo,sans-serif}
.btRow{display:flex;gap:8px;align-items:baseline;padding:7px 10px;border-radius:10px;border:1px solid rgba(10,50,80,.08)}
.btRow .c{font:700 9px/1 'Roboto Mono',monospace;text-transform:uppercase;color:#4a5b66;flex:none;width:78px}
.btRow .n{flex:1;font:600 13px/1.3 Archivo,sans-serif}
.btRow .d{font:600 11px/1 'Roboto Mono',monospace;flex:none}
.btNote{font:500 12.5px/1.4 Archivo,sans-serif;padding:8px 12px;border-radius:10px;background:#f3f6f8;color:#33434d}
#app:has(.btTrainer.wide){max-width:none}
.btTrainer.wide{max-width:none;padding-left:20px;padding-right:20px}
.btTrainer.wide > :not(.spBoard){width:100%;max-width:560px;margin-left:auto;margin-right:auto}
.spBoard{display:flex;flex-direction:column;gap:10px;width:100%}
.spBar{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.spTt{font:700 17px/1 Archivo,sans-serif;margin-right:auto}
.spTabs{display:flex;border:1.5px solid #005A96;border-radius:10px;overflow:hidden}
.spTabs button{border:0;background:#fff;color:#005A96;padding:9px 18px;font:700 13px/1 Archivo,sans-serif;cursor:pointer}
.spTabs button.sel{background:#005A96;color:#fff}
.spNav{display:flex;align-items:center;gap:10px}
.spTitle{font:700 15px/1.2 Archivo,sans-serif;min-width:190px;text-align:center}
.spToday{border:1px solid #9aa3a9;background:#fff;border-radius:8px;padding:8px 12px;font:600 12px/1 Archivo,sans-serif;cursor:pointer}
.spScroll{overflow-x:auto;padding-bottom:8px}
.spWeek{display:grid;grid-template-columns:150px repeat(7,minmax(150px,1fr));gap:6px;min-width:1150px}
.spCorner{font:700 11px/1 'Roboto Mono',monospace;color:#4a5b66;align-self:end;padding:4px}
.spDH{display:flex;flex-direction:column;gap:2px;padding:8px 10px;border-radius:10px;background:#eef2f5;cursor:pointer}
.spDH.today{background:#005A96;color:#fff}
.spDH b{font:800 14px/1 Archivo,sans-serif}.spDH span{font:600 11px/1 'Roboto Mono',monospace}
.spName{display:flex;flex-direction:column;gap:3px;padding:10px;border-radius:10px;background:#eef2f5;justify-content:center}
.spName b{font:700 14px/1.15 Archivo,sans-serif}.spName span{font:600 11px/1 'Roboto Mono',monospace;color:#4a5b66}
.spCell{display:flex;flex-direction:column;gap:3px;padding:6px;border-radius:10px;border:1px solid rgba(10,50,80,.12);background:#fff;cursor:pointer;min-width:0}
.spCell:hover{border-color:#005A96}
.spCell.free{color:#9aa3a9;align-items:center;justify-content:center;background:#f7f9fa}
.spCT{display:flex;flex-direction:column;gap:1px;padding:4px 7px;border-radius:7px;color:#000}
.spCT b{font:800 12px/1.2 Archivo,sans-serif}.spCT span{font:600 10.5px/1.2 Archivo,sans-serif}
.spL{font:600 11.5px/1.25 Archivo,sans-serif;padding:3px 6px;border-radius:6px;word-break:break-word}
.spL i{font-style:normal;color:#4a5b66;font-weight:500}
.spL.h1{background:#fff7b8}.spL.h2{background:#fbe0cd}.spL.rest{background:#eef2f5;color:#4a5b66;font-weight:500;font-size:10.5px}
.spTags{display:flex;flex-wrap:wrap;gap:4px}
.spTag{font:700 10px/1.2 Archivo,sans-serif;padding:3px 6px;border-radius:6px}
.spTag.wk{background:#fff;border:1.5px solid #d20028;color:#d20028}.spTag.st{background:#fff;border:1.5px solid #e8a33d;color:#8a5a00}
.spDay{display:grid;gap:10px;min-width:calc(8*165px)}
.spCol{display:flex;flex-direction:column;gap:6px;min-width:0}
.spHead{display:flex;flex-direction:column;gap:2px;padding:10px 12px;border-radius:12px;color:#000}
.spHead b{font:800 16px/1.15 Archivo,sans-serif}.spHead .o{font:700 14px/1.2 Archivo,sans-serif}.spHead .m{font:600 11.5px/1.25 Archivo,sans-serif}
.spSec{font:700 10px/1 'Roboto Mono',monospace;letter-spacing:.08em;text-transform:uppercase;color:#4a5b66;padding-top:4px}
.spItem{display:flex;flex-direction:column;gap:2px;padding:7px 9px;border-radius:9px;border:1px solid rgba(10,50,80,.10)}
.spItem.red .n{color:#d20028}
.spItem .n{font:700 12.5px/1.25 Archivo,sans-serif}.spItem .d{font:600 11px/1.2 'Roboto Mono',monospace}.spItem .s{font:500 11px/1.3 Archivo,sans-serif;color:#33434d}
.spRow{display:flex;flex-direction:column;gap:1px;padding:6px 9px;border-radius:9px;border:1px solid rgba(10,50,80,.08)}
.spRow .c{font:700 9px/1 'Roboto Mono',monospace;text-transform:uppercase;color:#4a5b66}.spRow .n{font:600 12px/1.25 Archivo,sans-serif}.spRow .d{font:600 10.5px/1 'Roboto Mono',monospace}
.spNote{font:500 11.5px/1.35 Archivo,sans-serif;padding:6px 9px;border-radius:9px;background:rgba(232,163,61,.15)}
.spFree{font:500 12px/1.3 Archivo,sans-serif;color:#9aa3a9;padding:10px;border:1px dashed #c3ccd2;border-radius:9px;text-align:center}
.btTrainer{padding:6px 16px 90px;display:flex;flex-direction:column;gap:10px;width:100%;max-width:560px;margin:0 auto;box-sizing:border-box}
`;

const JS = `
const BT_COL = {Bouldern:'#0090c9', Lead:'#78b83f', Speed:'#c9a227'};
const BT_UEB = 'https://kletternvorarlberg-my.sharepoint.com/:x:/g/personal/floyd_simen_klettern-vorarlberg_at/IQC9XgUg3engR7KFVrcHcok8AZ1cxB0C8wP0TQrGWXO8Y18?e=onBkcG';
const BT_H1 = ['Technikfokus','Technik/Taktik'], BT_H2 = ['Physis Klettern'];
function btName(it){ return String(it.ex||'').replace(/^\\s*\\d+(?:[.,]\\d+)?\\s*(?:h|std\\.?|min)\\s*/i,'').trim() || String(it.ex||''); }
function btDur(n){ return n>=60 ? (Math.floor(n/60)+' h'+(n%60?' '+(n%60)+' min':'')) : (n+' min'); }
function btItems(day, names){
  const out = [];
  (day && day.sessions || []).forEach(s=>(s.cats||[]).forEach(c=>{ if(names.indexOf(c.name)>=0) (c.items||[]).forEach(it=>{ if(!(names===BT_H1 && it.par)) out.push({it:it, cat:c.name}); }); }));
  return out;
}
function btCard(e){
  const it = e.it, m = it.match || {}, mins = tpItemMin(it);
  const has = v => v!=null && v!=='' && v!=='x';
  const sub = [];
  if(has(m.sets)) sub.push('Sätze: '+m.sets);
  if(has(m.vol)) sub.push('Wdh./Umfang: '+m.vol);
  if(has(m.pause)) sub.push('Pause: '+m.pause+(typeof m.pause==='number'?' min':''));
  const hw = (it.sx && D.EXHOW) ? D.EXHOW[it.sx] : null;
  const dur = mins ? btDur(mins) : (it.par ? 'läuft nebenbei' : '');
  return '<div class="btCard'+(it.red?' red':'')+'" style="background:'+(it.col?'#'+esc(it.col):'#fff')+'">'
    + '<div class="n">'+esc(btName(it))+'</div>'
    + (dur ? '<div class="d">'+esc(dur)+'</div>' : '')
    + (sub.length ? '<div class="s">'+sub.map(esc).join(' · ')+'</div>' : '')
    + ((hw && hw.length) ? '<ul>'+hw.map(t=>'<li>'+esc(t)+'</li>').join('')+'</ul>' : '')
    + '</div>';
}
function renderEinheitBeta(view, isSolo, key, hasSource, srcInfo){
  if(!hasSource) return '<div class="empty"><div class="t1">Keine Daten hinterlegt</div><div class="t2">'+esc(srcInfo)+'</div></div>';
  const plan = (D.PLANS[key] || {})[state.year + '-' + state.kw] || null;
  const kl0 = btKwLab(((plan && plan.days && plan.days[0]) ? plan.days[0].date : ''), state.kw, state.year);
  const nav = '<div class="weekNav"><button class="navBtn" data-act="prevWeek">‹</button><div class="weekTitle"><div class="weekKw">KW '+kl0.kw+' · '+kl0.y+'</div><div class="weekMeta">'+(plan ? esc(plan.span) : 'NOCH NICHT GEPLANT')+'</div></div><button class="navBtn" data-act="nextWeek">›</button></div>';
  if(!plan) return nav + '<div class="empty"><div class="t1">Kein Plan für diese Woche</div></div>';
  const days = plan.days || [];
  const di = Math.min(state.day, Math.max(0, days.length-1));
  const day = days[di] || null;
  const chips = days.map((dd,i)=>{
    const cx = dd.cancel && !dd.cancel.p;
    const col = cx ? '#9aa3a9' : (BT_COL[dd.ortType] || '#dfe5e9');
    const main = btItems(dd, BT_H1).concat(btItems(dd, BT_H2)).filter(e=>!e.it.pause).map(e=>btName(e.it)).slice(0,4).join(' · ');
    const wks = btWkDay(key, dd.date);
    const sts = btWkDay(key, dd.date, 'sonst');
    const wkTag = (wks.length ? '<span class="wk">WK '+esc(wks.map(e=>e.ort!=='-'?e.ort:e.name).join(', '))+'</span>' : '') + (sts.length ? '<span class="wk st">'+esc(sts.map(e=>e.name).join(', '))+'</span>' : '');
    return '<button class="btChip'+(i===di?' sel':'')+'" data-act="day" data-i="'+i+'" style="background:'+col+(cx?';color:#000':'')+'"><span class="dw">'+esc((dd.dow||'').slice(0,2).toUpperCase())+'</span><span class="dm">'+esc(dd.dom)+'</span>'+(dd.cancel?'<span class="wk" style="background:#fff;color:#333">ENTFÄLLT</span>':'')+wkTag+(main?'<span class="ct">'+esc(main)+'</span>':'')+'</button>';
  }).join('');
  let body = '';
  if(day){
    const col = BT_COL[day.ortType] || '#dfe5e9';
    const trainer = trainerDisplay(isSolo ? null : view.id, day);
    const hasTr = day.sessions && day.sessions.length;
    const cxd = day.cancel && !day.cancel.p;
    body += '<div class="btBanner" style="background:'+(cxd?'#9aa3a9;color:#000':col)+'"><span class="d">'+esc(day.dow+', '+day.dom)+'</span><span class="o">'+(cxd?'Training entfällt':esc(day.ort || (hasTr ? 'Ort offen' : 'Trainingsfrei')))+'</span>'+(day.cancel?'<span style="font:700 16px Archivo,sans-serif">'+esc(day.cancel.r)+'</span>':'')
      + ((day.zeit || trainer) ? '<div class="m">'+(day.zeit?'<span>'+esc(day.zeit)+'</span>':'')+(trainer?'<span>'+esc(trainer)+'</span>':'')+'</div>' : '')+'</div>';
    const wkDay = btWkDay(key, day.date);
    wkDay.forEach(e=>{ body += btWkCard(e); });
    btWkDay(key, day.date, 'sonst').forEach(e=>{ body += btSonstCard(e); });
    const h1 = btItems(day, BT_H1), h2 = btItems(day, BT_H2);
    if(h1.length) body += '<div class="btSec"><div class="btSecH">Hauptteil 1</div>'+h1.map(btCard).join('')+'</div>';
    if(h2.length) body += '<div class="btSec"><div class="btSecH">Hauptteil 2</div>'+h2.map(btCard).join('')+'</div>';
    const rest = [];
    (day.sessions||[]).forEach(s=>(s.cats||[]).forEach(c=>{ (c.items||[]).forEach(it=>{ const inMain = (BT_H1.indexOf(c.name)>=0 && !it.par) || BT_H2.indexOf(c.name)>=0; if(!inMain) rest.push({it:it,cat:(c.name==='Technik/Taktik'?'Taktik':c.name)}); }); }));
    const notes = [];
    [day.sonstiges, day.notiz].concat((day.sessions||[]).map(s=>s.notiz)).forEach(t=>{ t=String(t||'').trim(); if(!t || t==='-' || notes.indexOf(t)>=0) return; if(wkDay.some(e=>e.ort!=='-' && t.indexOf(e.ort)>=0)) return; if(/^mit\\s/i.test(t) || (day.zeit && t.indexOf(day.zeit.replace(/\\s/g,''))>=0) || (day.zeit && t.replace(/\\s/g,'').indexOf(day.zeit.replace(/\\s/g,''))>=0)) return; notes.push(t); });
    if(rest.length || notes.length){
      body += '<div class="btSec"><div class="btSecH">Sonstige Inhalte</div>'
        + rest.map(e=>{ const mins = tpItemMin(e.it); return '<div class="btRow" style="background:'+(e.it.col?'#'+esc(e.it.col):'#fff')+'"><span class="c">'+esc(e.cat)+'</span><span class="n">'+esc(btName(e.it))+'</span><span class="d">'+(mins?esc(btDur(mins)):(e.it.par?'nebenbei':''))+'</span></div>'; }).join('')
        + notes.map(t=>'<div class="btNote">'+esc(t)+'</div>').join('')+'</div>';
    }
    if(!hasTr && !notes.length) body += '<div class="dashed">Trainingsfrei / keine Einheit eingetragen</div>';
  }
  const wkOpen = btWkOpen(key, days).map(e=>'<div class="btNote">Wettkampf diese Woche (Tag offen): '+esc(e.name)+' · '+esc(e.ort)+' · '+esc(e.disc)+'</div>').join('') + btWkOpen(key, days, 'sonst').map(e=>'<div class="btNote">Termin diese Woche (Tag offen): '+esc(e.name)+'</div>').join('');
  const ueb = '<a class="btUeb" href="'+BT_UEB+'" target="_blank" rel="noopener">Übungssammlung</a>';
  return nav + btPhasePills(key) + '<div class="btChips">'+chips+'</div>' + wkOpen + body;
}
`;

function viennaStamp() {
  const f = new Intl.DateTimeFormat('de-AT', {timeZone: 'Europe/Vienna', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false})
    .formatToParts(new Date()).reduce((o, x) => (o[x.type] = x.value, o), {});
  return f.day + '.' + f.month + '.' + f.year + ', ' + f.hour + ':' + f.minute;
}
function apply(html) {
  const rep = (a, b) => {
    const n = html.split(a).length - 1;
    if (n !== 1) throw new Error('beta_ui: ' + n + 'x gefunden: ' + a.slice(0, 60));
    html = html.replace(a, () => b);
  };
  rep('</style>', CSS + '</style>');
  rep('function renderWochenplan(', 'const BT_BUILD = ' + JSON.stringify(viennaStamp()) + ';\n' + JS + require('fs').readFileSync(__dirname + '/beta_wk.frag.js', 'utf8') + require('fs').readFileSync(__dirname + '/beta_jz.frag.js', 'utf8') + require('fs').readFileSync(__dirname + '/beta_spogy.frag.js', 'utf8') + '\nfunction renderWochenplan(');
  rep("const tabNames = ['Dashboard','Woche','Wochenplan','Jahr','Statistik'];\n  if(isSolo){ tabNames.push('Benchmarks'); }\n  tabNames.push('Trainer');\n  if(tabNames.indexOf(state.tab) < 0) state.tab = 'Dashboard';",
      "const tabNames = ['Woche','Jahr'];\n  if(tabNames.indexOf(state.tab) < 0) state.tab = 'Woche';");
  rep("${state.tab==='Woche' ? renderWoche(view, isSolo, key, hasSource, srcInfo) : ''}", "${state.tab==='Jahr' ? renderJahrBeta(view, key) : renderEinheitBeta(view, isSolo, key, hasSource, srcInfo)}");
  rep(`<div class="syncbar">
      <span class="dot"></span>
      <div style="flex:1;display:flex;flex-direction:column;gap:2px;min-width:0">
        <span class="syncFile">\${esc(srcInfo)}</span>
        <span class="syncInfo">Stand \${esc(D.GENERATED || '-')}</span>
      </div>
    </div>`, `<div class="btStand">
      <span class="dot"></span>
      <div style="flex:1;display:flex;flex-direction:column;gap:3px;min-width:0">
        <span class="k">Letzte Aktualisierung</span>
        <span class="v">App-Stand: \${esc(btStand(BT_BUILD))}</span>
        <span class="f">\${esc(srcInfo)}</span>
      </div>
    </div>`);
  rep(`white-space:nowrap">Doku</a>
      \${routeBtn(view, 'head')}`, `white-space:nowrap">Doku</a>
      \${view.t==='a' && trainerSession.order.length ? '<a href="'+BT_UEB+'" target="_blank" rel="noopener" style="flex:none;display:flex;align-items:center;padding:8px 10px;border-radius:10px;background:'+AM+';color:#fff;font:600 12px/1 Archivo,sans-serif;white-space:nowrap">Übungssammlung</a>' : ''}
      \${routeBtn(view, 'head')}`);
  rep("${state.tab==='Jahr' ? renderJahr(view, isSolo, athlete, group) : ''}", '');
  rep("(n==='Woche'?'Einheit':(n==='Wochenplan'?'Woche':n))", "(n==='Woche'?'Einheit':(n==='Jahr'?'Jahresplanung':n))");
  rep("      </div>\n    </div>\n  `;\n}\n\nfunction wireEvents(){", "      </div>\n      <div class=\"btTrainer${btTrWide() ? ' wide' : ''}\">${renderTrainerspace(null)}${trainerSession.order.length ? `<div><a href=\"${BT_UEB}\" target=\"_blank\" rel=\"noopener\" style=\"display:inline-flex;align-items:center;padding:9px 14px;border-radius:10px;background:${AM};color:#fff;font:600 12px/1 Archivo,sans-serif;white-space:nowrap\">Übungssammlung</a></div>` : ''}</div>\n    </div>\n  `;\n}\n\nfunction wireEvents(){");
  rep("${gid==='SPOGY Gruppe' ? spogyDayOverview() : ''}", "${gid==='SPOGY Gruppe' ? renderSpogyBoard() : ''}");
  return html;
}
module.exports = { apply };
