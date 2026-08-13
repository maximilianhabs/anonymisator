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
  seiten: 0,
  dateigroesseBytes: null,
  naechsteId: 0,
  // Wird je Dokument einmal gesetzt, sobald der Prüfschritt bestätigt ist.
  geprueft: false,
};

const BUCHSTABEN = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
// Nur hier lag die Rollen-Heuristik erfahrungsgemäß daneben; bei E-Mail oder
// IBAN gibt es nichts umzustellen.
const UMSTELLBAR = new Set(['PATIENT', 'ARZT', 'PERSON', 'ORGANISATION', 'ORT', 'ADRESSE', 'MANUELL']);

const $ = (id) => document.getElementById(id);
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const farbe = (typ) => (Z.kategorien[typ] || {}).farbe || '#888';

/**
 * Entfernt jede Spur des bearbeiteten Dokuments aus dem Browser.
 *
 * Der Prüftext lebt allein hier — der Server hält nichts. Beim Wechsel zum
 * nächsten Dokument muss er deshalb vollständig verschwinden, samt der
 * Markierungen im angezeigten Text und dem Inhalt des Eingabefelds. Sonst
 * stünde der vorige Brief im Klartext im Speicher, während schon der
 * nächste bearbeitet wird.
 */
function zustandLoeschen() {
  Z.text = '';
  Z.gruppen = [];
  Z.kategorien = {};
  Z.dateiname = 'dokument';
  Z.seiten = 0;
  Z.dateigroesseBytes = null;
  Z.naechsteId = 0;
  Z.geprueft = false;
  Z.modus = 'original';

  const feld = $('eingabe-text');
  if (feld) feld.value = '';
  const auswahl = $('datei');
  if (auswahl) auswahl.value = '';

  // Der gerenderte Text steht als HTML in der Seite und muss ebenfalls fort.
  for (const id of ['dokument', 'gruppen', 'hinweise', 'bilanz', 'quelle-info', 'statistik-inhalt']) {
    const el = $(id);
    if (el) el.innerHTML = '';
  }
}

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
  // Die Browser-API kennt die Originalgrösse der Datei bereits, bevor sie
  // gesendet wird — der Server muss sie dafür nicht extra zurückmelden.
  Z.dateigroesseBytes = datei.size;
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
  Z.dateigroesseBytes = null;   // kein Datei-Upload, keine Dateigrösse
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
  Z.seiten = daten.seiten || 0;
  Z.geprueft = false;   // neues Dokument, neue Prüfung
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
  kategorienInAuswahl();
  zeichneAlles();
}

/** Füllt die Kategorieliste des Auswahlmenüs — einmal je Dokument. */
function kategorienInAuswahl() {
  const feld = $('auswahl-kategorie');
  if (!feld) return;
  feld.innerHTML = '';
  for (const typ of UMSTELLBAR) {
    if (!Z.kategorien[typ]) continue;
    const eintrag = document.createElement('option');
    eintrag.value = typ;
    eintrag.textContent = Z.kategorien[typ].titel;
    feld.appendChild(eintrag);
  }
  feld.value = 'MANUELL';
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
  // Im Ergebnis-Tab steht nur noch der fertige Text — die Unterscheidung
  // kräftig/gedämpft gibt es dort nicht, die Legende wäre irreführend.
  $('legende').hidden = nurErsetzte;
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

/**
 * Weist auf schwach belegte Treffer hin und bietet an, sie gesammelt
 * abzuwählen.
 *
 * Bewusst kein automatisches Kappen ab einer Anzahl: welche der erkannten
 * Personen die echten sind, lässt sich nicht an ihrer Zahl ablesen. Ein
 * Brief kann Patient, Angehörige, Zuweiser, Haus- und Fachärzte nennen und
 * damit zu Recht über einem Grenzwert liegen. Wer dort automatisch kappt,
 * lässt Klarnamen stehen — der teuerste Fehler, den dieses Werkzeug machen
 * kann. Also: alles bleibt ersetzt, aber der Blick wird gelenkt.
 */
function zeichneUnbelegtHinweis() {
  const alt = document.getElementById('unbelegt-hinweis');
  if (alt) alt.remove();

  const unbelegt = Z.gruppen.filter((g) => !g.sicher && g.aktiv);
  if (!unbelegt.length) return;

  const kasten = document.createElement('div');
  kasten.className = 'warnung';
  kasten.id = 'unbelegt-hinweis';
  kasten.innerHTML =
    `<b>${unbelegt.length} Treffer ohne Beleg.</b> Nur vom Sprachmodell `
    + 'vorgeschlagen, ohne Anrede oder Titel daneben. Sie werden ersetzt — '
    + 'hier stecken aber die meisten Fehlalarme.';

  const knopf = document.createElement('button');
  knopf.className = 'knopf klein';
  knopf.style.marginTop = '8px';
  knopf.textContent = `Diese ${unbelegt.length} abwählen`;
  knopf.onclick = () => {
    unbelegt.forEach((g) => { g.aktiv = false; });
    labelsVergeben();
    zeichneAlles();
  };
  kasten.appendChild(knopf);

  $('gruppen').prepend(kasten);
}

function zeichneStufen() {
  const behaelter = $('stufen-knoepfe');
  behaelter.innerHTML = '';

  for (const name of Z.stufenReihenfolge) {
    const info = Z.stufenInfo[name];
    const knopf = document.createElement('button');
    knopf.type = 'button';
    knopf.className = `stufe-${name}` + (name === Z.stufe ? ' aktiv' : '');
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

  const erlaeuterung = $('stufen-erlaeuterung');
  erlaeuterung.className = `stufen-erlaeuterung stufe-${Z.stufe}`;
  erlaeuterung.textContent = info.erlaeuterung || '';

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

    // Belegte Treffer zuerst, unbelegte darunter — dort lohnt das Nachsehen.
    const sortiert = [...gruppen].sort((a, b) => (a.sicher ? 0 : 1) - (b.sicher ? 0 : 1));
    for (const gruppe of sortiert) {
      block.appendChild(zeileFuer(gruppe));
    }
    behaelter.appendChild(block);
  }

  zeichneUnbelegtHinweis();

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
  name.className = 'name' + (gruppe.sicher ? '' : ' unbelegt');
  name.textContent = gruppe.anzeige;
  const zusatz = gruppe.varianten.filter((v) => v !== gruppe.anzeige);
  const hinweis = gruppe.sicher
    ? ''
    : '\n\nNur vom Sprachmodell vorgeschlagen — ohne Anrede, Titel oder '
      + 'sonstigen Beleg. Wird ersetzt, lohnt aber einen Blick.';
  name.title = (zusatz.length
    ? `Auch als: ${zusatz.join(', ')}\n(klicken: erste Fundstelle zeigen)`
    : 'Klicken: erste Fundstelle im Text zeigen') + hinweis;
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

/**
 * Aufschlüsselung nach Kategorie: wie viele Angaben je Art erkannt wurden,
 * wie viele davon tatsächlich ersetzt werden, dazu ein paar Eckdaten zum
 * Dokument selbst. Die Bilanz oben beantwortet "wie viel insgesamt";
 * das hier beantwortet "wovon wie viel".
 */
function zeichneStatistik() {
  const ziel = $('statistik-inhalt');
  if (!ziel) return;

  const nachTyp = [];
  let summeGruppen = 0;
  let summeFunde = 0;
  for (const typ of Object.keys(Z.kategorien)) {
    const gruppen = Z.gruppen.filter((g) => g.typ === typ);
    if (!gruppen.length) continue;
    const kat = Z.kategorien[typ];
    const ersetzt = gruppen.filter(wirdErsetzt).length;
    const funde = gruppen.reduce((s, g) => s + g.funde.length, 0);
    summeGruppen += gruppen.length;
    summeFunde += funde;
    nachTyp.push({ kat, gruppen: gruppen.length, ersetzt, funde });
  }

  const dokZeilen = [`${Z.text.length.toLocaleString('de-DE')} Zeichen`];
  if (Z.seiten) dokZeilen.push(`${Z.seiten} Seite${Z.seiten === 1 ? '' : 'n'}`);
  if (Z.dateigroesseBytes != null) {
    const mb = Z.dateigroesseBytes / (1024 * 1024);
    dokZeilen.push(mb >= 0.1
      ? `${mb.toLocaleString('de-DE', { maximumFractionDigits: 1 })} MB`
      : `${Math.round(Z.dateigroesseBytes / 1024)} KB`);
  }

  if (!nachTyp.length) {
    ziel.innerHTML = `<div class="statistik-dokument">Nichts erkannt · ${dokZeilen.join(' · ')}</div>`;
    return;
  }

  const kacheln = [
    [summeGruppen, 'Angaben'], [summeFunde, 'Fundstellen'],
    [Z.text.length.toLocaleString('de-DE'), 'Zeichen'],
  ].map(([zahl, label]) =>
    `<div class="statistik-kachel"><div class="statistik-zahl">${zahl}</div>`
    + `<div class="statistik-kachel-label">${label}</div></div>`).join('');

  // Die Anteilsleiste macht das Gewicht jeder Kategorie auf einen Blick
  // sichtbar — Fundstellen, nicht Angaben: eine dreimal erwähnte Person
  // soll auch dreimal so breit wirken.
  const anteil = nachTyp.map(({ kat, funde }) =>
    `<span style="width:${(funde / summeFunde) * 100}%;background:${kat.farbe}"></span>`
  ).join('');

  const zeilen = nachTyp.map(({ kat, gruppen, ersetzt, funde }) => {
    const zahl = ersetzt === gruppen
      ? `${gruppen}`
      : `${gruppen} <span class="klein">(${ersetzt} ersetzt)</span>`;
    return `<div class="statistik-zeile">`
      + `<span class="strich" style="background:${kat.farbe}"></span>`
      + `<span class="name">${esc(kat.titel)}</span><span>${zahl}</span></div>`;
  }).join('');

  ziel.innerHTML = `<div class="statistik-kacheln">${kacheln}</div>`
    + `<div class="statistik-anteil">${anteil}</div>`
    + zeilen
    + (Z.seiten || Z.dateigroesseBytes != null
      ? `<div class="statistik-dokument">${dokZeilen.slice(1).join(' · ')}</div>` : '');
}

function zeichneAlles() {
  zeichneStufen();
  zeichneDokument();
  zeichneSeitenleiste();
  zeichneBilanz();
  zeichneStatistik();
}

// ------------------------------------------------------- Eigener Begriff

// ------------------------------------------------- Markieren im Text
//
// Der Notausgang für alles, was keine Regel trifft: Text auswählen, Kategorie
// bestimmen, ersetzen. Anders als "Zusätzlich ersetzen" in der Seitenleiste
// wirkt das auf **genau die gewählte Stelle**, nicht auf jedes Vorkommen —
// nützlich, wenn dasselbe Wort einmal ein Name und einmal ein Fachbegriff ist.

let auswahlBereich = null;

/** Rechnet eine Auswahl im gerenderten HTML auf Zeichenpositionen im Text um. */
function auswahlZuBereich(auswahl) {
  const dok = $('dokument');
  if (!auswahl.rangeCount) return null;
  const bereich = auswahl.getRangeAt(0);
  if (bereich.collapsed || !dok.contains(bereich.commonAncestorContainer)) return null;

  // Zeichen vor dem Auswahlbeginn zählen — das ergibt den Versatz im
  // Originaltext, weil der angezeigte Text zeichengleich dazu ist.
  const davor = document.createRange();
  davor.selectNodeContents(dok);
  davor.setEnd(bereich.startContainer, bereich.startOffset);
  const start = davor.toString().length;
  const ende = start + bereich.toString().length;

  return start < ende ? { start, ende, text: Z.text.slice(start, ende) } : null;
}

function auswahlMenueZeigen() {
  const menue = $('auswahl-menue');
  const auswahl = window.getSelection();
  const bereich = auswahlZuBereich(auswahl);

  if (!bereich || !bereich.text.trim() || Z.modus !== 'original') {
    menue.hidden = true;
    auswahlBereich = null;
    return;
  }

  // Bereits abgedeckte Stellen nicht erneut anbieten.
  if (alleFunde(false).some((f) => bereich.start < f.ende && f.start < bereich.ende)) {
    menue.hidden = true;
    auswahlBereich = null;
    return;
  }

  auswahlBereich = bereich;
  const kurz = bereich.text.trim().replace(/\s+/g, ' ');
  $('auswahl-text').textContent = kurz.length > 30 ? kurz.slice(0, 30) + '…' : kurz;

  const rechteck = auswahl.getRangeAt(0).getBoundingClientRect();
  menue.hidden = false;
  menue.style.left = `${Math.max(8, rechteck.left)}px`;
  menue.style.top = `${rechteck.bottom + 6}px`;
}

/**
 * Findet jedes weitere Vorkommen von `suchtext` in `text` — exakt dieselbe
 * Zeichenfolge, Gross-/Kleinschreibung eingeschlossen, an einer Wortgrenze.
 *
 * Anders als "Zusätzlich ersetzen" (das jede Schreibvariante unabhängig von
 * Gross-/Kleinschreibung findet) bleibt das hier bewusst fallsensitiv: eine
 * von Hand markierte Stelle steht für eine bestimmte, konkrete Angabe in
 * exakt dieser Schreibweise, nicht für das Wort an sich. Spiegelt serverseitig
 * `_konsistenz_nachlauf` in app/detect.py, das dieselbe Wortgrenzenprüfung für
 * automatisch erkannte Treffer vornimmt.
 */
function wortgrenzenTreffer(text, suchtext) {
  const istWortzeichen = (z) => z !== undefined && /[\wÄÖÜäöüß]/.test(z);
  const treffer = [];
  let ab = 0;
  for (;;) {
    const i = text.indexOf(suchtext, ab);
    if (i === -1) break;
    if (!istWortzeichen(text[i - 1]) && !istWortzeichen(text[i + suchtext.length])) {
      treffer.push({ start: i, ende: i + suchtext.length });
    }
    ab = i + 1;
  }
  return treffer;
}

function auswahlUebernehmen() {
  if (!auswahlBereich) return;
  const typ = $('auswahl-kategorie').value;
  const text = auswahlBereich.text;
  const anzeige = text.trim().replace(/\s+/g, ' ');

  const funde = [{ start: auswahlBereich.start, ende: auswahlBereich.ende,
                   text, quelle: 'auswahl', formen: {} }];

  // Dieselbe Buchstabenfolge an anderer Stelle im Dokument gilt als dieselbe
  // Angabe und wird mitgenommen — sofern die Stelle noch frei ist. Kurze
  // Fragmente (unter 3 Zeichen) bleiben aussen vor, sonst würde eine
  // versehentlich markierte Silbe im ganzen Text nach sich ziehen.
  if (anzeige.length >= 3) {
    const belegt = alleFunde(false);
    for (const treffer of wortgrenzenTreffer(Z.text, anzeige)) {
      if (treffer.start === auswahlBereich.start) continue;
      if (belegt.some((f) => treffer.start < f.ende && f.start < treffer.ende)) continue;
      funde.push({ start: treffer.start, ende: treffer.ende, text: anzeige,
                   quelle: 'auswahl-nachlauf', formen: {} });
    }
  }

  Z.gruppen.push({
    id: `s${Z.naechsteId}`,
    typ,
    anzeige,
    label: '',
    initialen: '',
    aktiv: true,
    sicher: true,          // von Hand gesetzt — der stärkste Beleg überhaupt
    varianten: [anzeige],
    funde,
  });
  Z.naechsteId += 1;

  window.getSelection().removeAllRanges();
  $('auswahl-menue').hidden = true;
  auswahlBereich = null;
  labelsVergeben();
  zeichneAlles();
  const weitere = funde.length - 1;
  brot(weitere
    ? `„${anzeige.slice(0, 24)}" wird ersetzt — ${weitere + 1}× im Dokument.`
    : `„${anzeige.slice(0, 24)}" wird ersetzt.`);
}

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

/**
 * Verlangt vor dem ersten Export eine ausdrückliche Bestätigung.
 *
 * Der Prüfschritt ist Bestandteil des Verfahrens, nicht Zierrat: keine
 * automatische Erkennung erreicht volle Trefferquote. Ohne diese Rückfrage
 * liesse sich ein Dokument hochladen und sofort exportieren, ohne je eine
 * Fundstelle angesehen zu haben.
 *
 * Gefragt wird einmal je Dokument, nicht bei jedem Export — sonst wird die
 * Rückfrage zur Gewohnheit und damit wirkungslos.
 */
function pruefungBestaetigt() {
  if (Z.geprueft) return true;

  const unbelegt = Z.gruppen.filter((g) => !g.sicher && g.aktiv).length;
  const stellen = Z.gruppen.filter(wirdErsetzt)
    .reduce((summe, g) => summe + g.funde.length, 0);

  const text =
    `Vor dem Export bitte bestätigen:\n\n`
    + `Es werden ${stellen} Textstellen ersetzt`
    + (unbelegt ? `, davon ${unbelegt} Gruppen ohne Beleg.` : '.')
    + `\n\nHaben Sie den markierten Text durchgesehen?\n\n`
    + `Die Erkennung kann Namen übersehen — Vollständigkeit ist nicht `
    + `garantiert. Die Verantwortung für das weitergegebene Dokument bleibt `
    + `bei Ihnen.`;

  if (!window.confirm(text)) {
    brot('Export abgebrochen. Bitte die Markierungen durchsehen.', true);
    return false;
  }
  Z.geprueft = true;
  return true;
}

async function exportieren(format) {
  if (!pruefungBestaetigt()) return;

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

  // Auswahl im Text: Menü einblenden, sobald etwas markiert ist.
  document.addEventListener('selectionchange', () => {
    // Verzögert, damit die Auswahl beim Loslassen der Maus steht.
    clearTimeout(window._auswahlZeit);
    window._auswahlZeit = setTimeout(auswahlMenueZeigen, 120);
  });
  $('auswahl-hinzu').onclick = auswahlUebernehmen;
  // Klick ausserhalb schliesst das Menü, ohne die Auswahl zu übernehmen.
  document.addEventListener('mousedown', (e) => {
    if (!$('auswahl-menue').contains(e.target)) $('auswahl-menue').hidden = true;
  });
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
    zustandLoeschen();
    ansicht('eingabe');
    brot('Dokument verworfen.');
  };
}

start();
