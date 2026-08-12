#!/usr/bin/env python3
"""
Patch: KHD-absorptierate-lijn + combined chart update
(checkbox-volgorde, tijdvenster-toggle ±3u/±6u/±9u).
Draai dit vanuit ~/Desktop/Glucose-dashboard.
"""
import pathlib

PATH = pathlib.Path("public/index.html")
src = PATH.read_text()

def apply(old, new, label):
    global src
    count = src.count(old)
    assert count == 1, f"[{label}] anchor gevonden {count}x, verwacht 1x"
    src = src.replace(old, new)
    print(f"OK: {label}")

# --- HTML: checkboxes herordenen + KHD-absorptie checkbox + tijdvenster-toggle ---
apply(
    """        <div style="display:flex; gap:10px; margin-top:4px;">
          <label style="display:flex; align-items:center; gap:4px; font-size:11px; color:#b7b7b2; cursor:pointer;"><input type="checkbox" id="combChkIob" checked onchange="renderCombinedChart()"> IOB</label>
          <label style="display:flex; align-items:center; gap:4px; font-size:11px; color:#b7b7b2; cursor:pointer;"><input type="checkbox" id="combChkAct" onchange="renderCombinedChart()"> Activiteit</label>
          <label style="display:flex; align-items:center; gap:4px; font-size:11px; color:#b7b7b2; cursor:pointer;"><input type="checkbox" id="combChkCob" checked onchange="renderCombinedChart()"> COB</label>
        </div>
        <div style="flex:1; overflow:hidden; margin-top:2px;"><canvas id="combinedChart"></canvas></div>
      </div>
      </div>
      </div>
""",
    """        <div style="display:flex; gap:10px; margin-top:4px; flex-wrap:wrap;">
          <label style="display:flex; align-items:center; gap:4px; font-size:11px; color:#b7b7b2; cursor:pointer;"><input type="checkbox" id="combChkIob" onchange="renderCombinedChart()"> IOB</label>
          <label style="display:flex; align-items:center; gap:4px; font-size:11px; color:#b7b7b2; cursor:pointer;"><input type="checkbox" id="combChkCob" onchange="renderCombinedChart()"> COB</label>
          <label style="display:flex; align-items:center; gap:4px; font-size:11px; color:#b7b7b2; cursor:pointer;"><input type="checkbox" id="combChkAct" checked onchange="renderCombinedChart()"> Insuline-activiteit</label>
          <label style="display:flex; align-items:center; gap:4px; font-size:11px; color:#b7b7b2; cursor:pointer;"><input type="checkbox" id="combChkKhdAbs" checked onchange="renderCombinedChart()"> KHD-absorptie</label>
        </div>
        <div id="combWindowToggle" style="display:flex; gap:4px; margin-top:6px;"></div>
        <div style="flex:1; overflow:hidden; margin-top:2px;"><canvas id="combinedChart"></canvas></div>
      </div>
      </div>
      </div>
""",
    "HTML: checkboxes herordenen + KHD-absorptie + window-toggle container",
)

# --- JS: KHD-absorptierate functies (afgeleide van COB) ---
apply(
    """function totalCobAt(targetTime, carbEntries){
  let total = 0;
  carbEntries.forEach(c => {
    if (c.amount == null || c.absorptionScore == null) return;
    const minsSince = (targetTime - new Date(c.ts).getTime()) / 60000;
    if (minsSince >= 0 && minsSince < COB_WINDOW_MIN) total += c.amount * cobFraction(minsSince, c.absorptionScore);
  });
  return total;
}""",
    """function totalCobAt(targetTime, carbEntries){
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
    "KHD-absorptierate functies toevoegen",
)

# --- JS: IOB_WINDOW_MIN mutable maken, default ±6u ---
apply(
    "const IOB_WINDOW_MIN = 300; // ±5 uur",
    "let IOB_WINDOW_MIN = 360; // default ±6 uur, aanpasbaar via combWindowToggle",
    "IOB_WINDOW_MIN mutable + default ±6u",
)

# --- JS: tijdvenster-toggle state en render-functie ---
apply(
    "const IOB_POINTS_PER_HOUR = 60 / IOB_STEP_MIN;",
    """const IOB_POINTS_PER_HOUR = 60 / IOB_STEP_MIN;

function setCombinedWindow(minutes){
  IOB_WINDOW_MIN = minutes;
  renderCombinedChart();
}

function renderCombinedWindowToggle(){
  const el = document.getElementById('combWindowToggle');
  if (!el) return;
  const options = [[180,'\u00b13u'],[360,'\u00b16u'],[540,'\u00b19u']];
  el.innerHTML = options.map(([min, label]) =>
    '<button type="button" onclick="setCombinedWindow(' + min + ')" style="font-size:10px; padding:2px 8px; border-radius:6px; border:0.5px solid rgba(255,255,255,0.14); cursor:pointer; background:' +
    (IOB_WINDOW_MIN === min ? 'rgba(127,119,221,0.35); color:#e4e4e0;' : 'transparent; color:#8a8a86;') + '">' + label + '</button>'
  ).join('');
}""",
    "Tijdvenster-toggle state + render-functie",
)

# --- JS: renderCombinedChart uitbreiden met KHD-absorptie + juiste volgorde ---
apply(
    """  const stepMin = IOB_STEP_MIN;
  const points = [];
  for (let offset = -IOB_WINDOW_MIN; offset <= IOB_WINDOW_MIN; offset += stepMin) {
    const ts = now + offset * 60000;
    points.push({
      offset, ts,
      iob: totalIobAt(ts, boluses),
      act: totalActivityAt(ts, boluses),
      cob: totalCobAt(ts, carbEntries)
    });
  }
  const centerIdx = points.findIndex(p => p.offset === 0);
  const iobVals = points.map(p => p.iob);
  const actVals = points.map(p => p.act);
  const cobVals = points.map(p => p.cob);

  document.getElementById('iobNowVal').textContent = (iobVals[centerIdx] || 0).toFixed(1) + 'E';
  document.getElementById('cobNowVal').textContent = (cobVals[centerIdx] || 0).toFixed(0) + 'g';

  const norm = arr => { const m = Math.max(...arr, 0.0001); return arr.map(v => v / m * 100); };
  const labels = points.map(p => fmtTime(p.ts));
  const bolusMarkerObj = bolusMarkerData(now, boluses, stepMin, points.length, IOB_WINDOW_MIN);

  const showIob = document.getElementById('combChkIob').checked;
  const showAct = document.getElementById('combChkAct').checked;
  const showCob = document.getElementById('combChkCob').checked;

  const datasets = [];
  if (showIob) datasets.push({ label:'IOB', data: norm(iobVals), borderColor:'#7f77dd', backgroundColor:'transparent', borderWidth:1.5, pointRadius:0, tension:0.35, pointHitRadius:8 });
  if (showAct) datasets.push({ label:'Activiteit', data: norm(actVals), borderColor:'#a89af0', backgroundColor:'transparent', borderWidth:1.5, pointRadius:0, tension:0.35, pointHitRadius:8, borderDash:[4,3] });
  if (showCob) datasets.push({ label:'COB', data: norm(cobVals), borderColor:'#d85a30', backgroundColor:'transparent', borderWidth:1.5, pointRadius:0, tension:0.35, pointHitRadius:8 });
  datasets.push({ data: bolusMarkerObj.data, descs: bolusMarkerObj.descs, showLine:false, pointStyle:'triangle', pointRadius:6, pointBackgroundColor:'#7f77dd', pointBorderColor:'#fff', pointBorderWidth:1 });
""",
    """  const stepMin = IOB_STEP_MIN;
  const points = [];
  for (let offset = -IOB_WINDOW_MIN; offset <= IOB_WINDOW_MIN; offset += stepMin) {
    const ts = now + offset * 60000;
    points.push({
      offset, ts,
      iob: totalIobAt(ts, boluses),
      act: totalActivityAt(ts, boluses),
      cob: totalCobAt(ts, carbEntries),
      khdAbs: totalKhdAbsorptionAt(ts, carbEntries)
    });
  }
  const centerIdx = points.findIndex(p => p.offset === 0);
  const iobVals = points.map(p => p.iob);
  const actVals = points.map(p => p.act);
  const cobVals = points.map(p => p.cob);
  const khdAbsVals = points.map(p => p.khdAbs);

  document.getElementById('iobNowVal').textContent = (iobVals[centerIdx] || 0).toFixed(1) + 'E';
  document.getElementById('cobNowVal').textContent = (cobVals[centerIdx] || 0).toFixed(0) + 'g';

  const norm = arr => { const m = Math.max(...arr, 0.0001); return arr.map(v => v / m * 100); };
  const labels = points.map(p => fmtTime(p.ts));
  const bolusMarkerObj = bolusMarkerData(now, boluses, stepMin, points.length, IOB_WINDOW_MIN);

  const showIob = document.getElementById('combChkIob').checked;
  const showCob = document.getElementById('combChkCob').checked;
  const showAct = document.getElementById('combChkAct').checked;
  const showKhdAbs = document.getElementById('combChkKhdAbs').checked;

  const datasets = [];
  if (showIob) datasets.push({ label:'IOB', data: norm(iobVals), borderColor:'#7f77dd', backgroundColor:'transparent', borderWidth:1.5, pointRadius:0, tension:0.35, pointHitRadius:8 });
  if (showCob) datasets.push({ label:'COB', data: norm(cobVals), borderColor:'#d85a30', backgroundColor:'transparent', borderWidth:1.5, pointRadius:0, tension:0.35, pointHitRadius:8 });
  if (showAct) datasets.push({ label:'Insuline-activiteit', data: norm(actVals), borderColor:'#a89af0', backgroundColor:'transparent', borderWidth:1.5, pointRadius:0, tension:0.35, pointHitRadius:8, borderDash:[4,3] });
  if (showKhdAbs) datasets.push({ label:'KHD-absorptie', data: norm(khdAbsVals), borderColor:'#f0a85a', backgroundColor:'transparent', borderWidth:1.5, pointRadius:0, tension:0.35, pointHitRadius:8, borderDash:[4,3] });
  datasets.push({ data: bolusMarkerObj.data, descs: bolusMarkerObj.descs, showLine:false, pointStyle:'triangle', pointRadius:6, pointBackgroundColor:'#7f77dd', pointBorderColor:'#fff', pointBorderWidth:1 });

  renderCombinedWindowToggle();
""",
    "renderCombinedChart: KHD-absorptie + volgorde + window-toggle render",
)

PATH.write_text(src)
print("\nAlle 5 patches toegepast.")
