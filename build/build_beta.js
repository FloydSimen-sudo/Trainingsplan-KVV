#!/usr/bin/env node
// Beta-Testebene: erzeugt beta.html (neue Oberflaeche) + beta-data.enc.js (nur Adrian Kathan + U15 II, Passwort KVV).
//   node build/build_beta.js            -> beta.html + beta-data.enc.js aus index-live.html (neue UI) + tp-data.js
//   node build/build_beta.js --live <alte index.html> -> gibt die Live-index.html (alte UI + Beta-Button) nach stdout-Datei index.html
//   node build/build_beta.js --promote  -> index.html aus beta.html (Beta-Button, normales Datenpaket) + tp-data.enc.js (TP_PASSWORD)
const fs = require('fs'), crypto = require('crypto');
const BETA_PW = 'KVV';
const BTN = `const betaLink = \`<a href="./beta.html" style="display:inline-flex;align-items:center;margin-left:8px;padding:9px 14px;border-radius:10px;background:#d20028;color:#fff;font:700 12px/1 Archivo,sans-serif;white-space:nowrap">Beta</a>\`;\n  `;
function addBetaButton(html){
  if (html.includes('const betaLink')) return html;
  if (!html.includes('const pwForm =')) throw new Error('pwForm nicht gefunden');
  html = html.replace('const pwForm =', BTN + 'const pwForm =');
  return html.replace(/\$\{formLink\}/g, '${formLink}${betaLink}');
}
function encrypt(jsonStr, pw){
  const salt = crypto.randomBytes(16), iv = crypto.randomBytes(12), IT = 250000;
  const key = crypto.pbkdf2Sync(pw, salt, IT, 32, 'sha256');
  const c = crypto.createCipheriv('aes-256-gcm', key, iv);
  const enc = Buffer.concat([c.update(jsonStr, 'utf8'), c.final()]);
  const ct = Buffer.concat([enc, c.getAuthTag()]);
  return 'window.TPDATA_ENC = ' + JSON.stringify({v:1,kdf:'PBKDF2',hash:'SHA-256',iterations:IT,salt:salt.toString('base64'),iv:iv.toString('base64'),ct:ct.toString('base64')}) + ';\n';
}
function loadData(){
  const raw = fs.readFileSync('tp-data.js','utf8').trim();
  return JSON.parse(raw.slice('window.TPDATA = '.length).replace(/;\s*$/, ''));
}
const ATH = 'Adrian Kathan', GRP = 'U15 II';
function filterBeta(D){
  const pick = (o, keys) => { const r = {}; keys.forEach(k => { if (o && o[k] !== undefined) r[k] = o[k]; }); return r; };
  const out = Object.assign({}, D);
  const ak = 'a:' + ATH, gk = 'g:' + GRP;
  ['PLANS','CATS_BY_VIEW','SOURCE_INFO','JAHRESPLAN2027','PLANS2027_INFO'].forEach(k => out[k] = pick(D[k], [ak, gk]));
  ['WEEKS_BY_ATHLETE','BENCH','JAHRESPLAN','JAHRESPLAN_SOURCE'].forEach(k => out[k] = pick(D[k], [ATH]));
  ['JAHRESPLAN_GROUP','JAHRESPLAN_GROUP_SOURCE'].forEach(k => out[k] = pick(D[k], [GRP]));
  out.SEASON_STATS = {};
  Object.keys(D.SEASON_STATS).forEach(s => out.SEASON_STATS[s] = pick(D.SEASON_STATS[s], [ak, gk]));
  const spogy = D.GROUPS.find(g => g.id === 'SPOGY Gruppe');
  out.GROUPS = D.GROUPS.filter(g => g.id === GRP).concat(spogy ? [Object.assign({}, spogy, {athletes: spogy.athletes.filter(a => a.n === ATH)})] : []);
  return out;
}
function makeBetaHtml(html){
  html = addBetaButton(html);
  const rep = (a, b) => { if (!html.includes(a)) throw new Error('nicht gefunden: ' + a.slice(0,50)); html = html.split(a).join(b); };
  rep('<script src="./tp-data.enc.js"></script>', '<script src="./beta-data.enc.js"></script>');
  rep('<script src="./trainer-data.enc.js"></script>\n', '');
  rep("sessionStorage.getItem('tpPw')", "sessionStorage.getItem('tpPwBeta')");
  rep("sessionStorage.setItem('tpPw', password)", "sessionStorage.setItem('tpPwBeta', password)");
  rep('<title>Trainingspläne KVV</title>', '<title>BETA · Trainingspläne KVV</title>');
  rep('<body>', '<body>\n<div style="position:fixed;top:6px;right:6px;z-index:999;background:#d20028;color:#fff;font:700 10px/1 Archivo,sans-serif;padding:4px 9px;border-radius:8px;pointer-events:none;letter-spacing:.08em">BETA</div>');
  rep('Bitte Passwort eingeben, um die Trainingspläne zu öffnen.', 'BETA-Testversion (Adrian Kathan, U15 II). Bitte Passwort eingeben.');
  return html;
}
function fromBetaToLive(beta){
  let h = beta;
  const rep = (a, b) => { if (!h.includes(a)) throw new Error('promote: nicht gefunden ' + a.slice(0,50)); h = h.split(a).join(b); };
  rep('<script src="./beta-data.enc.js"></script>', '<script src="./tp-data.enc.js"></script>\n<script src="./trainer-data.enc.js"></script>');
  rep("tpPwBeta", "tpPw");
  rep('<title>BETA · Trainingspläne KVV</title>', '<title>Trainingspläne KVV</title>');
  h = h.replace(/\n<div style="position:fixed;top:6px;right:6px;z-index:999;[^\n]*BETA<\/div>/, '');
  rep('BETA-Testversion (Adrian Kathan, U15 II). Bitte Passwort eingeben.', 'Bitte Passwort eingeben, um die Trainingspläne zu öffnen.');
  return h;
}
const a = process.argv.slice(2);
if (a[0] === '--live') {            // alte UI + Beta-Button
  fs.writeFileSync('index.html', addBetaButton(fs.readFileSync(a[1], 'utf8')));
  console.log('OK index.html (alte Oberflaeche + Beta-Button)');
} else if (a[0] === '--promote') {  // neue UI fuer alle
  fs.writeFileSync('index.html', fromBetaToLive(fs.readFileSync('beta.html', 'utf8')));
  console.log('OK index.html aus beta.html. Danach: TP_PASSWORD=... node build/encrypt_tpdata.js');
} else {
  const src = fs.readFileSync('index-live.html', 'utf8');
  fs.writeFileSync('beta.html', makeBetaHtml(src));
  fs.writeFileSync('beta-data.enc.js', encrypt(JSON.stringify(filterBeta(loadData())), BETA_PW));
  console.log('OK beta.html + beta-data.enc.js (Passwort ' + BETA_PW + ')');
}
