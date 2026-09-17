#!/usr/bin/env node
// Verschluesselt tp-data.js (Klartext, von build_tpdata_v2.py erzeugt) zu
// tp-data.enc.js -- letzteres wird ins Repo committet und von index.html
// geladen, tp-data.js bleibt lokales Build-Artefakt (.gitignore) und wird
// NICHT committet. AES-256-GCM + PBKDF2-SHA256, kompatibel zur WebCrypto-
// Entschluesselung im Browser (siehe index.html: decryptTPData()).
//
// Aufruf:
//   TP_PASSWORD="geheim" node build/encrypt_tpdata.js
// oder ohne TP_PASSWORD gesetzt: interaktive Passwort-Abfrage.
const fs = require('fs');
const crypto = require('crypto');
const readline = require('readline');

function getPassword() {
  if (process.env.TP_PASSWORD) return Promise.resolve(process.env.TP_PASSWORD);
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question('Passwort fuer die Trainingsplan-App: ', (pw) => { rl.close(); resolve(pw); });
  });
}

(async () => {
  const raw = fs.readFileSync('tp-data.js', 'utf8').trim();
  const prefix = 'window.TPDATA = ';
  if (!raw.startsWith(prefix)) throw new Error('tp-data.js hat unerwartetes Format (erwartet: "window.TPDATA = {...}")');
  const jsonStr = raw.slice(prefix.length).replace(/;\s*$/, '');
  JSON.parse(jsonStr); // Validierung -- wirft, falls kaputt

  const password = (await getPassword()).trim();
  if (!password) throw new Error('Kein Passwort angegeben -- abgebrochen.');

  const ITERATIONS = 250000;
  const salt = crypto.randomBytes(16);
  const iv = crypto.randomBytes(12);
  const key = crypto.pbkdf2Sync(password, salt, ITERATIONS, 32, 'sha256');
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const encrypted = Buffer.concat([cipher.update(jsonStr, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  const ct = Buffer.concat([encrypted, tag]); // WebCrypto erwartet Tag ans Ende angehaengt

  const payload = {
    v: 1,
    kdf: 'PBKDF2',
    hash: 'SHA-256',
    iterations: ITERATIONS,
    salt: salt.toString('base64'),
    iv: iv.toString('base64'),
    ct: ct.toString('base64'),
  };
  const out = 'window.TPDATA_ENC = ' + JSON.stringify(payload) + ';\n';
  fs.writeFileSync('tp-data.enc.js', out);
  console.log('OK tp-data.enc.js geschrieben (' + out.length + ' bytes, ' + ITERATIONS + ' PBKDF2-Iterationen)');
})().catch((e) => { console.error('FEHLER:', e.message); process.exit(1); });
