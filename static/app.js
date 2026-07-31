/* Anonymisator — Frontend.
 *
 * Der Server ist zustandslos: er analysiert und er exportiert. Der aktuelle
 * Prüfstand (was ist an-, was abgewählt) lebt nur hier im Browser.
 */

'use strict';

const Z = {
  text: '',
  gruppen: [],
  kategorien: {},
  stufen: {},
  stufenInfo: {},
  stufenReihenfolge: [],
  stufe: 'standard',
  modus: 'original',
  dateiname: 'dokument',
  naechsteId: 0,
};

const BUCHSTABEN = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
// Nur hier lag die Rollen-Heuristik erfahrungsgemäß daneben; bei E-Mail oder
// IBAN gibt es nichts umzustellen.
const UMSTELLBAR = new Set(['PATIENT', 'ARZT', 'PERSON', 'KLINIK', 'ORT', 'ADRESSE', 'MANUELL']);

const $ = (id) => document.getElementById(id);
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const farbe = (typ) => (Z.kategorien[typ] || {}).farbe || '#888';

// ---------------------------------------------------------------- Ansichten

function ansicht(name) {
  $('ansicht-eingabe').hidden = name !== 'eingabe';
  $('ansicht-laden').hidden = name !== 'laden';
  $('ansicht-pruefen').hidden = name !== 'pruefen';
}

let brotZeit;
function brot(text, istFehler = false) {
  const el = $('brot');
  el.textContent = text;
  el.classList.toggle('fehler', istFehler);
  el.hidden = false;
  clearTimeout(brotZeit);
  brotZeit = setTimeout(() => { el.hidden = true; }, istFehler ? 7000 : 3200);
}

// ------------------------------------------------------------------- Analyse

async function analysiere(anfrage, ladeText) {
  $('lade-text').textContent = ladeText;
  ansicht('laden');
  try {
    const antwort = await fetch(anfrage.url, anfrage.optionen);
    if (!antwort.ok) {
      let meldung = `Fehler ${antwort.status}`;
      try { meldung = (await antwort.json()).detail || meldung; } catch (_) {}
      throw new Error(meldung);
    }
    uebernehmen(await antwort.json());
    ansicht('pruefen');
  } catch (fehler) {
    ansicht('eingabe');
    brot(fehler.message, true);
  }
}

function dateiAnalysieren(datei) {
  Z.dateiname = datei.name.replace(/\.[^.]+$/, '');
  const formular = new FormData();
  formular.append('datei', datei);
  analysiere(
    { url: '/api/analysieren/datei', optionen: { method: 'POST', body: formular } },
    `„${datei.name}" wird gelesen …`,
  );
}

function textAnalysieren() {
  const text = $('eingabe-text').value;
  if (!text.trim()) { brot('Bitte zuerst Text einfügen.', true); return; }
  Z.dateiname = 'text';
  analysiere({
    url: '/api/analysieren/text',
    optionen: {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    },
  }, 'Text wird analysiert …');
}

function uebernehmen(daten) {
  Z.text = daten.text;
  Z.gruppen = daten.gruppen;
  Z.kategorien = daten.kategorien;
  Z.stufen = daten.stufen;
  Z.stufenInfo = daten.stufen_info;
  Z.stufenReihenfolge = daten.stufen_reihenfolge;
  Z.naechsteId = daten.gruppen.length;
  Z.modus = 'original';

  document.querySelectorAll('.umschalter button').forEach((b) =>
    b.classList.toggle('aktiv', b.dataset.modus === 'original'));

  const beschreibung = {
    'pdf-textlayer': `PDF, ${daten.seiten} Seite(n), Textlayer`,
    'pdf-ocr': `PDF, ${daten.seiten} Seite(n), per OCR gelesen`,
    docx: 'Word-Dokument',
    paste: 'Eingefügter Text',
  }[daten.quelle] || daten.quelle;
  $('quelle-info').textContent = `${beschreibung} · ${Z.text.length.toLocaleString('de-DE')} Zeichen`;

  $('hinweise').innerHTML = daten.hinweise.map((h) => `<p>${esc(h)}</p>`).join('');
  labelsVergeben();
  zeichneAlles();
}

// -------------------------------------------------------------- Pseudonyme

// Welche Behandlung erfährt diese Kategorie auf der gewählten Stufe?
function behandlung(typ) {
  return (Z.stufen[Z.stufe] || {})[typ] || 'ersetzen';
}

/**
 * Wodurch wird diese Fundstelle ersetzt? null heisst: sie bleibt stehen.
 *
 * Gruppenweite Behandlungen (Initialen, Pseudonym) gelten für alle Stellen
 * gleich. Datumsabhängige Formen unterscheiden sich je Fundstelle und kommen
 * vorberechnet vom Server.
 */
function ersatzFuer(gruppe, fund) {
  if (!gruppe.aktiv) return null;
  const art = behandlung(gruppe.typ);
  if (art === 'behalten') return null;
  if (art === 'initialen') return gruppe.initialen || gruppe.label;
  if (art === 'ersetzen') return gruppe.label;
  return (fund.formen && fund.formen[art]) || gruppe.label;
}

function wirdErsetzt(gruppe) {
  return gruppe.aktiv && behandlung(gruppe.typ) !== 'behalten';
}

function labelsVergeben() {
  const zaehler = {};
  const aktive = Z.gruppen
    .filter(wirdErsetzt)
    .sort((a, b) => (a.funde[0]?.start ?? 0) - (b.funde[0]?.start ?? 0));

  for (const gruppe of aktive) {
    const kat = Z.kategorien[gruppe.typ];
    const n = zaehler[gruppe.typ] ?? 0;
    zaehler[gruppe.typ] = n + 1;
    let suffix;
    if (kat.stil === 'letter') {
      suffix = n < 26
        ? BUCHSTABEN[n]
        : BUCHSTABEN[Math.floor(n / 26) - 1] + BUCHSTABEN[n % 26];
    } else {
      suffix = String(n + 1);
    }
    gruppe.label = `[${kat.label}_${suffix}]`;
  }
  Z.gruppen.filter((g) => !wirdErsetzt(g)).forEach((g) => { g.label = ''; });
}

// --------------------------------------------------------------- Zeichnen

function alleFunde(nurErsetzte) {
  const liste = [];
  for (const gruppe of Z.gruppen) {
    const ersetzt = wirdErsetzt(gruppe);
    if (nurErsetzte && !ersetzt) continue;
    for (const fund of gruppe.funde) {
      liste.push({
        ...fund, gid: gruppe.id, typ: gruppe.typ,
        ersetzt, ersatz: ersatzFuer(gruppe, fund),
      });
    }
  }
  return liste.sort((a, b) => a.start - b.start);
}

function zeichneDokument() {
  const nurErsetzte = Z.modus === 'ergebnis';
  let html = '';
  let pos = 0;

  for (const fund of alleFunde(nurErsetzte)) {
    if (fund.start < pos) continue; // Überlappung — sollte nicht vorkommen
    html += esc(Z.text.slice(pos, fund.start));
    if (Z.modus === 'ergebnis') {
      html += `<mark class="ers" style="--c:${farbe(fund.typ)}">${esc(fund.ersatz)}</mark>`;
    } else {
      // Gestrichelt heisst: erkannt, aber auf dieser Stufe nicht ersetzt —
      // entweder abgewählt oder von der Stufe auf "behalten" gesetzt.
      const titel = `${Z.kategorien[fund.typ].titel}${fund.ersetzt ? ` → ${fund.ersatz}` : ' — bleibt stehen'}`;
      html += `<mark class="tr${fund.ersetzt ? '' : ' aus'}" data-g="${fund.gid}" `
        + `style="--c:${farbe(fund.typ)}" title="${esc(titel)}"`
        + `>${esc(Z.text.slice(fund.start, fund.ende))}</mark>`;
    }
    pos = fund.ende;
  }
  html += esc(Z.text.slice(pos));
  $('dokument').innerHTML = html;
}

function zeichneStufen() {
  const behaelter = $('stufen-knoepfe');
  behaelter.innerHTML = '';

  for (const name of Z.stufenReihenfolge) {
    const info = Z.stufenInfo[name];
    const knopf = document.createElement('button');
    knopf.type = 'button';
    knopf.className = name === Z.stufe ? 'aktiv' : '';
    // Der sichtbare Text steckt in zwei Kindelementen; ohne aria-label bleibt
    // der Knopf für Vorlesesoftware namenlos.
    knopf.setAttribute('aria-label', `${info.titel} — ${info.untertitel}. ${info.zweck}`);
    knopf.setAttribute('aria-pressed', String(name === Z.stufe));
    knopf.title = info.zweck;
    knopf.innerHTML = `<strong>${esc(info.titel)}</strong>`
      + `<span>${esc(info.untertitel)}</span>`;
    knopf.onclick = () => {
      Z.stufe = name;
      labelsVergeben();
      zeichneAlles();
    };
    behaelter.appendChild(knopf);
  }

  const info = Z.stufenInfo[Z.stufe] || {};
  $('stufen-zweck').textContent = info.zweck || '';

  const warnung = $('stufen-warnung');
  warnung.hidden = !info.warnung;
  if (info.warnung) warnung.textContent = info.warnung;
}

function zeichneBilanz() {
  const ersetzte = Z.gruppen.filter(wirdErsetzt);
  const stellen = ersetzte.reduce((summe, g) => summe + g.funde.length, 0);
  const stehen = Z.gruppen.length - ersetzte.length;
  $('bilanz').innerHTML =
    `<b>${stellen}</b> Textstellen werden ersetzt<br>`
    + `<span class="klein">${ersetzte.length} von ${Z.gruppen.length} Gruppen`
    + `${stehen ? ` · ${stehen} bleiben stehen` : ''}</span>`;

  const personen = Z.gruppen.filter((g) => ['PATIENT', 'ARZT', 'PERSON'].includes(g.typ));
  const warnung = $('warnung');
  if (personen.length === 0 && Z.text.length > 200) {
    warnung.hidden = false;
    warnung.innerHTML = '<strong>Kein einziger Personenname erkannt.</strong> '
      + 'Bei einem Arztbrief oder Gutachten ist das ungewöhnlich. Bitte den Text '
      + 'besonders sorgfältig durchsehen und Namen über „Zusätzlich ersetzen" ergänzen.';
  } else {
    warnung.hidden = true;
  }
}

function zeichneSeitenleiste() {
  const behaelter = $('gruppen');
  behaelter.innerHTML = '';

  for (const typ of Object.keys(Z.kategorien)) {
    const gruppen = Z.gruppen.filter((g) => g.typ === typ);
    if (!gruppen.length) continue;

    const kat = Z.kategorien[typ];
    const block = document.createElement('div');
    block.className = 'kategorie';

    const alleAktiv = gruppen.every((g) => g.aktiv);
    const kopf = document.createElement('div');
    kopf.className = 'kategorie-kopf';
    kopf.innerHTML = `<span class="strich" style="background:${kat.farbe}"></span>`
      + `<h3>${esc(kat.titel)} (${gruppen.length})</h3>`;
    const alleKnopf = document.createElement('button');
    alleKnopf.className = 'alle';
    alleKnopf.textContent = alleAktiv ? 'keine' : 'alle';
    alleKnopf.onclick = () => {
      gruppen.forEach((g) => { g.aktiv = !alleAktiv; });
      labelsVergeben();
      zeichneAlles();
    };
    kopf.appendChild(alleKnopf);
    block.appendChild(kopf);

    for (const gruppe of gruppen) {
      block.appendChild(zeileFuer(gruppe));
    }
    behaelter.appendChild(block);
  }

  if (!Z.gruppen.length) {
    behaelter.innerHTML = '<p class="hilfe" style="padding:16px 18px">'
      + 'Nichts erkannt. Über „Zusätzlich ersetzen" lassen sich Begriffe von Hand ergänzen.</p>';
  }
}

// Wie die Ersetzung in der Seitenleiste angekündigt wird.
const BEHANDLUNG_ZUSATZ = {
  verschoben: ' (verschoben)',
  dekade: '',
  jahrgang: '',
  nur_ort: '',
  initialen: '',
  ersetzen: '',
};

function zeileFuer(gruppe) {
  const zeile = document.createElement('div');
  zeile.className = 'zeile' + (wirdErsetzt(gruppe) ? '' : ' inaktiv');

  const haken = document.createElement('input');
  haken.type = 'checkbox';
  haken.checked = gruppe.aktiv;
  haken.title = 'Diese Gruppe ersetzen';
  haken.onchange = () => {
    gruppe.aktiv = haken.checked;
    labelsVergeben();
    zeichneAlles();
  };

  const name = document.createElement('span');
  name.className = 'name';
  name.textContent = gruppe.anzeige;
  const zusatz = gruppe.varianten.filter((v) => v !== gruppe.anzeige);
  name.title = zusatz.length
    ? `Auch als: ${zusatz.join(', ')}\n(klicken: erste Fundstelle zeigen)`
    : 'Klicken: erste Fundstelle im Text zeigen';
  name.onclick = () => zeigeFundstelle(gruppe);

  const anzahl = document.createElement('span');
  anzahl.className = 'anzahl';
  anzahl.textContent = `${gruppe.funde.length}×`;

  zeile.append(haken, name, anzahl);

  const label = document.createElement('span');
  label.className = 'marke-label';
  label.style.gridColumn = '2 / 4';
  const art = behandlung(gruppe.typ);
  if (!gruppe.aktiv) {
    label.textContent = '→ abgewählt, bleibt im Text';
  } else if (art === 'behalten') {
    label.textContent = '→ bleibt unverändert';
    label.classList.add('bleibt');
  } else {
    label.textContent = `→ ${ersatzFuer(gruppe, gruppe.funde[0])}`
      + (BEHANDLUNG_ZUSATZ[art] || '');
  }
  zeile.appendChild(label);

  if (UMSTELLBAR.has(gruppe.typ)) {
    const wahl = document.createElement('select');
    wahl.title = 'Kategorie korrigieren';
    for (const typ of Object.keys(Z.kategorien)) {
      const option = document.createElement('option');
      option.value = typ;
      option.textContent = Z.kategorien[typ].titel;
      option.selected = typ === gruppe.typ;
      wahl.appendChild(option);
    }
    wahl.onchange = () => {
      gruppe.typ = wahl.value;
      labelsVergeben();
      zeichneAlles();
    };
    zeile.appendChild(wahl);
  }
  return zeile;
}

function zeigeFundstelle(gruppe) {
  if (Z.modus !== 'original') {
    Z.modus = 'original';
    document.querySelectorAll('.umschalter button').forEach((b) =>
      b.classList.toggle('aktiv', b.dataset.modus === 'original'));
    zeichneDokument();
  }
  const treffer = $('dokument').querySelector(`mark[data-g="${gruppe.id}"]`);
  if (!treffer) return;
  treffer.scrollIntoView({ behavior: 'smooth', block: 'center' });
  treffer.classList.remove('blitz');
  void treffer.offsetWidth; // Animation neu starten
  treffer.classList.add('blitz');
}

function zeichneAlles() {
  zeichneStufen();
  zeichneDokument();
  zeichneSeitenleiste();
  zeichneBilanz();
}

// ------------------------------------------------------- Eigener Begriff

async function begriffHinzufuegen() {
  const feld = $('eigener-begriff');
  const begriff = feld.value.trim();
  const rueckmeldung = $('begriff-rueckmeldung');
  if (begriff.length < 2) {
    rueckmeldung.textContent = 'Bitte mindestens zwei Zeichen eingeben.';
    rueckmeldung.className = 'hilfe leer';
    return;
  }

  const antwort = await fetch('/api/begriff', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: Z.text, begriff, naechste_id: `m${Z.naechsteId}` }),
  });
  const daten = await antwort.json();

  if (!daten.gefunden) {
    rueckmeldung.textContent = `„${begriff}" kommt im Text nicht vor.`;
    rueckmeldung.className = 'hilfe leer';
    return;
  }

  // Stellen verwerfen, die bereits von einer anderen Gruppe abgedeckt sind —
  // sonst würden zwei Ersetzungen auf denselben Bereich zeigen.
  const belegt = alleFunde(false);
  const frei = daten.gruppe.funde.filter(
    (f) => !belegt.some((b) => f.start < b.ende && b.start < f.ende));

  if (!frei.length) {
    rueckmeldung.textContent = `„${begriff}" ist bereits vollständig abgedeckt.`;
    rueckmeldung.className = 'hilfe';
    feld.value = '';
    return;
  }

  daten.gruppe.funde = frei;
  Z.gruppen.push(daten.gruppe);
  Z.naechsteId += 1;
  labelsVergeben();
  zeichneAlles();

  rueckmeldung.textContent = `„${begriff}" ${frei.length}× ergänzt.`;
  rueckmeldung.className = 'hilfe treffer';
  feld.value = '';
}

// ---------------------------------------------------------------- Export

function ersetzungen() {
  const liste = [];
  for (const gruppe of Z.gruppen) {
    for (const fund of gruppe.funde) {
      const ersatz = ersatzFuer(gruppe, fund);
      if (ersatz === null) continue;
      liste.push({ start: fund.start, ende: fund.ende, label: ersatz });
    }
  }
  return liste;
}

function ergebnisText() {
  let text = Z.text;
  const liste = ersetzungen().sort((a, b) => b.start - a.start);
  for (const e of liste) {
    text = text.slice(0, e.start) + e.label + text.slice(e.ende);
  }
  return text;
}

async function exportieren(format) {
  const knoepfe = document.querySelectorAll('.export-knoepfe button');
  knoepfe.forEach((b) => { b.disabled = true; });
  try {
    const antwort = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: Z.text,
        ersetzungen: ersetzungen(),
        format,
        dateiname: Z.dateiname,
        mit_kopfzeile: $('mit-kopfzeile').checked,
        stufe: Z.stufe,
      }),
    });
    if (!antwort.ok) throw new Error(`Export fehlgeschlagen (${antwort.status})`);

    const blob = await antwort.blob();
    const kopf = antwort.headers.get('Content-Disposition') || '';
    const name = (kopf.match(/filename="([^"]+)"/) || [])[1]
      || `${Z.dateiname}_anonymisiert.${format}`;

    const url = URL.createObjectURL(blob);
    const anker = document.createElement('a');
    anker.href = url;
    anker.download = name;
    anker.click();
    URL.revokeObjectURL(url);
    brot(`${name} gespeichert.`);
  } catch (fehler) {
    brot(fehler.message, true);
  } finally {
    knoepfe.forEach((b) => { b.disabled = false; });
  }
}

function schluesselHerunterladen() {
  const aktive = Z.gruppen.filter(wirdErsetzt);
  if (!aktive.length) { brot('Nichts zu exportieren.', true); return; }

  const bestaetigt = confirm(
    'Die Zuordnungstabelle enthält die Klarnamen im Klartext.\n\n'
    + 'Wer sie zusammen mit dem anonymisierten Dokument aufbewahrt, hebt die '
    + 'Anonymisierung faktisch auf. Nur getrennt und geschützt speichern.\n\n'
    + 'Trotzdem herunterladen?');
  if (!bestaetigt) return;

  const zeilen = [['Ersetzt durch', 'Kategorie', 'Klartext',
                   'Weitere Schreibweisen', 'Fundstellen', 'Stufe']];
  for (const gruppe of aktive.sort((a, b) => a.anzeige.localeCompare(b.anzeige))) {
    zeilen.push([
      ersatzFuer(gruppe, gruppe.funde[0]),
      Z.kategorien[gruppe.typ].titel,
      gruppe.anzeige,
      gruppe.varianten.filter((v) => v !== gruppe.anzeige).join(' | '),
      String(gruppe.funde.length),
      Z.stufenInfo[Z.stufe].titel,
    ]);
  }
  const csv = '﻿' + zeilen
    .map((z) => z.map((f) => `"${String(f).replace(/"/g, '""')}"`).join(';'))
    .join('\r\n');

  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const anker = document.createElement('a');
  anker.href = url;
  anker.download = `${Z.dateiname}_ZUORDNUNG_VERTRAULICH.csv`;
  anker.click();
  URL.revokeObjectURL(url);
}

// ------------------------------------------------------------ Verdrahtung

function start() {
  const ablage = $('ablage');
  const datei = $('datei');

  $('knopf-auswaehlen').onclick = () => datei.click();
  datei.onchange = () => { if (datei.files[0]) dateiAnalysieren(datei.files[0]); };
  $('knopf-text').onclick = textAnalysieren;

  ['dragenter', 'dragover'].forEach((e) => ablage.addEventListener(e, (ev) => {
    ev.preventDefault();
    ablage.classList.add('aktiv');
  }));
  ['dragleave', 'drop'].forEach((e) => ablage.addEventListener(e, (ev) => {
    ev.preventDefault();
    ablage.classList.remove('aktiv');
  }));
  ablage.addEventListener('drop', (ev) => {
    if (ev.dataTransfer.files[0]) dateiAnalysieren(ev.dataTransfer.files[0]);
  });
  // Ein Fehlgriff neben die Ablagefläche darf die Datei nicht im Browser öffnen.
  ['dragover', 'drop'].forEach((e) =>
    window.addEventListener(e, (ev) => ev.preventDefault()));

  document.querySelectorAll('.umschalter button').forEach((knopf) => {
    knopf.onclick = () => {
      Z.modus = knopf.dataset.modus;
      document.querySelectorAll('.umschalter button').forEach((b) =>
        b.classList.toggle('aktiv', b === knopf));
      zeichneDokument();
    };
  });

  $('dokument').addEventListener('click', (ev) => {
    const treffer = ev.target.closest('mark.tr');
    if (!treffer) return;
    const gruppe = Z.gruppen.find((g) => g.id === treffer.dataset.g);
    if (!gruppe) return;
    gruppe.aktiv = !gruppe.aktiv;
    labelsVergeben();
    zeichneAlles();
  });

  $('knopf-begriff').onclick = begriffHinzufuegen;
  $('eigener-begriff').addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter') begriffHinzufuegen();
  });

  document.querySelectorAll('.export-knoepfe button').forEach((knopf) => {
    knopf.onclick = () => exportieren(knopf.dataset.format);
  });

  $('knopf-kopieren').onclick = async () => {
    try {
      await navigator.clipboard.writeText(ergebnisText());
      brot('Anonymisierter Text kopiert.');
    } catch (_) {
      brot('Zwischenablage nicht verfügbar.', true);
    }
  };

  $('knopf-schluessel').onclick = schluesselHerunterladen;

  $('knopf-neu').onclick = () => {
    Z.text = '';
    Z.gruppen = [];
    $('eingabe-text').value = '';
    datei.value = '';
    ansicht('eingabe');
  };
}

start();
