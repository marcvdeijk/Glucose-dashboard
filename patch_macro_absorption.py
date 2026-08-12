#!/usr/bin/env python3
"""
Patch: macro-gebaseerde COB/absorptie (FPU-formule).
Voegt optionele vet/eiwit/calorieen-velden toe aan quick-log en edit-modal,
en breidt de forecast-engine uit met macro-prioriteit boven de 0-5 schaal.
Draai dit vanuit ~/Desktop/Glucose-dashboard.

LET OP: draai eerst de D1-schema-migratie (zie instructies in chat) voordat je dit
patch script uitvoert en deployt - anders breekt de data-ophaal-query.
"""
import pathlib

def apply(src, old, new, label):
    count = src.count(old)
    assert count == 1, f"[{label}] anchor gevonden {count}x, verwacht 1x"
    print(f"OK: {label}")
    return src.replace(old, new)

# ============ FRONTEND: public/index.html ============
FE = pathlib.Path("public/index.html")
fe = FE.read_text()

fe = apply(fe,
    """          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
            <input id="qlContext" type="text" placeholder="Context (optioneel)" style="flex:1; min-width:140px; background:rgba(255,255,255,0.06); color:#e4e4e0; border:0.5px solid rgba(255,255,255,0.14); border-radius:10px; padding:8px 10px;">
          </div>""",
    """          <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center; margin-top:8px;">
            <span style="font-size:11px; color:#8a8a86;">Macro's (optioneel):</span>
            <input id="qlFat" type="number" step="0.1" placeholder="vet (g)" style="width:80px; background:rgba(255,255,255,0.06); color:#e4e4e0; border:0.5px solid rgba(255,255,255,0.14); border-radius:8px; padding:6px 8px; font-size:13px;">
            <input id="qlProtein" type="number" step="0.1" placeholder="eiwit (g)" style="width:80px; background:rgba(255,255,255,0.06); color:#e4e4e0; border:0.5px solid rgba(255,255,255,0.14); border-radius:8px; padding:6px 8px; font-size:13px;">
            <input id="qlCalories" type="number" step="1" placeholder="kcal (optioneel)" style="width:110px; background:rgba(255,255,255,0.06); color:#e4e4e0; border:0.5px solid rgba(255,255,255,0.14); border-radius:8px; padding:6px 8px; font-size:13px;">
          </div>
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
            <input id="qlContext" type="text" placeholder="Context (optioneel)" style="flex:1; min-width:140px; background:rgba(255,255,255,0.06); color:#e4e4e0; border:0.5px solid rgba(255,255,255,0.14); border-radius:10px; padding:8px 10px;">
          </div>""",
    "HTML: macro-velden quick-log")

fe = apply(fe,
    """async function quickLog(){
  const { clean: descRaw, tags: extractedTags } = getChipInputContent('qlDesc');
  const carbs = document.getElementById('qlCarbs').value.trim();
  const context = document.getElementById('qlContext').value.trim();
  const ts = buildTs('ql', 'qlTimeOnly');
  const status = document.getElementById('qlStatus');
  if (!descRaw && !extractedTags.length){ status.textContent = 'Vul in wat je hebt gegeten.'; return; }
  const desc = descRaw || extractedTags.map(t => '@' + t).join(' ');

  const tags = extractedTags.join(',');

  const absorptionParam = qlAbsorptionScore != null ? '&absorptionScore=' + encodeURIComponent(qlAbsorptionScore) : '';
  const url = API_LOG + '?key=' + encodeURIComponent(WRITE_KEY) + '&desc=' + encodeURIComponent(desc) + '&carbs=' + encodeURIComponent(carbs) + '&tags=' + encodeURIComponent(tags) + '&context=' + encodeURIComponent(context) + '&type=khd' + absorptionParam + (ts ? '&ts=' + encodeURIComponent(ts) : '');
  const result = await sendLog(url, status);
  await applyPickedLinks('ql', result && result.id);
  document.getElementById('qlDesc').innerHTML = '';
  document.getElementById('qlCarbs').value = '';
  document.getElementById('qlContext').value = '';
  qlAbsorptionScore = null;
  document.getElementById('qlAbsorptionRow').querySelectorAll('.dayBtn').forEach(b => b.classList.remove('dayBtnActive'));
}""",
    """async function quickLog(){
  const { clean: descRaw, tags: extractedTags } = getChipInputContent('qlDesc');
  const carbs = document.getElementById('qlCarbs').value.trim();
  const context = document.getElementById('qlContext').value.trim();
  const fat = document.getElementById('qlFat').value.trim();
  const protein = document.getElementById('qlProtein').value.trim();
  const calories = document.getElementById('qlCalories').value.trim();
  const ts = buildTs('ql', 'qlTimeOnly');
  const status = document.getElementById('qlStatus');
  if (!descRaw && !extractedTags.length){ status.textContent = 'Vul in wat je hebt gegeten.'; return; }
  const desc = descRaw || extractedTags.map(t => '@' + t).join(' ');

  const tags = extractedTags.join(',');

  const absorptionParam = qlAbsorptionScore != null ? '&absorptionScore=' + encodeURIComponent(qlAbsorptionScore) : '';
  const macroParams = (fat ? '&fat=' + encodeURIComponent(fat) : '') + (protein ? '&protein=' + encodeURIComponent(protein) : '') + (calories ? '&calories=' + encodeURIComponent(calories) : '');
  const url = API_LOG + '?key=' + encodeURIComponent(WRITE_KEY) + '&desc=' + encodeURIComponent(desc) + '&carbs=' + encodeURIComponent(carbs) + '&tags=' + encodeURIComponent(tags) + '&context=' + encodeURIComponent(context) + '&type=khd' + absorptionParam + macroParams + (ts ? '&ts=' + encodeURIComponent(ts) : '');
  const result = await sendLog(url, status);
  await applyPickedLinks('ql', result && result.id);
  document.getElementById('qlDesc').innerHTML = '';
  document.getElementById('qlCarbs').value = '';
  document.getElementById('qlContext').value = '';
  document.getElementById('qlFat').value = '';
  document.getElementById('qlProtein').value = '';
  document.getElementById('qlCalories').value = '';
  qlAbsorptionScore = null;
  document.getElementById('qlAbsorptionRow').querySelectorAll('.dayBtn').forEach(b => b.classList.remove('dayBtnActive'));
}""",
    "JS: quickLog() macro-velden")

fe = apply(fe,
    """      (row.type === 'khd' ?
        '<div style="font-size:11px; font-weight:600; color:#8a8a86; text-transform:uppercase; letter-spacing:0.5px; margin-top:4px;">Verwerking</div>' +
        '<div class="pillRow" id="rdmAbsorptionRow" style="display:flex; gap:6px; flex-wrap:wrap;">' +
          ABSORPTION_TITLES.map((t, i) => '<button type="button" class="dayBtn' + (row.absorptionScore === i ? ' dayBtnActive' : '') + '" data-score="' + i + '" title="' + t + '" onclick="selectRdmAbsorptionScore(' + i + ',this)">' + ABSORPTION_EMOJI[i] + '</button>').join('') +
        '</div>'
      : '') +""",
    """      (row.type === 'khd' ?
        '<div style="font-size:11px; font-weight:600; color:#8a8a86; text-transform:uppercase; letter-spacing:0.5px; margin-top:4px;">Verwerking</div>' +
        '<div class="pillRow" id="rdmAbsorptionRow" style="display:flex; gap:6px; flex-wrap:wrap;">' +
          ABSORPTION_TITLES.map((t, i) => '<button type="button" class="dayBtn' + (row.absorptionScore === i ? ' dayBtnActive' : '') + '" data-score="' + i + '" title="' + t + '" onclick="selectRdmAbsorptionScore(' + i + ',this)">' + ABSORPTION_EMOJI[i] + '</button>').join('') +
        '</div>' +
        '<div style="font-size:11px; font-weight:600; color:#8a8a86; text-transform:uppercase; letter-spacing:0.5px; margin-top:4px;">Macro\\'s (optioneel, overschrijft verwerking-schaal)</div>' +
        '<div style="display:flex; gap:6px; flex-wrap:wrap;">' +
          '<input id="rdmFat" type="number" step="0.1" value="' + (row.fatG != null ? row.fatG : '') + '" placeholder="vet (g)" style="flex:1; min-width:80px; ' + fieldStyle + '">' +
          '<input id="rdmProtein" type="number" step="0.1" value="' + (row.proteinG != null ? row.proteinG : '') + '" placeholder="eiwit (g)" style="flex:1; min-width:80px; ' + fieldStyle + '">' +
          '<input id="rdmCalories" type="number" step="1" value="' + (row.calories != null ? row.calories : '') + '" placeholder="kcal (optioneel)" style="flex:1; min-width:90px; ' + fieldStyle + '">' +
        '</div>'
      : '') +""",
    "HTML: macro-velden edit-modal")

fe = apply(fe,
    """async function saveRdModal(id){
  const { clean: descRaw, tags: extractedTags } = getChipInputContent('rdmDesc');
  const desc = descRaw || extractedTags.map(t => '@' + t).join(' ');
  const amount = document.getElementById('rdmAmount').value;
  const tags = extractedTags.join(',');
  const context = document.getElementById('rdmContext').value;
  const ts = document.getElementById('rdmTs').value;
  const type = document.getElementById('rdmType').value;
  const bolusTypeEl = document.getElementById('rdmBolusType');
  const bolusType = bolusTypeEl ? bolusTypeEl.value : '';
  const absorptionParam = type === 'khd' ? '&absorptionScore=' + encodeURIComponent(rdmAbsorptionScore != null ? rdmAbsorptionScore : '') : '';

  try {
    const res = await fetch(API_UPDATE + '?key=' + encodeURIComponent(WRITE_KEY) + '&id=' + encodeURIComponent(id) +
      '&desc=' + encodeURIComponent(desc) + '&amount=' + encodeURIComponent(amount) +
      '&tags=' + encodeURIComponent(tags) + '&context=' + encodeURIComponent(context) +
      '&ts=' + encodeURIComponent(ts) + '&type=' + encodeURIComponent(type) +
      '&bolusType=' + encodeURIComponent(bolusType) + absorptionParam);
    const json = await res.json();
    if (json.status !== 'ok') { alert('Mislukt: ' + (json.message || 'onbekende fout')); return; }

""",
    """async function saveRdModal(id){
  const { clean: descRaw, tags: extractedTags } = getChipInputContent('rdmDesc');
  const desc = descRaw || extractedTags.map(t => '@' + t).join(' ');
  const amount = document.getElementById('rdmAmount').value;
  const tags = extractedTags.join(',');
  const context = document.getElementById('rdmContext').value;
  const ts = document.getElementById('rdmTs').value;
  const type = document.getElementById('rdmType').value;
  const bolusTypeEl = document.getElementById('rdmBolusType');
  const bolusType = bolusTypeEl ? bolusTypeEl.value : '';
  const absorptionParam = type === 'khd' ? '&absorptionScore=' + encodeURIComponent(rdmAbsorptionScore != null ? rdmAbsorptionScore : '') : '';
  const fatEl = document.getElementById('rdmFat');
  const proteinEl = document.getElementById('rdmProtein');
  const caloriesEl = document.getElementById('rdmCalories');
  const macroParams = type === 'khd'
    ? '&fat=' + encodeURIComponent(fatEl ? fatEl.value : '') + '&protein=' + encodeURIComponent(proteinEl ? proteinEl.value : '') + '&calories=' + encodeURIComponent(caloriesEl ? caloriesEl.value : '')
    : '';

  try {
    const res = await fetch(API_UPDATE + '?key=' + encodeURIComponent(WRITE_KEY) + '&id=' + encodeURIComponent(id) +
      '&desc=' + encodeURIComponent(desc) + '&amount=' + encodeURIComponent(amount) +
      '&tags=' + encodeURIComponent(tags) + '&context=' + encodeURIComponent(context) +
      '&ts=' + encodeURIComponent(ts) + '&type=' + encodeURIComponent(type) +
      '&bolusType=' + encodeURIComponent(bolusType) + absorptionParam + macroParams);
    const json = await res.json();
    if (json.status !== 'ok') { alert('Mislukt: ' + (json.message || 'onbekende fout')); return; }

""",
    "JS: saveRdModal() macro-velden")

fe = apply(fe,
    """// ---- COB: Hill/log-logistic absorptiemodel ----
// tau = absorptie-midpoint (min), n = steilheid. Per bestaande absorption_score (0-5).
// Waarden gebaseerd op literatuur (glycemic index / vetrijke-maaltijd onderzoek), afgestemd
// op de bestaande 6 categorieen in de KHD-tab (Bliksemsnel t/m Zeer traag).
const ABSORPTION_PARAMS = {
  0: { tau: 20,  n: 5   }, // Bliksemsnel (~45 min)
  1: { tau: 60,  n: 3.5 }, // Snel (~1.5-2u)
  2: { tau: 105, n: 2.5 }, // Normaal (~2.5-3u)
  3: { tau: 150, n: 2   }, // Standaard maaltijd (~3.5-4u)
  4: { tau: 270, n: 1.2 }, // Vetrijk/traag (~5-6u)
  5: { tau: 420, n: 0.8 }  // Zeer traag (~7-8u)
};
const COB_WINDOW_MIN = 600; // veiligheidsgrens, ruim boven score 5

// Fractie koolhydraten die nog NIET is opgenomen (dus nog "on board") op tMin minuten na eten.
function cobFraction(tMin, score){
  const p = ABSORPTION_PARAMS[score];
  if (!p || tMin <= 0) return 1;
  if (tMin >= COB_WINDOW_MIN) return 0;
  const ratio = Math.pow(tMin / p.tau, p.n);
  return 1 / (1 + ratio);
}

function totalCobAt(targetTime, carbEntries){
  let total = 0;
  carbEntries.forEach(c => {
    if (c.amount == null || c.absorptionScore == null) return;
    const minsSince = (targetTime - new Date(c.ts).getTime()) / 60000;
    if (minsSince >= 0 && minsSince < COB_WINDOW_MIN) total += c.amount * cobFraction(minsSince, c.absorptionScore);
  });
  return total;
}

// KHD-absorptie = hoe snel COB op dit moment daalt (numerieke afgeleide, zelfde onderliggende curve)
function khdAbsorptionFraction(tMin, score){
  if (tMin < 0 || tMin > COB_WINDOW_MIN) return 0;
  const d = 1; // 1 minuut-stap voor de afgeleide
  return Math.max(0, (cobFraction(Math.max(0, tMin - d/2), score) - cobFraction(Math.min(COB_WINDOW_MIN, tMin + d/2), score)) / d);
}

function totalKhdAbsorptionAt(targetTime, carbEntries){
  let total = 0;
  carbEntries.forEach(c => {
    if (c.amount == null || c.absorptionScore == null) return;
    const minsSince = (targetTime - new Date(c.ts).getTime()) / 60000;
    if (minsSince >= 0 && minsSince < COB_WINDOW_MIN) total += c.amount * khdAbsorptionFraction(minsSince, c.absorptionScore);
  });
  return total;
}""",
    """// ---- COB: Hill/log-logistic absorptiemodel ----
// tau = absorptie-midpoint (min), n = steilheid. Per bestaande absorption_score (0-5).
// Waarden gebaseerd op literatuur (glycemic index / vetrijke-maaltijd onderzoek), afgestemd
// op de bestaande 6 categorieen in de KHD-tab (Bliksemsnel t/m Zeer traag).
const ABSORPTION_PARAMS = {
  0: { tau: 20,  n: 5   }, // Bliksemsnel (~45 min)
  1: { tau: 60,  n: 3.5 }, // Snel (~1.5-2u)
  2: { tau: 105, n: 2.5 }, // Normaal (~2.5-3u)
  3: { tau: 150, n: 2   }, // Standaard maaltijd (~3.5-4u)
  4: { tau: 270, n: 1.2 }, // Vetrijk/traag (~5-6u)
  5: { tau: 420, n: 0.8 }  // Zeer traag (~7-8u)
};
const COB_WINDOW_MIN = 600; // veiligheidsgrens, ruim boven score 5

// ---- FPU (Fat-Protein Units, Warsaw-methode) ----
// FPU = (vet_g * 9 + eiwit_g * 4) / 100. Baseline bij FPU=0 geankerd op categorie "Snel"
// (pure koolhydraten zijn niet instant). Voorlopige kalibratie op 1 datapunt (AH pizza
// tonno, aug 2026) - bijstellen zodra een schone meting (zonder correctiebolus) beschikbaar is.
const FPU_TAU0 = 60;
const FPU_N0 = 3.5;
const FPU_K_TAU = 49;
const FPU_K_N = 0.53;

// Bepaalt welke tau/n gebruikt wordt voor een KHD-entry, volgens vaste prioriteit:
// 1) macro's (vet+eiwit) aanwezig -> FPU-formule (meest realistisch)
// 2) geen macro's, wel verwerkingsschaal (0-5) -> vaste categorie
// 3) geen van beide -> null (telt niet mee in COB/absorptiecurve)
function getEffectiveTauN(entry){
  if (entry.fatG != null && entry.proteinG != null) {
    const fpu = (entry.fatG * 9 + entry.proteinG * 4) / 100;
    return { tau: FPU_TAU0 + FPU_K_TAU * fpu, n: FPU_N0 / (1 + FPU_K_N * fpu) };
  }
  if (entry.absorptionScore != null) return ABSORPTION_PARAMS[entry.absorptionScore] || null;
  return null;
}

// Fractie koolhydraten die nog NIET is opgenomen (dus nog "on board") op tMin minuten na eten.
function cobFractionParams(tMin, params){
  if (!params || tMin <= 0) return 1;
  if (tMin >= COB_WINDOW_MIN) return 0;
  const ratio = Math.pow(tMin / params.tau, params.n);
  return 1 / (1 + ratio);
}

function totalCobAt(targetTime, carbEntries){
  let total = 0;
  carbEntries.forEach(c => {
    if (c.amount == null) return;
    const params = getEffectiveTauN(c);
    if (!params) return;
    const minsSince = (targetTime - new Date(c.ts).getTime()) / 60000;
    if (minsSince >= 0 && minsSince < COB_WINDOW_MIN) total += c.amount * cobFractionParams(minsSince, params);
  });
  return total;
}

// KHD-absorptie = hoe snel COB op dit moment daalt (numerieke afgeleide, zelfde onderliggende curve)
function khdAbsorptionFractionParams(tMin, params){
  if (tMin < 0 || tMin > COB_WINDOW_MIN) return 0;
  const d = 1; // 1 minuut-stap voor de afgeleide
  return Math.max(0, (cobFractionParams(Math.max(0, tMin - d/2), params) - cobFractionParams(Math.min(COB_WINDOW_MIN, tMin + d/2), params)) / d);
}

function totalKhdAbsorptionAt(targetTime, carbEntries){
  let total = 0;
  carbEntries.forEach(c => {
    if (c.amount == null) return;
    const params = getEffectiveTauN(c);
    if (!params) return;
    const minsSince = (targetTime - new Date(c.ts).getTime()) / 60000;
    if (minsSince >= 0 && minsSince < COB_WINDOW_MIN) total += c.amount * khdAbsorptionFractionParams(minsSince, params);
  });
  return total;
}""",
    "JS: forecast-engine FPU-formule + prioriteitslogica")

fe = apply(fe,
    """  const carbEntries = (DATA.foodLogRaw || []).filter(r => r.type === 'khd' && r.amount != null && r.absorptionScore != null);""",
    """  const carbEntries = (DATA.foodLogRaw || []).filter(r => r.type === 'khd' && r.amount != null && (r.absorptionScore != null || (r.fatG != null && r.proteinG != null)));""",
    "JS: carbEntries-filter macro-only toestaan")

FE.write_text(fe)

# ============ BACKEND: src/index.js ============
BE = pathlib.Path("src/index.js")
be = BE.read_text()

be = apply(be,
    '"SELECT id, timestamp, description, tags, amount, context, type, source, bolus_type, absorption_score FROM food_log" +',
    '"SELECT id, timestamp, description, tags, amount, context, type, source, bolus_type, absorption_score, fat_g, protein_g, calories FROM food_log" +',
    "Backend: SELECT macro-kolommen")

be = apply(be,
    """      bolusType: r.bolus_type || '',
      absorptionScore: r.absorption_score != null ? r.absorption_score : null,""",
    """      bolusType: r.bolus_type || '',
      absorptionScore: r.absorption_score != null ? r.absorption_score : null,
      fatG: r.fat_g != null ? r.fat_g : null,
      proteinG: r.protein_g != null ? r.protein_g : null,
      calories: r.calories != null ? r.calories : null,""",
    "Backend: foodLogRaw mapping macro's")

be = apply(be,
    """  const absorptionScore = (type === 'khd' && params.get('absorptionScore') !== null && params.get('absorptionScore') !== '')
    ? Number(params.get('absorptionScore')) : null;

  const result = await env.DB.prepare(
    'INSERT INTO food_log (timestamp, description, tags, amount, context, type, source, bolus_type, absorption_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(tsText, desc, tags, amount, context, type, source, bolusType, absorptionScore).run();""",
    """  const absorptionScore = (type === 'khd' && params.get('absorptionScore') !== null && params.get('absorptionScore') !== '')
    ? Number(params.get('absorptionScore')) : null;
  const fatG = (type === 'khd' && params.get('fat') !== null && params.get('fat') !== '')
    ? Number(params.get('fat')) : null;
  const proteinG = (type === 'khd' && params.get('protein') !== null && params.get('protein') !== '')
    ? Number(params.get('protein')) : null;
  const calories = (type === 'khd' && params.get('calories') !== null && params.get('calories') !== '')
    ? Number(params.get('calories')) : null;

  const result = await env.DB.prepare(
    'INSERT INTO food_log (timestamp, description, tags, amount, context, type, source, bolus_type, absorption_score, fat_g, protein_g, calories) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(tsText, desc, tags, amount, context, type, source, bolusType, absorptionScore, fatG, proteinG, calories).run();""",
    "Backend: handleLog macro's")

be = apply(be,
    """  const existing = await env.DB.prepare(
    'SELECT description, tags, amount, context, timestamp, type, bolus_type, absorption_score FROM food_log WHERE id = ?'
  ).bind(id).first();
  if (!existing) {
    return jsonOut({ status: 'error', message: 'Niets gevonden om bij te werken.' });
  }

  const desc = params.has('desc') ? (params.get('desc') || '') : existing.description;
  const tags = params.has('tags') ? (params.get('tags') || '') : existing.tags;
  const amount = params.has('amount')
    ? (params.get('amount') !== '' ? Number(params.get('amount')) : null)
    : existing.amount;
  const context = params.has('context') ? (params.get('context') || '') : existing.context;
  const type = params.has('type') && params.get('type') ? params.get('type') : existing.type;
  const bolusType = params.has('bolusType') ? (params.get('bolusType') || '') : (existing.bolus_type || '');
  const absorptionScore = params.has('absorptionScore')
    ? (params.get('absorptionScore') !== '' ? Number(params.get('absorptionScore')) : null)
    : (existing.absorption_score != null ? existing.absorption_score : null);
  const tsParam = params.get('ts');
  const tsText = tsParam ? tsParam.replace('T', ' ') + ':00' : existing.timestamp;

  const result = await env.DB.prepare(
    'UPDATE food_log SET description = ?, tags = ?, amount = ?, context = ?, timestamp = ?, type = ?, bolus_type = ?, absorption_score = ? WHERE id = ?'
  ).bind(desc, tags, amount, context, tsText, type, bolusType, absorptionScore, id).run();""",
    """  const existing = await env.DB.prepare(
    'SELECT description, tags, amount, context, timestamp, type, bolus_type, absorption_score, fat_g, protein_g, calories FROM food_log WHERE id = ?'
  ).bind(id).first();
  if (!existing) {
    return jsonOut({ status: 'error', message: 'Niets gevonden om bij te werken.' });
  }

  const desc = params.has('desc') ? (params.get('desc') || '') : existing.description;
  const tags = params.has('tags') ? (params.get('tags') || '') : existing.tags;
  const amount = params.has('amount')
    ? (params.get('amount') !== '' ? Number(params.get('amount')) : null)
    : existing.amount;
  const context = params.has('context') ? (params.get('context') || '') : existing.context;
  const type = params.has('type') && params.get('type') ? params.get('type') : existing.type;
  const bolusType = params.has('bolusType') ? (params.get('bolusType') || '') : (existing.bolus_type || '');
  const absorptionScore = params.has('absorptionScore')
    ? (params.get('absorptionScore') !== '' ? Number(params.get('absorptionScore')) : null)
    : (existing.absorption_score != null ? existing.absorption_score : null);
  const fatG = params.has('fat')
    ? (params.get('fat') !== '' ? Number(params.get('fat')) : null)
    : (existing.fat_g != null ? existing.fat_g : null);
  const proteinG = params.has('protein')
    ? (params.get('protein') !== '' ? Number(params.get('protein')) : null)
    : (existing.protein_g != null ? existing.protein_g : null);
  const calories = params.has('calories')
    ? (params.get('calories') !== '' ? Number(params.get('calories')) : null)
    : (existing.calories != null ? existing.calories : null);
  const tsParam = params.get('ts');
  const tsText = tsParam ? tsParam.replace('T', ' ') + ':00' : existing.timestamp;

  const result = await env.DB.prepare(
    'UPDATE food_log SET description = ?, tags = ?, amount = ?, context = ?, timestamp = ?, type = ?, bolus_type = ?, absorption_score = ?, fat_g = ?, protein_g = ?, calories = ? WHERE id = ?'
  ).bind(desc, tags, amount, context, tsText, type, bolusType, absorptionScore, fatG, proteinG, calories, id).run();""",
    "Backend: handleUpdate macro's")

BE.write_text(be)
print("\nAlle patches toegepast (frontend + backend).")
