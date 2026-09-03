const fs = require('fs');
const vm = require('vm');

const sandbox = {
  window: { scrollTo: () => {} },
  document: {
    getElementById: () => ({ _html: '', set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; } }),
    querySelectorAll: () => [],
    querySelector: () => null,
  },
  console,
};
vm.createContext(sandbox);

const tpdata = fs.readFileSync('tp-data.js', 'utf8');
const html = fs.readFileSync('index-live.html', 'utf8');
const appScript = html.match(/<script>\n([\s\S]*)<\/script>\n<\/body>/)[1];

const tests = `
function check(name, fn) {
  try { fn(); console.log('OK  ', name); }
  catch (e) { console.log('FAIL', name, '->', e.message); console.log(e.stack.split('\\n').slice(0,4).join('\\n')); }
}

check('Startseite: kein view gewählt -> Landing-Page mit Gruppen- und Einzelplan-Auswahl, kein Absturz', () => {
  if (state.view !== null) throw new Error('initialer state.view sollte null sein (Startseite), ist: ' + JSON.stringify(state.view));
  const out = renderApp();
  if (!out.includes('landing')) throw new Error('Landing-Page-Markup fehlt: ' + out.slice(0,300));
  if (!out.includes('U9')) throw new Error('Gruppenauswahl fehlt: ' + out.slice(0,300));
  if (!out.includes('Adrian Kathan')) throw new Error('Einzelplanauswahl fehlt: ' + out.slice(0,300));
  if (out.includes('class="tabs"')) throw new Error('Tab-Leiste sollte auf der Startseite nicht sichtbar sein');
});

check('Nach Auswahl eines Plans: Reiter Woche ist immer aktiv (initial + nach Wechsel)', () => {
  state.view = {t:'a', id:'Adrian Kathan'};
  let out = renderApp();
  if (!out.includes('Adrian Kathan')) throw new Error('missing name');
  if (!out.includes('KW ' + state.kw)) throw new Error('missing week');
  if (state.tab !== 'Woche') throw new Error('Tab sollte nach Auswahl Woche sein, ist: ' + state.tab);
  state.tab = 'Statistik'; renderApp();
  state.view = {t:'g', id:'U9'}; state.tab = 'Woche'; state.day = 0;
  out = renderApp();
  if (!out.includes('U9')) throw new Error('Gruppenwechsel fehlgeschlagen');
});

check('all tabs for Adrian render without throw', () => {
  ['Woche','Jahr','Statistik','Benchmarks','Kader'].forEach(t => { state.tab = t; renderApp(); });
});

check('switch to group U9, all tabs', () => {
  state.view = {t:'g', id:'U9'}; state.tab='Woche'; state.day=0;
  ['Woche','Jahr','Statistik','Kader'].forEach(t => { state.tab = t; renderApp(); });
});

check('week nav far into past and future (U9)', () => {
  state.view = {t:'g', id:'U9'}; state.tab='Woche';
  let y = NOW.year, k = NOW.kw;
  for (let i=0;i<80;i++){ const nw = addWeeks(y,k,-1); y=nw.year; k=nw.kw; }
  state.year=y; state.kw=k; state.day=0;
  renderApp();
  console.log('   80 weeks in the past ->', y, 'KW', k);
  y = NOW.year; k = NOW.kw;
  for (let i=0;i<200;i++){ const nw = addWeeks(y,k,1); y=nw.year; k=nw.kw; }
  state.year=y; state.kw=k; state.day=0;
  renderApp();
  console.log('   200 weeks in the future ->', y, 'KW', k);
});

check('Levi Strolz (28.08. jetzt mit echter Einzelplan-Excel) zeigt reale Daten statt Platzhalter, kein Crash', () => {
  state.view = {t:'a', id:'Levi Strolz'}; state.tab='Woche'; state.year=NOW.year; state.kw=NOW.kw; state.day=0;
  const out = renderApp();
  if (out.includes('Keine Daten hinterlegt')) throw new Error('Levi Strolz hat jetzt eine echte Excel, sollte keinen Platzhalter mehr zeigen: ' + out.slice(0,300));
  if (!out.includes('Levi Strolz')) throw new Error('Name fehlt: ' + out.slice(0,300));
  ['Woche','Jahr','Statistik','Benchmarks','Kader'].forEach(t => { state.tab = t; renderApp(); });
});

check('SPOGY Gruppe (missing group data) shows empty state', () => {
  state.view = {t:'g', id:'SPOGY Gruppe'}; state.tab='Woche';
  const out = renderApp();
  if (!out.includes('Keine Daten hinterlegt')) throw new Error('expected empty-state message');
});

check('Benchmarks tab: Adrian has data, alle 8 SPOGY-Athlet:innen haben inzwischen mind. einen echten Wert (Jakob seit Fix ebenfalls), unbekannte Person zeigt weiterhin Platzhalter', () => {
  state.view = {t:'a', id:'Adrian Kathan'}; state.tab='Benchmarks';
  const out1 = renderApp();
  if (!out1.includes('8b+')) throw new Error('expected real benchmark value 8b+');
  ['Mariella Vierhauser','Raphael Hubmann','Jakob Burtscher','Linus Pfleger','Sophie Bickel','Matthäus Kathan','Levi Strolz'].forEach(n=>{
    if(!D.BENCH[n]) throw new Error(n + ' sollte inzwischen einen Benchmark-Eintrag haben (mind. Aufbau-Boulder-Sessions automatisch gezählt)');
  });
  state.view = {t:'a', id:'Noch Nie Gesehen'}; state.tab='Benchmarks';
  const out2 = renderApp();
  if (!out2.includes('Noch keine Werte')) throw new Error('expected placeholder for unknown athlete: ' + out2.slice(0,300));
});

check('Statistik Adrian: Saison 25/26 zeigt echten Load-Verlauf + ACWR + Verteilung', () => {
  state.view = {t:'a', id:'Adrian Kathan'}; state.tab='Statistik';
  const out = renderApp();
  if (!out.includes('SAISON 25/26')) throw new Error('Saison-Label fehlt: ' + out.slice(0,300));
  if (!out.includes('Load pro Woche')) throw new Error('Load-Chart fehlt, sollte für Adrian angezeigt werden: ' + out.slice(0,500));
  if (!out.includes('ACWR')) throw new Error('ACWR fehlt');
  if (!out.includes('Technik/Taktik')) throw new Error('Kategorie-Verteilung fehlt');
});

check('Statistik Sophie: genug Kategorien-Daten, aber Load-Chart ausgeblendet (zu wenig RPE/Dauer dokumentiert)', () => {
  state.view = {t:'a', id:'Sophie Bickel'}; state.tab='Statistik';
  const out = renderApp();
  if (out.includes('Load pro Woche')) throw new Error('Load-Chart sollte bei Sophie NICHT erscheinen (nur Adrian gut dokumentiert)');
  if (!out.includes('Technik/Taktik')) throw new Error('Kategorie-Verteilung sollte trotzdem da sein');
});

check('Statistik funktioniert jetzt auch für Gruppen (U9), Physis Wand/Boden korrekt getrennt', () => {
  state.view = {t:'g', id:'U9'}; state.tab='Statistik';
  const out = renderApp();
  if (!out.includes('Verteilung der Inhalte')) throw new Error('Verteilung fehlt für Gruppe: ' + out.slice(0,400));
  if (out.includes('Load pro Woche')) throw new Error('Gruppen haben kein Load, Chart sollte fehlen');
});

check('Statistik Gruppen: geschätzte Trainingsstunden (2,75h × echte Trainingstage), Adrian bleibt bei echter Dauer', () => {
  state.view = {t:'g', id:'U9'}; state.tab='Statistik';
  const outU9 = renderApp();
  if (!outU9.includes('geschätzt')) throw new Error('Schätz-Hinweis fehlt bei Gruppe: ' + outU9.slice(0,500));
  if (!outU9.includes('2.75')) throw new Error('2,75h-Annahme fehlt im Hinweistext');
  const d = window.TPDATA;
  const ss = d.SEASON_STATS['25/26']['g:U9'];
  if (ss.trainingDays == null || ss.estHours !== Math.round(ss.trainingDays*2.75*10)/10) throw new Error('estHours stimmt nicht mit trainingDays*2.75 überein');

  state.view = {t:'a', id:'Adrian Kathan'}; state.tab='Statistik';
  const outAdrian = renderApp();
  if (outAdrian.includes('geschätzt')) throw new Error('Adrian sollte weiterhin echte (nicht geschätzte) Trainingsstunden zeigen');
});

check('Statistik: Saison-Toggle nur im Statistik-Tab, andere Tabs (Woche/Jahr/Benchmarks) bleiben unbeeinflusst von statSeason', () => {
  const d = window.TPDATA;
  if (!Array.isArray(d.SEASONS) || d.SEASONS.length < 2) throw new Error('SEASONS fehlt/zu kurz: ' + JSON.stringify(d.SEASONS));
  state.view = {t:'a', id:'Adrian Kathan'}; state.tab='Statistik'; state.statSeason='25/26';
  const out2526 = renderApp();
  if (!out2526.includes('SAISON 25/26')) throw new Error('25/26 Label fehlt: ' + out2526.slice(0,300));
  if (!out2526.includes('Load pro Woche')) throw new Error('25/26 sollte weiterhin Load-Chart für Adrian zeigen');

  state.statSeason = '26/27';
  const out2627 = renderApp();
  if (!out2627.includes('SAISON 26/27')) throw new Error('26/27 Label fehlt: ' + out2627.slice(0,300));
  if (out2627.includes('Load pro Woche')) throw new Error('26/27 hat noch keine 10 Wochen Load-Doku, Chart sollte fehlen');
  if (!out2627.includes('Technik/Taktik')) throw new Error('Kategorie-Verteilung fehlt für 26/27');

  // Andere Tabs bleiben fortlaufend, unabhängig von statSeason
  state.tab = 'Woche'; state.year=2026; state.kw=36; state.day=1; state.weekView='tage';
  const wocheOut = renderApp();
  if (!wocheOut.includes('2-3 Onsight Gos')) throw new Error('Woche-Tab sollte weiterhin fortlaufend/unverändert sein: ' + wocheOut.slice(0,400));

  state.tab = 'Jahr';
  const jahrOut = renderApp();
  if (!jahrOut.includes('ribbonWrap')) throw new Error('Jahr-Tab sollte weiterhin fortlaufend/unverändert sein');

  state.tab = 'Benchmarks';
  const benchOut = renderApp();
  if (!benchOut.includes('8b+')) throw new Error('Benchmarks-Tab sollte weiterhin fortlaufend/unverändert sein');

  state.statSeason = '25/26'; state.tab='Statistik';
});

check('Woche KW36 Adrian shows updated Dienstag exercise + fuzzy duration + Notiz', () => {
  state.view = {t:'a', id:'Adrian Kathan'}; state.tab='Woche'; state.year=2026; state.kw=36; state.day=1; state.weekView='tage';
  const out = renderApp();
  if (!out.includes('2-3 Onsight Gos')) throw new Error('missing dienstag exercise: ' + out.slice(0,800));
  if (!out.includes('120 min')) throw new Error('missing fuzzy-matched duration for Onsight Gos: ' + out.slice(0,800));
  if (!out.includes('Gute Vorbereitung vor jedem Versuch')) throw new Error('missing updated Notiz: ' + out.slice(0,800));
});

check('Woche kompakt (Kurzform) view renders week-at-a-glance without throw, all 7 days', () => {
  state.view = {t:'a', id:'Adrian Kathan'}; state.tab='Woche'; state.year=2026; state.kw=36; state.day=1; state.weekView='kurz';
  const out = renderApp();
  if (!out.includes('kurzTable')) throw new Error('kurz view did not render: ' + out.slice(0,500));
  if (!out.includes('Technik/Taktik')) throw new Error('expected category tag for Dienstag in kurz view');
  state.weekView='tage';
});

check('Woche kompakt renders for a group plan too (U9)', () => {
  state.view = {t:'g', id:'U9'}; state.tab='Woche'; state.weekView='kurz';
  renderApp();
  state.weekView='tage';
});

check('Jahr tab renders for group U13 I without crash', () => {
  state.view = {t:'g', id:'U13 I'}; state.tab='Jahr';
  renderApp();
});

check('Jahr tab Adrian: reine Grafik-Ribbon mit echten Excel-Farben (kein Termine-Block mehr)', () => {
  state.view = {t:'a', id:'Adrian Kathan'}; state.tab='Jahr';
  const out = renderApp();
  if (!out.includes('jahrRibbon')) throw new Error('Phasen-Ribbon fehlt: ' + out.slice(0,400));
  if (!out.includes('ribbonCol')) throw new Error('Wochen-Spalten fehlen');
  if (!/Max|Aufbau|SK|KA/.test(out)) throw new Error('erwartete Phasen-Legende fehlt');
  if (!/#[0-9a-fA-F]{6}/.test(out)) throw new Error('echte Excel-Hex-Farbe fehlt im Output: ' + out.slice(0,400));
  if (out.includes('evRow') || out.includes('WK Termine')) throw new Error('Termine-Block sollte laut Vorgabe (erstmal) weg sein');
});

check('Jahr tab Gruppen (U9): eigener Phasen-Ribbon aus Jahresplan-Excel (Lead/Bouldern, echte Farben), kein Gesamtkalender mehr', () => {
  state.view = {t:'g', id:'U9'}; state.tab='Jahr';
  const out = renderApp();
  if (!out.includes('jahrRibbon')) throw new Error('Gruppen-Ribbon fehlt: ' + out.slice(0,400));
  if (!out.includes('Lead') && !out.includes('Bouldern')) throw new Error('Lead/Bouldern-Legende fehlt');
  if (!out.includes('#92D050') && !out.toLowerCase().includes('#92d050')) throw new Error('echte Grün-Farbe (Lead) aus Excel fehlt');
});

check('Jahr tab Sophie: Freitext-Phase wird als Text gezeigt, nicht als erfundener Phasen-Chip', () => {
  state.view = {t:'a', id:'Sophie Bickel'}; state.tab='Jahr';
  const out = renderApp();
  if (!out.includes('Vorbereitung LT, KA verbessern')) throw new Error('Freitext-Phase fehlt: ' + out.slice(0,400));
});

check('missing values render as "-" not blank/undefined', () => {
  const out = val(null) + '|' + val(undefined) + '|' + val('') + '|' + val(0) + '|' + val('8b+');
  if (out !== '-|-|-|0|8b+') throw new Error('val() broken: ' + out);
});

check('Woche Tage-Ansicht (U9, Do 17.09.): Zeit + Trainer + farbiger Ort-Pill sichtbar', () => {
  state.view = {t:'g', id:'U9'}; state.tab='Woche'; state.weekView='tage';
  state.year = 2026; state.kw = 38; state.day = 3;
  const out = renderApp();
  if (!out.includes('16:30-19:00')) throw new Error('Zeit fehlt: ' + out.slice(0,500));
  if (!out.includes('Florian')) throw new Error('Trainer fehlt: ' + out.slice(0,500));
  if (!out.includes('Steinblock Dornbirn')) throw new Error('Ort fehlt: ' + out.slice(0,500));
  if (!out.includes(ORT_COLORS.Bouldern)) throw new Error('Ort-Farbe (Blau=Bouldern) fehlt im Markup: ' + out.slice(0,500));
});

check('Woche kompakt (U9, KW38): Ort/Zeit/Trainer je Tag + farbiger Rahmen', () => {
  state.view = {t:'g', id:'U9'}; state.tab='Woche'; state.weekView='kurz';
  state.year = 2026; state.kw = 38; state.day = 0;
  const out = renderApp();
  if (!out.includes('16:30-19:00') || !out.includes('Florian')) throw new Error('Kompakt-Ansicht zeigt Zeit/Trainer nicht: ' + out.slice(0,600));
  if (!out.includes('border-left:4px solid ' + ORT_COLORS.Bouldern)) throw new Error('Kompakt-Ansicht faerbt Bouldern-Tag nicht: ' + out.slice(0,600));
  if (!out.includes('border-left:4px solid ' + ORT_COLORS.Lead)) throw new Error('Kompakt-Ansicht faerbt Lead-Tag nicht: ' + out.slice(0,600));
});

check('Individuen ohne Zeit/Trainer/Ort-Typ crashen nicht (Adrian)', () => {
  state.view = {t:'a', id:'Adrian Kathan'}; state.tab='Woche';
  state.weekView='tage'; state.year=NOW.year; state.kw=NOW.kw; state.day=0;
  renderApp();
  state.weekView='kurz';
  renderApp();
});

check('Header zeigt Austria-Climbing-Bildmarke, Vorarlberg-Logo und echte Tab-Icons (kein leeres Rechteck mehr)', () => {
  state.view = {t:'a', id:'Adrian Kathan'}; state.tab='Woche';
  const out = renderApp();
  if (!out.includes(MARK_IMG)) throw new Error('Brand-Mark fehlt');
  if (!out.includes(LOGO_IMG)) throw new Error('Vorarlberg-Logo fehlt');
  if (!out.includes('<svg')) throw new Error('Tab-Icons (SVG) fehlen, evtl. noch leere Rechtecke');
});

check('Technikfokus wird wörtlich übernommen, ohne erfundene Min/Sätze/Pause-Chips (Adrian KW38 Mi)', () => {
  state.view = {t:'a', id:'Adrian Kathan'}; state.tab='Woche'; state.weekView='tage';
  state.year = 2026; state.kw = 38; state.day = 2;
  const out = renderApp();
  if (!out.includes('Vorbereitung auf Go')) throw new Error('Technikfokus-Text fehlt: ' + out.slice(0,600));
  if (out.includes('90 min') || out.includes('Boulder a 8 Züge') || out.includes('Gos pro Boulder')) {
    throw new Error('Technikfokus zeigt weiterhin erfundene Fuzzy-Match-Chips: ' + out.slice(0,900));
  }
});

check('Jakob Burtscher (30.08. Fix: veraltete Root-Datei überschrieb echte Konfliktkopie): KW37/38 zeigen echte Orte/Sessions statt leer', () => {
  state.view = {t:'a', id:'Jakob Burtscher'}; state.tab='Woche'; state.weekView='tage';
  state.year = 2026; state.kw = 38; state.day = 0;
  const out = renderApp();
  if (!out.includes('SB Dornbirn')) throw new Error('Jakobs echter Ort (SB Dornbirn, KW38 Mo) fehlt weiterhin: ' + out.slice(0,600));
});

check('Jakob Burtscher KW36: neues Sheet leer, Inhalte werden automatisch aus alter Einheitenplanung nachgezogen', () => {
  state.view = {t:'a', id:'Jakob Burtscher'}; state.tab='Woche'; state.weekView='tage';
  state.year = 2026; state.kw = 36; state.day = 0;
  const out = renderApp();
  if (!out.includes('1-1,5h Spraywall Max')) throw new Error('Fallback-Inhalt aus alter Einheitenplanung fehlt (Mo KW36): ' + out.slice(0,700));
  state.day = 3;
  const out2 = renderApp();
  if (!out2.includes('BM Leiste HA 20 Sek')) throw new Error('Fallback-Inhalt fehlt (Do KW36): ' + out2.slice(0,700));
});

check('Startseite zeigt "Training gesamt" als eigene Option auf gleicher Ebene wie Gruppen-/Einzelpläne', () => {
  state.view = null;
  const out = renderApp();
  if (!out.includes('Training gesamt')) throw new Error('Option fehlt auf der Startseite: ' + out.slice(0,400));
});

check('Training gesamt (Do KW38/2026, Tag-Index 3): zeigt GENAU EINEN Tag, Gruppenpläne UND Einzelpläne sortiert, mit echtem Inhalt bis auf Übungsebene, keine Tab-Leiste, keine Wochen-Pfeile', () => {
  state.view = {t:'all'}; state.year = 2026; state.kw = 38; state.day = 3;
  const out = renderApp();
  if (!out.includes('Training gesamt')) throw new Error('Titel fehlt: ' + out.slice(0,300));
  if (!out.includes('Donnerstag')) throw new Error('Tagestitel (Donnerstag) fehlt: ' + out.slice(0,400));
  const iGroups = out.indexOf('Gruppenpläne');
  const iSolo = out.indexOf('Einzelpläne SPOGY');
  if (iGroups < 0 || iSolo < 0 || iGroups > iSolo) throw new Error('Reihenfolge falsch: erst Gruppenpläne, dann Einzelpläne SPOGY erwartet');
  if (!out.includes('U9')) throw new Error('Gruppe U9 fehlt');
  if (!out.includes('Adrian Kathan')) throw new Error('Athlet Adrian Kathan fehlt');
  if (!out.includes('Steinblock Dornbirn')) throw new Error('Exakter Ort/Inhalt von U9 (Do KW38) fehlt: ' + out.slice(0,300));
  if (out.includes('class="tabs"')) throw new Error('Tab-Leiste sollte bei "Training gesamt" nicht sichtbar sein');
  if (out.includes('data-act="prevWeek"') || out.includes('data-act="nextWeek"')) throw new Error('Wochen-Pfeile sollten hier durch Tages-Pfeile ersetzt sein');
  if (!out.includes('data-act="prevDay"') || !out.includes('data-act="nextDay"')) throw new Error('Tages-Pfeile fehlen: ' + out.slice(0,600));
});

check('Training gesamt: Tagesnavigation (prevDay/nextDay) blättert einen Tag weiter, auch über Wochengrenzen hinweg', () => {
  state.view = {t:'all'}; state.year = 2026; state.kw = 38; state.day = 6; // So KW38
  renderApp();
  const nd = addDays(state.year, state.kw, state.day, 1); // -> Mo KW39
  state.year = nd.year; state.kw = nd.kw; state.day = nd.day;
  const out = renderApp();
  if (nd.kw !== 39 || nd.day !== 0) throw new Error('addDays über Wochengrenze falsch berechnet: ' + JSON.stringify(nd));
  if (!out.includes('Montag')) throw new Error('Tagestitel nach Tageswechsel falsch: ' + out.slice(0,400));
});

check('Training gesamt: Tag ohne Plan für eine Gruppe/Athlet crasht nicht, zeigt Hinweistext statt Fehler', () => {
  state.view = {t:'all'}; state.year = 2020; state.kw = 3; state.day = 0;
  const out = renderApp();
  if (!out.includes('Kein Plan für diesen Tag')) throw new Error('erwarteter Leer-Hinweis fehlt: ' + out.slice(0,400));
});

check('Auswahl "Training gesamt" von der Startseite/Picker springt auf den heutigen Tag', () => {
  const t = renderPickOpts(null);
  if (!t.allOpt.includes('data-t="all"')) throw new Error('allOpt-Button fehlt data-t="all"');
});

console.log('DONE');
`;

vm.runInContext(tpdata + '\n' + appScript + '\n' + tests, sandbox, { filename: 'combined.js' });
