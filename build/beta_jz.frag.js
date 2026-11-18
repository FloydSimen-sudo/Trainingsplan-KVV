// ---- Jahresplanung: KW47/2026 bis KW47/2027, eine Zeile je Woche, Phase + Kraftausdauer als senkrechte Balken, Termine rechts ----
function btTxtCol(col){ const n = parseInt(col.slice(1),16), l = (0.299*(n>>16) + 0.587*((n>>8)&255) + 0.114*(n&255))/255; return l < 0.45 ? '#fff' : '#000'; }
function btFmtDM(t){ const d = new Date(t); return d.getUTCDate()+'.'+(d.getUTCMonth()+1)+'.'; }
function renderJahrBeta(view, key){
  const J = (D.JAHRESPLAN2027||{})[key];
  if(!J || !J.weeks) return '<div class="empty"><div class="t1">Keine Jahresplanung hinterlegt</div></div>';
  const W = J.weeks, tr = J.tracks || {};
  let s = W.findIndex(w=>w.y===2026 && w.kw===47), e = W.findIndex(w=>w.y===2027 && w.kw===47);
  if(s<0) s = 0; if(e<0) e = W.length-1;
  const now = Date.now(), DAY = 864e5;
  const cell = (bl, i, first)=>{
    const b = btBlockAt(bl, i);
    if(!b) return '<div class="jzC"></div>';
    const col = /^#[0-9a-f]{6}$/i.test(b.c||'') ? b.c : '#e3e8ec';
    const lab = (i===Math.max(b.s, s)) ? esc(b.t) : '';
    const top = (i===Math.max(b.s, s)), bot = (i===Math.min(b.s+b.n-1, e));
    return '<div class="jzC" style="background:'+col+';color:'+btTxtCol(col)+';border-radius:'+(top?'8px':'0')+' '+(top?'8px':'0')+' '+(bot?'8px':'0')+' '+(bot?'8px':'0')+'"><span>'+lab+'</span></div>';
  };
  let html = '', lastY = null;
  for(let i=s;i<=e;i++){
    const w = W[i], monT = Date.parse(w.mon+'T00:00:00Z'), endT = monT + 6*DAY;
    const days = [0,1,2,3,4,5,6].map(k=>{ const t = new Date(monT+k*DAY); return {md:(t.getUTCMonth()+1)*100+t.getUTCDate(), dm:t.getUTCDate()+'.'+(t.getUTCMonth()+1)+'.'}; });
    const ev = [], seen = {};
    const add = (cls, label, sub, dm, col)=>{ const k = cls+label+sub; if(seen[k]) return; seen[k] = 1; const okc = /^#[0-9a-f]{6}$/i.test(col||''); ev.push('<div class="jzEv '+cls+'"'+(okc?' style="background:'+col+';color:'+btTxtCol(col)+';border-color:'+col+'"':'')+'><b>'+esc(label)+'</b>'+(sub?' <span>'+esc(sub)+'</span>':'')+(dm?' <i>'+esc(dm)+'</i>':'')+'</div>'); };
    [['wk','wk'],['sonst','st']].forEach(f=>{
      (J[f[0]]||[]).forEach(x=>{
        const xd = btDayNum(x.date); if(!xd || Math.abs(xd[0]-monT) > 20*DAY) return;
        let xc = null; ['wkB','wkS','wkWC','wkL','sonst'].forEach(tk=>(tr[tk]||[]).forEach(b=>{ if(b.t===x.name && b.c) xc = b.c; }));
        btParseWk(x.name, x.kind).forEach(p=>{
          let hit = null;
          if(p.range) hit = days.find(d=>d.md>=p.range[0] && d.md<=p.range[1]);
          else if(xd[0]>=monT && xd[0]<=endT) hit = {dm:''};
          if(!hit) return;
          if(f[1]==='st') add('st', p.name, '', hit.dm, xc);
          else add('wk', p.name, (p.ort!=='-'?p.ort+' · ':'')+p.disc, hit.dm, xc);
        });
      });
    });
    [['fels','Fels','fl'],['test','Test','ts'],['deload','Deload','dl']].forEach(f=>{ const b = btBlockAt(tr[f[0]], i); if(b) add(f[2], b.t, '', '', b.c); });
    const fb = btBlockAt(tr.ferien, i); if(fb && i===Math.max(fb.s, s)) add('fe', fb.t, '', '', fb.c);
    const cur = now >= monT && now < monT + 7*DAY;
    if(lastY!==null && w.y!==lastY) html += '<div class="jzYear">'+w.y+'</div>';
    if(lastY===null) html += '<div class="jzYear">'+w.y+'</div>';
    lastY = w.y;
    html += '<div class="jzRow'+(cur?' cur':'')+'"><div class="jzW"><b>KW '+w.kw+'</b><span>'+btFmtDM(monT)+'–'+btFmtDM(endT)+'</span></div>'
      + cell(tr.phase, i) + cell(tr.ka, i) + '<div class="jzE">'+ev.join('')+'</div></div>';
  }
  return '<div class="jz"><div class="jzHead"><span>Woche</span><span>Phase</span><span>Kraftausd.</span><span>Termine</span></div>'+html+'</div>';
}
