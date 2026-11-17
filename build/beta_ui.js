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
.btBanner{border-radius:16px;padding:16px 16px 14px;color:#000;display:flex;flex-direction:column;gap:6px}
.btBanner .d{font:600 12px/1 'Roboto Mono',monospace;letter-spacing:.04em;text-transform:uppercase}
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
.btNote{font:500 12.5px/1.4 Archivo,sans-serif;padding:8px 12px;border-radius:10px;background:rgba(232,163,61,.15)}
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
  const nav = '<div class="weekNav"><button class="navBtn" data-act="prevWeek">‹</button><div class="weekTitle"><div class="weekKw">KW '+state.kw+' · '+state.year+'</div><div class="weekMeta">'+(plan ? esc(plan.span) : 'NOCH NICHT GEPLANT')+'</div></div><button class="navBtn" data-act="nextWeek">›</button></div>';
  if(!plan) return nav + '<div class="empty"><div class="t1">Kein Plan für diese Woche</div></div>';
  const days = plan.days || [];
  const di = Math.min(state.day, Math.max(0, days.length-1));
  const day = days[di] || null;
  const chips = days.map((dd,i)=>{
    const col = BT_COL[dd.ortType] || '#dfe5e9';
    const main = btItems(dd, BT_H1).concat(btItems(dd, BT_H2)).filter(e=>!e.it.pause).map(e=>btName(e.it)).slice(0,4).join(' · ');
    const wks = btWkDay(key, dd.date);
    const wkTag = wks.length ? '<span class="wk">WK '+esc(wks.map(e=>e.ort!=='-'?e.ort:e.name).join(', '))+'</span>' : '';
    return '<button class="btChip'+(i===di?' sel':'')+'" data-act="day" data-i="'+i+'" style="background:'+col+'"><span class="dw">'+esc((dd.dow||'').slice(0,2).toUpperCase())+'</span><span class="dm">'+esc(dd.dom)+'</span>'+wkTag+(main?'<span class="ct">'+esc(main)+'</span>':'')+'</button>';
  }).join('');
  let body = '';
  if(day){
    const col = BT_COL[day.ortType] || '#dfe5e9';
    const trainer = trainerDisplay(isSolo ? null : view.id, day);
    const hasTr = day.sessions && day.sessions.length;
    body += '<div class="btBanner" style="background:'+col+'"><span class="d">'+esc(day.dow+', '+day.dom)+'</span><span class="o">'+esc(day.ort || (hasTr ? 'Ort offen' : 'Trainingsfrei'))+'</span>'
      + ((day.zeit || trainer) ? '<div class="m">'+(day.zeit?'<span>'+esc(day.zeit)+'</span>':'')+(trainer?'<span>'+esc(trainer)+'</span>':'')+'</div>' : '')+'</div>';
    const wkDay = btWkDay(key, day.date);
    wkDay.forEach(e=>{ body += btWkCard(e); });
    const h1 = btItems(day, BT_H1), h2 = btItems(day, BT_H2);
    if(h1.length) body += '<div class="btSec"><div class="btSecH">Hauptteil 1</div>'+h1.map(btCard).join('')+'</div>';
    if(h2.length) body += '<div class="btSec"><div class="btSecH">Hauptteil 2</div>'+h2.map(btCard).join('')+'</div>';
    const rest = [];
    (day.sessions||[]).forEach(s=>(s.cats||[]).forEach(c=>{ (c.items||[]).forEach(it=>{ const inMain = (BT_H1.indexOf(c.name)>=0 && !it.par) || BT_H2.indexOf(c.name)>=0; if(!inMain) rest.push({it:it,cat:(c.name==='Technik/Taktik'?'Taktik':c.name)}); }); }));
    const notes = [];
    [day.sonstiges, day.notiz].concat((day.sessions||[]).map(s=>s.notiz)).forEach(t=>{ t=String(t||'').trim(); if(!t || t==='-' || notes.indexOf(t)>=0) return; if(wkDay.some(e=>e.ort!=='-' && t.indexOf(e.ort)>=0)) return; if(/^mit\\s/i.test(t) || (day.zeit && t.indexOf(day.zeit.replace(/\\s/g,''))>=0) || (day.zeit && t.replace(/\\s/g,'').indexOf(day.zeit.replace(/\\s/g,''))>=0)) return; notes.push(t); });
    if(rest.length || notes.length){
      body += '<div class="btSec"><div class="btSecH">Sonstige Inhalte</div>'
        + rest.map(e=>{ const mins = tpItemMin(e.it); return '<div class="btRow" style="background:'+(e.it.col?'#'+esc(e.it.col)+'55':'#fff')+'"><span class="c">'+esc(e.cat)+'</span><span class="n">'+esc(btName(e.it))+'</span><span class="d">'+(mins?esc(btDur(mins)):(e.it.par?'nebenbei':''))+'</span></div>'; }).join('')
        + notes.map(t=>'<div class="btNote">'+esc(t)+'</div>').join('')+'</div>';
    }
    if(!hasTr && !notes.length) body += '<div class="dashed">Trainingsfrei / keine Einheit eingetragen</div>';
  }
  const wkOpen = btWkOpen(key, days).map(e=>'<div class="btNote">Wettkampf diese Woche (Tag offen): '+esc(e.name)+' · '+esc(e.ort)+' · '+esc(e.disc)+'</div>').join('');
  const ueb = '<a class="btUeb" href="'+BT_UEB+'" target="_blank" rel="noopener">Übungen</a>';
  return nav + '<div class="btChips">'+chips+'</div>' + wkOpen + ueb + body;
}
`;

function apply(html) {
  const rep = (a, b) => {
    const n = html.split(a).length - 1;
    if (n !== 1) throw new Error('beta_ui: ' + n + 'x gefunden: ' + a.slice(0, 60));
    html = html.replace(a, () => b);
  };
  rep('</style>', CSS + '</style>');
  rep('function renderWochenplan(', JS + require('fs').readFileSync(__dirname + '/beta_wk.frag.js', 'utf8') + '\nfunction renderWochenplan(');
  rep("const tabNames = ['Dashboard','Woche','Wochenplan','Jahr','Statistik'];\n  if(isSolo){ tabNames.push('Benchmarks'); }\n  tabNames.push('Trainer');\n  if(tabNames.indexOf(state.tab) < 0) state.tab = 'Dashboard';",
      "const tabNames = ['Woche'];\n  state.tab = 'Woche';");
  rep("${state.tab==='Woche' ? renderWoche(view, isSolo, key, hasSource, srcInfo) : ''}", "${renderEinheitBeta(view, isSolo, key, hasSource, srcInfo)}");
  rep('<div class="tabs">\n      ${tabNames', '<div class="tabs" style="display:none">\n      ${tabNames');
  rep("      </div>\n    </div>\n  `;\n}\n\nfunction wireEvents(){", "      </div>\n      <div class=\"btTrainer\">${renderTrainerspace(null)}</div>\n    </div>\n  `;\n}\n\nfunction wireEvents(){");
  return html;
}
module.exports = { apply };
