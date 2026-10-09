#!/usr/bin/env node
// Verschluesselt die Trainer-Doku pro Zugang: build/trainer-plain.json (Klartext,
// .gitignored) -> trainer-data.enc.js (wird committet). Jedes Passwort oeffnet nur
// den eigenen Block (Name + zugeordnete Gruppen inkl. Eintraege).
// KDF: PBKDF2-SHA256 (gemeinsames Salt), Key K; kid = SHA256(K || "kid") -> findet
// den passenden Block ohne zweite KDF; Block = AES-256-GCM unter K.
const fs = require('fs');
const crypto = require('crypto');
const plain = JSON.parse(fs.readFileSync(__dirname + '/trainer-plain.json', 'utf8'));
const ITER = 600000; // hoeher, weil die Passwoerter kurz sind
const salt = crypto.randomBytes(16);
const users = plain.access.map((u) => {
  const K = crypto.pbkdf2Sync(u.password, salt, ITER, 32, 'sha256');
  const kid = crypto.createHash('sha256').update(Buffer.concat([K, Buffer.from('kid')])).digest('hex').slice(0, 16);
  const blob = JSON.stringify({
    name: u.name,
    groups: u.groups.map((id) => ({ id, label: (plain.groups.find((g) => g.id === id) || {}).label || id, entries: plain.entries[id] || [] })),
  });
  const iv = crypto.randomBytes(12);
  const c = crypto.createCipheriv('aes-256-gcm', K, iv);
  const ct = Buffer.concat([c.update(blob, 'utf8'), c.final(), c.getAuthTag()]);
  return { kid, iv: iv.toString('base64'), ct: ct.toString('base64') };
});
users.sort(() => Math.random() - 0.5);
fs.writeFileSync('trainer-data.enc.js', 'window.TRAINER_ENC = ' + JSON.stringify({ v: 1, iterations: ITER, salt: salt.toString('base64'), users }) + ';\n');
console.log('OK trainer-data.enc.js:', users.length, 'Zugaenge');
