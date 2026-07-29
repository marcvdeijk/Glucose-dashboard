#!/usr/bin/env python3
"""
Patch: voegt de absorptiescore-picker (Verwerking) toe aan de edit-modal
van een bestaande KHD-entry (Ruwe data -> klik op entry). Alleen zichtbaar
als het om een khd-entry gaat. Slaat op via de bestaande absorptionScore
kolom, dus geen database-wijziging nodig.
"""
import pathlib
import sys

FILE = pathlib.Path("public/index.html")

if not FILE.exists():
    print(f"FOUT: {FILE} niet gevonden. Draai dit script vanuit ~/Desktop/Glucose-dashboard")
    sys.exit(1)

text = FILE.read_text(encoding="utf-8")

# --- 1. Titels-array toevoegen naast de bestaande ABSORPTION_EMOJI ---
anchor_titles = "const ABSORPTION_EMOJI = ['\\u26a1','\\ud83c\\udfc3','\\ud83d\\udeb6','\\ud83c\\udf7d\\ufe0f','\\ud83c\\udf55','\\ud83c\\udf56'];"

replacement_titles = anchor_titles + '''
const ABSORPTION_TITLES = ['Bliksemsnel (~45 min)','Snel (~1.5-2u)','Normaal (~2.5-3u)','Standaard maaltijd (~3.5-4u)','Vetrijk/traag (~5-6u)','Zeer traag (~7-8u)'];
let rdmAbsorptionScore = null;
function selectRdmAbsorptionScore(score, btn){
  const row = document.getElementById('rdmAbsorptionRow');
  if (rdmAbsorptionScore === score) {
    rdmAbsorptionScore = null;
    row.querySelectorAll('.dayBtn').forEach(b => b.classList.remove('dayBtnActive'));
    return;
  }
  rdmAbsorptionScore = score;
  row.querySelectorAll('.dayBtn').forEach(b => b.classList.remove('dayBtnActive'));
  btn.classList.add('dayBtnActive');
}'''

assert text.count(anchor_titles) == 1, "Anker (ABSORPTION_EMOJI) niet uniek gevonden — patch afgebroken."
text = text.replace(anchor_titles, replacement_titles)

# --- 2. Picker-HTML toevoegen in de modal, alleen voor khd-entries ---
anchor_modal_html = '''    '<div style="display:flex; flex-direction:column; gap:8px;">' +
      '<div style="display:flex; gap:6px; flex-wrap:wrap;">' +
        '<input id="rdmTs" type="datetime-local" value="' + tsLocal + '" style="flex:1; min-width:150px; ' + fieldStyle + '">' +'''

assert text.count(anchor_modal_html) == 1, "Anker (modal-HTML start) niet uniek gevonden — patch afgebroken."

replacement_modal_html = anchor_modal_html  # ts/type/bolusType regel blijft ongewijzigd, we voegen verderop toe

anchor_before_context = '''      '<textarea id="rdmContext" placeholder="Context" style="min-height:54px; ' + fieldStyle + '">' + (row.context||'') + '</textarea>' +'''

assert text.count(anchor_before_context) == 1, "Anker (voor context-textarea) niet uniek gevonden — patch afgebroken."

replacement_before_context = '''      (row.type === 'khd' ?
        '<div style="font-size:11px; font-weight:600; color:#8a8a86; text-transform:uppercase; letter-spacing:0.5px; margin-top:4px;">Verwerking</div>' +
        '<div class="pillRow" id="rdmAbsorptionRow" style="display:flex; gap:6px; flex-wrap:wrap;">' +
          ABSORPTION_TITLES.map((t, i) => '<button type="button" class="dayBtn' + (row.absorptionScore === i ? ' dayBtnActive' : '') + '" data-score="' + i + '" title="' + t + '" onclick="selectRdmAbsorptionScore(' + i + ',this)">' + ABSORPTION_EMOJI[i] + '</button>').join('') +
        '</div>'
      : '') +
      '<textarea id="rdmContext" placeholder="Context" style="min-height:54px; ' + fieldStyle + '">' + (row.context||'') + '</textarea>' +'''

text = text.replace(anchor_before_context, replacement_before_context)

# --- 3. rdmAbsorptionScore initialiseren bij het openen van de modal ---
anchor_open = "  const linksHtml = candidates.map(c =>"

assert text.count(anchor_open) == 1, "Anker (openRdModal init) niet uniek gevonden — patch afgebroken."
replacement_open = "  rdmAbsorptionScore = row.absorptionScore != null ? row.absorptionScore : null;\n" + anchor_open

text = text.replace(anchor_open, replacement_open)

# --- 4. saveRdModal: absorptionScore meesturen als het om khd gaat ---
anchor_save = '''  const bolusTypeEl = document.getElementById('rdmBolusType');
  const bolusType = bolusTypeEl ? bolusTypeEl.value : '';

  try {
    const res = await fetch(API_UPDATE + '?key=' + encodeURIComponent(WRITE_KEY) + '&id=' + encodeURIComponent(id) +
      '&desc=' + encodeURIComponent(desc) + '&amount=' + encodeURIComponent(amount) +
      '&tags=' + encodeURIComponent(tags) + '&context=' + encodeURIComponent(context) +
      '&ts=' + encodeURIComponent(ts) + '&type=' + encodeURIComponent(type) +
      '&bolusType=' + encodeURIComponent(bolusType));'''

assert text.count(anchor_save) == 1, "Anker (saveRdModal) niet uniek gevonden — patch afgebroken."

replacement_save = '''  const bolusTypeEl = document.getElementById('rdmBolusType');
  const bolusType = bolusTypeEl ? bolusTypeEl.value : '';
  const absorptionParam = type === 'khd' ? '&absorptionScore=' + encodeURIComponent(rdmAbsorptionScore != null ? rdmAbsorptionScore : '') : '';

  try {
    const res = await fetch(API_UPDATE + '?key=' + encodeURIComponent(WRITE_KEY) + '&id=' + encodeURIComponent(id) +
      '&desc=' + encodeURIComponent(desc) + '&amount=' + encodeURIComponent(amount) +
      '&tags=' + encodeURIComponent(tags) + '&context=' + encodeURIComponent(context) +
      '&ts=' + encodeURIComponent(ts) + '&type=' + encodeURIComponent(type) +
      '&bolusType=' + encodeURIComponent(bolusType) + absorptionParam);'''

text = text.replace(anchor_save, replacement_save)

FILE.write_text(text, encoding="utf-8")
print("Patch succesvol toegepast op public/index.html")
print(" - Verwerking-picker (absorptiescore) toegevoegd aan de KHD edit-modal")
print(" - Opslaan stuurt de aangepaste score mee naar de bestaande absorption_score kolom")
