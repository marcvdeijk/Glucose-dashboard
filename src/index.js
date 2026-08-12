// ---- Helpers ----

function jsonOut(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json' }
  });
}

function fmtTimestamp(date) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Amsterdam',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false
  }).formatToParts(date);
  const get = t => parts.find(p => p.type === t).value;
  return `${get('year')}-${get('month')}-${get('day')} ${get('hour')}:${get('minute')}:${get('second')}`;
}

async function getState(env, key) {
  const row = await env.DB.prepare('SELECT value FROM kv_state WHERE key = ?').bind(key).first();
  return row ? row.value : null;
}

async function setState(env, key, value) {
  await env.DB.prepare('INSERT INTO kv_state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value')
    .bind(key, value).run();
}

// ---- /api/data: lezen ----

function nearestGlucose(glucose, tsText) {
  if (!glucose.length) return null;
  const target = new Date(tsText).getTime();
  let best = null, bestDiff = Infinity;
  for (const g of glucose) {
    const diff = Math.abs(new Date(g.ts).getTime() - target);
    if (diff < bestDiff) { bestDiff = diff; best = g.glucose; }
  }
  return best;
}

async function getData(env, days) {
  const cutoff = days ? fmtTimestamp(new Date(Date.now() - Number(days) * 24 * 3600000)) : null;

  const glucoseRows = await env.DB.prepare(
    "SELECT timestamp, glucose FROM nightscout_data WHERE type = 'glucose'" +
    (cutoff ? " AND timestamp >= ?" : "") + " ORDER BY timestamp"
  ).bind(...(cutoff ? [cutoff] : [])).all();
  const glucose = glucoseRows.results.map(r => ({ ts: r.timestamp.replace(' ', 'T'), glucose: r.glucose }));

  const treatmentRows = await env.DB.prepare(
    "SELECT timestamp, bolus FROM nightscout_data WHERE type = 'treatment' AND bolus > 0" +
    (cutoff ? " AND timestamp >= ?" : "") + " ORDER BY timestamp"
  ).bind(...(cutoff ? [cutoff] : [])).all();
  const treatments = treatmentRows.results.map(r => ({ ts: r.timestamp.replace(' ', 'T'), bolus: r.bolus }));

  const logRows = await env.DB.prepare(
    "SELECT id, timestamp, description, tags, amount, context, type, source, bolus_type, absorption_score, fat_g, protein_g, calories FROM food_log" +
    (cutoff ? " WHERE timestamp >= ?" : "") + " ORDER BY timestamp"
  ).bind(...(cutoff ? [cutoff] : [])).all();

  const linkRows = await env.DB.prepare("SELECT entry_a_id, entry_b_id FROM entry_links").all();
  const linkMap = {};
  linkRows.results.forEach(l => {
    (linkMap[l.entry_a_id] = linkMap[l.entry_a_id] || []).push(l.entry_b_id);
    (linkMap[l.entry_b_id] = linkMap[l.entry_b_id] || []).push(l.entry_a_id);
  });
  const byId = {};
  logRows.results.forEach(r => { byId[r.id] = r; });

  const foodLogRaw = logRows.results.map(r => {
    const linkedIds = [...new Set(linkMap[r.id] || [])];
    const links = linkedIds.map(lid => {
      const o = byId[lid];
      return o ? { id: o.id, desc: o.description, type: o.type || '', ts: o.timestamp.replace(' ', 'T') } : null;
    }).filter(Boolean);
    return {
      id: r.id, ts: r.timestamp.replace(' ', 'T'), desc: r.description, tags: r.tags, amount: r.amount,
      context: r.context, type: r.type || '', source: r.source || 'Marc',
      bolusType: r.bolus_type || '',
      absorptionScore: r.absorption_score != null ? r.absorption_score : null,
      fatG: r.fat_g != null ? r.fat_g : null,
      proteinG: r.protein_g != null ? r.protein_g : null,
      calories: r.calories != null ? r.calories : null,
      bgAtEntry: r.type === 'bolus' ? nearestGlucose(glucose, r.timestamp.replace(' ', 'T')) : null,
      links
    };
  });

  const meals = [];
  const exercises = [];
  logRows.results.forEach(r => {
    const desc = r.description || '';
    const type = r.type || '';
    if (desc.indexOf('[PLAN]') === 0) return;
    if (desc.indexOf('[BEWEGING]') === 0 || type === 'beweging') {
      exercises.push({ ts: r.timestamp.replace(' ', 'T'), desc: r.description, tags: r.tags, context: r.context, type });
    } else if (type === 'bolus') {
      const bolusVal = Number(r.amount) || 0;
      if (bolusVal > 0) {
        treatments.push({ ts: r.timestamp.replace(' ', 'T'), bolus: bolusVal });
      }
    } else {
      meals.push({ ts: r.timestamp.replace(' ', 'T'), desc: r.description, tags: r.tags, carbs: r.amount, context: r.context, type });
    }
  });

  treatments.sort((a, b) => a.ts < b.ts ? -1 : 1);

  const sensorRow = await env.DB.prepare(
    "SELECT timestamp FROM nightscout_data WHERE event_type = 'Sensor Start' ORDER BY timestamp DESC LIMIT 1"
  ).first();
  const sensorStart = sensorRow ? sensorRow.timestamp.replace(' ', 'T') : null;

  const tagCounts = {};
  logRows.results.forEach(r => {
    (r.tags || '').split(/[,;]/).map(t => t.trim().toLowerCase()).filter(Boolean).forEach(t => {
      tagCounts[t] = (tagCounts[t] || 0) + 1;
    });
  });
  const tagFrequency = Object.entries(tagCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([tag, count]) => ({ tag, count }));

  return { glucose, treatments, meals, exercises, foodLogRaw, sensorStart, tagFrequency };
}

async function handleData(env, params) {
  const days = params ? params.get('days') : null;
  return jsonOut(await getData(env, days));
}

// ---- /api/summary: samengevatte KPI's en patronen, klaar voor AI-analyse zonder ruwe data ----

function computeGlucoseStats(vals) {
  const n = vals.length;
  if (!n) return null;
  const sum = vals.reduce((s, v) => s + v, 0);
  const avg = sum / n;
  const variance = vals.reduce((s, v) => s + (v - avg) * (v - avg), 0) / n;
  const cv = avg > 0 ? Math.round(1000 * Math.sqrt(variance) / avg) / 10 : 0;
  const gmi = Math.round(10 * (3.31 + 0.02392 * avg * 18.0182)) / 10;
  const low = vals.filter(v => v < 3.9).length;
  const high = vals.filter(v => v > 10.0).length;
  const inRange = n - low - high;
  return {
    n,
    avg: Math.round(avg * 10) / 10,
    cv,
    gmi,
    tirPct: Math.round(1000 * inRange / n) / 10,
    tarPct: Math.round(1000 * high / n) / 10,
    tbrPct: Math.round(1000 * low / n) / 10
  };
}

function computePerDay(glucose) {
  const byDay = {};
  glucose.forEach(g => {
    const d = g.ts.slice(0, 10);
    (byDay[d] = byDay[d] || []).push(g.glucose);
  });
  return Object.keys(byDay).sort().map(d => {
    const vals = byDay[d];
    const stats = computeGlucoseStats(vals);
    return {
      date: d,
      n: vals.length,
      avg: stats.avg,
      min: Math.min(...vals),
      max: Math.max(...vals),
      tirPct: stats.tirPct,
      tarPct: stats.tarPct,
      tbrPct: stats.tbrPct
    };
  });
}

function computeHourlyPattern(glucose) {
  const byHour = {};
  glucose.forEach(g => {
    const h = new Date(g.ts).getHours();
    (byHour[h] = byHour[h] || []).push(g.glucose);
  });
  const result = [];
  for (let h = 0; h < 24; h++) {
    const vals = byHour[h] || [];
    result.push({
      hour: h,
      avg: vals.length ? Math.round((vals.reduce((s, v) => s + v, 0) / vals.length) * 10) / 10 : null,
      n: vals.length
    });
  }
  return result;
}

function findEpisodes(glucose, predicate) {
  const episodes = [];
  let current = null;
  glucose.forEach(g => {
    if (predicate(g.glucose)) {
      if (!current) current = { start: g.ts, end: g.ts, values: [g.glucose] };
      else { current.end = g.ts; current.values.push(g.glucose); }
    } else if (current) {
      episodes.push(current);
      current = null;
    }
  });
  if (current) episodes.push(current);
  return episodes.map(e => ({
    start: e.start,
    end: e.end,
    durationMin: Math.round((new Date(e.end) - new Date(e.start)) / 60000),
    minGlucose: Math.min(...e.values),
    maxGlucose: Math.max(...e.values),
    n: e.values.length
  }));
}

async function handleApiSummary(env, params) {
  if (!env.READ_KEY || params.get('key') !== env.READ_KEY) {
    return jsonOut({ status: 'error', message: 'Toegang geweigerd.' }, 403);
  }
  const days = Math.min(400, Math.max(1, Number(params.get('days')) || 7));
  const data = await getData(env, days);
  const glucose = data.glucose;

  if (!glucose.length) {
    return jsonOut({ status: 'ok', days, message: 'Geen glucosedata in deze periode.' });
  }

  const glucoseVals = glucose.map(g => g.glucose);
  const overall = computeGlucoseStats(glucoseVals);
  const perDay = computePerDay(glucose);
  const hourlyPattern = computeHourlyPattern(glucose);
  const hypoEpisodes = findEpisodes(glucose, v => v < 3.9);
  const severeHyperEpisodes = findEpisodes(glucose, v => v > 13.9);

  const bolusesInPeriod = data.foodLogRaw.filter(r => r.type === 'bolus' && r.amount > 0);
  const totalBolusUnits = bolusesInPeriod.reduce((s, r) => s + r.amount, 0);

  const sortedLog = data.foodLogRaw.slice().sort((a, b) => new Date(b.ts) - new Date(a.ts));
  const lastBolus = sortedLog.find(r => r.type === 'bolus') || null;
  const lastMeal = sortedLog.find(r => r.type === 'khd') || null;
  const lastExercise = sortedLog.find(r => r.type === 'beweging') || null;

  return jsonOut({
    status: 'ok',
    period: { days, from: glucose[0].ts, to: glucose[glucose.length - 1].ts },
    overall,
    perDay,
    hourlyPattern,
    hypoEpisodes,
    severeHyperEpisodes,
    treatments: {
      totalBolusUnits,
      bolusCount: bolusesInPeriod.length,
      avgUnitsPerDay: Math.round((totalBolusUnits / days) * 10) / 10
    },
    lastBolus,
    lastMeal,
    lastExercise
  });
}

// ---- /api/log: schrijven ----

async function handleLog(env, params) {
  const ts = params.get('ts');
  const tsText = ts ? ts.replace('T', ' ') + ':00' : fmtTimestamp(new Date());

  const desc = params.get('desc') || '';
  const tags = params.get('tags') || '';
  const amount = params.get('carbs') !== null && params.get('carbs') !== '' ? Number(params.get('carbs')) : null;
  const context = params.get('context') || '';
  const type = params.get('type') || 'khd';
  const source = params.get('source') || 'Marc';
  const bolusType = type === 'bolus' ? (params.get('bolusType') || '') : '';
  const absorptionScore = (type === 'khd' && params.get('absorptionScore') !== null && params.get('absorptionScore') !== '')
    ? Number(params.get('absorptionScore')) : null;
  const fatG = (type === 'khd' && params.get('fat') !== null && params.get('fat') !== '')
    ? Number(params.get('fat')) : null;
  const proteinG = (type === 'khd' && params.get('protein') !== null && params.get('protein') !== '')
    ? Number(params.get('protein')) : null;
  const calories = (type === 'khd' && params.get('calories') !== null && params.get('calories') !== '')
    ? Number(params.get('calories')) : null;

  const result = await env.DB.prepare(
    'INSERT INTO food_log (timestamp, description, tags, amount, context, type, source, bolus_type, absorption_score, fat_g, protein_g, calories) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(tsText, desc, tags, amount, context, type, source, bolusType, absorptionScore, fatG, proteinG, calories).run();

  const newId = result.meta && result.meta.last_row_id;
  return jsonOut({ status: 'ok', message: 'Gelogd: ' + tsText + ' - ' + desc, ts: tsText, id: newId });
}

// ---- /api/update: een eigen log-entry bewerken ----

async function handleUpdate(env, params) {
  const id = params.get('id');
  if (!id) {
    return jsonOut({ status: 'error', message: 'Geen id opgegeven.' });
  }

  const existing = await env.DB.prepare(
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
  ).bind(desc, tags, amount, context, tsText, type, bolusType, absorptionScore, fatG, proteinG, calories, id).run();

  if (!result.meta || result.meta.changes === 0) {
    return jsonOut({ status: 'error', message: 'Niets gevonden om bij te werken.' });
  }
  return jsonOut({ status: 'ok', message: 'Bijgewerkt.', id });
}

// ---- /api/delete: een eigen log-entry verwijderen ----

async function handleDelete(env, params) {
  const id = params.get('id');
  if (!id) {
    return jsonOut({ status: 'error', message: 'Geen id opgegeven.' });
  }
  const result = await env.DB.prepare('DELETE FROM food_log WHERE id = ?').bind(id).run();
  if (!result.meta || result.meta.changes === 0) {
    return jsonOut({ status: 'error', message: 'Niets gevonden om te verwijderen (mogelijk al weg).' });
  }
  return jsonOut({ status: 'ok', message: 'Verwijderd.', id });
}

// ---- Nightscout-sync (vervangt syncNightscout in Code.gs) ----

async function syncNightscout(env) {
  const NS_URL = (env.NS_URL || '').replace(/\/+$/, '');
  const NS_TOKEN = env.NS_TOKEN;

  const lastSync = await getState(env, 'last_sync_iso');
  let sinceDate;
  if (lastSync) {
    sinceDate = new Date(new Date(lastSync).getTime() - 30 * 60 * 1000);
  } else {
    sinceDate = new Date(Date.now() - 24 * 60 * 60 * 1000);
  }
  const sinceIso = sinceDate.toISOString();

  const entriesUrl = NS_URL + '/api/v1/entries.json?find[dateString][$gte]=' +
    encodeURIComponent(sinceIso) + '&count=2000&token=' + NS_TOKEN;
  const treatUrl = NS_URL + '/api/v1/treatments.json?find[created_at][$gte]=' +
    encodeURIComponent(sinceIso) + '&count=500&token=' + NS_TOKEN;

  const fetchHeaders = {
    'User-Agent': 'Mozilla/5.0 (compatible; GlucoseDashboardSync/1.0)',
    'Accept': 'application/json'
  };
  const [entriesRes, treatRes] = await Promise.all([
    fetch(entriesUrl, { headers: fetchHeaders }),
    fetch(treatUrl, { headers: fetchHeaders })
  ]);

  const entriesCT = entriesRes.headers.get('content-type') || '';
  if (!entriesCT.includes('json')) {
    const body = await entriesRes.text();
    throw new Error('Nightscout gaf geen JSON terug (status ' + entriesRes.status + '): ' + body.slice(0, 200));
  }
  const entries = await entriesRes.json();
  const treatmentsData = await treatRes.json();

  // Dedup: bestaande timestamps binnen het overlap-venster ophalen
  const existingRows = await env.DB.prepare(
    "SELECT timestamp, type, event_type FROM nightscout_data WHERE timestamp >= ?"
  ).bind(fmtTimestamp(sinceDate)).all();
  const existingKeys = new Set(existingRows.results.map(r => r.timestamp + '|' + r.type + '|' + (r.event_type || '')));

  const newRows = [];

  entries.forEach(e => {
    if (!e.sgv) return;
    const ts = e.date ? new Date(e.date) : new Date(e.dateString);
    if (isNaN(ts.getTime())) return;
    const tsText = fmtTimestamp(ts);
    const key = tsText + '|glucose|';
    if (existingKeys.has(key)) return;
    existingKeys.add(key);
    newRows.push({ ts, sql: 'glucose', vals: [tsText, 'glucose', (e.sgv / 18).toFixed(1), null, null, null, null] });
  });

  treatmentsData.forEach(t => {
    const ts = new Date(t.created_at);
    if (isNaN(ts.getTime())) return;
    const tsText = fmtTimestamp(ts);
    const eventType = t.eventType || '';
    const key = tsText + '|treatment|' + eventType;
    if (existingKeys.has(key)) return;
    existingKeys.add(key);
    newRows.push({ ts, sql: 'treatment', vals: [tsText, 'treatment', null, t.carbs || null, t.insulin || null, t.notes || null, eventType || null] });
  });

  newRows.sort((a, b) => a.ts - b.ts);

  if (newRows.length > 0) {
    const stmts = newRows.map(r =>
      env.DB.prepare('INSERT INTO nightscout_data (timestamp, type, glucose, amount, bolus, notes, event_type) VALUES (?, ?, ?, ?, ?, ?, ?)').bind(...r.vals)
    );
    for (let i = 0; i < stmts.length; i += 100) {
      await env.DB.batch(stmts.slice(i, i + 100));
    }
    await setState(env, 'last_sync_iso', newRows[newRows.length - 1].ts.toISOString());
  }

  return newRows.length;
}

// ---- /mcp: Model Context Protocol server (Fase 1 - alleen lezen) ----

const MCP_TOOLS = [
  {
    name: 'get_glucose_data',
    description: 'Haalt de actuele en historische diabetesdata op: glucosewaarden, insuline-bolussen, maaltijden (koolhydraten), beweging/sport, en de ruwe logboek-entries. Gebruik dit om vragen te beantwoorden over de huidige bloedglucose, recente maaltijden, laatste bolus, of trends over tijd.',
    inputSchema: { type: 'object', properties: {}, required: [] }
  }
];

function mcpResult(id, result) {
  return jsonOut({ jsonrpc: '2.0', id, result });
}

function mcpError(id, code, message) {
  return jsonOut({ jsonrpc: '2.0', id: id ?? null, error: { code, message } });
}

async function handleMcp(request, env) {
  const url = new URL(request.url);
  if (!env.READ_KEY || url.searchParams.get('key') !== env.READ_KEY) {
    return jsonOut({ jsonrpc: '2.0', id: null, error: { code: -32001, message: 'Toegang geweigerd.' } }, 403);
  }

  if (request.method === 'GET') {
    // Geen server-initiated streaming ondersteund (stateless server) - conform MCP-spec.
    return new Response('Method Not Allowed', { status: 405 });
  }

  let body;
  try {
    body = await request.json();
  } catch (err) {
    return mcpError(null, -32700, 'Parse error');
  }

  const { id, method, params } = body;

  // Notificaties (geen 'id') vereisen geen response-body.
  if (method === 'notifications/initialized') {
    return new Response(null, { status: 202 });
  }

  if (method === 'initialize') {
    return mcpResult(id, {
      protocolVersion: (params && params.protocolVersion) || '2024-11-05',
      capabilities: { tools: {} },
      serverInfo: { name: 'glucose-dashboard-mcp', version: '1.0.0' }
    });
  }

  if (method === 'ping') {
    return mcpResult(id, {});
  }

  if (method === 'tools/list') {
    return mcpResult(id, { tools: MCP_TOOLS });
  }

  if (method === 'tools/call') {
    const toolName = params && params.name;
    if (toolName === 'get_glucose_data') {
      try {
        const data = await getData(env);
        return mcpResult(id, {
          content: [{ type: 'text', text: JSON.stringify(data) }]
        });
      } catch (err) {
        return mcpResult(id, {
          content: [{ type: 'text', text: 'Fout bij ophalen van data: ' + String(err) }],
          isError: true
        });
      }
    }
    return mcpError(id, -32602, 'Onbekende tool: ' + toolName);
  }

  return mcpError(id, -32601, 'Methode niet gevonden: ' + method);
}

// ---- /api/layout/*: indeling van de Home-widgets (opgeslagen via kv_state) ----

function layoutDevice(params) {
  return params.get('device') === 'mobile' ? 'mobile' : 'desktop';
}

async function handleLayoutGet(env, params) {
  const device = layoutDevice(params);
  let layout = await getState(env, 'home_layout_' + device);
  if (!layout) layout = await getState(env, 'home_layout'); // migratie: oude gedeelde layout als startpunt
  return jsonOut({ status: 'ok', layout: layout || null });
}

async function handleLayoutSave(env, params) {
  const device = layoutDevice(params);
  const layout = params.get('layout');
  if (!layout) return jsonOut({ status: 'error', message: 'Geen layout opgegeven.' });
  await setState(env, 'home_layout_' + device, layout);
  return jsonOut({ status: 'ok' });
}

async function handleLayoutSetDefault(env, params) {
  const device = layoutDevice(params);
  let layout = await getState(env, 'home_layout_' + device);
  if (!layout) layout = await getState(env, 'home_layout'); // migratie
  if (!layout) return jsonOut({ status: 'error', message: 'Nog geen indeling om als standaard op te slaan.' });
  await setState(env, 'home_layout_default_' + device, layout);
  return jsonOut({ status: 'ok' });
}

async function handleLayoutReset(env, params) {
  const device = layoutDevice(params);
  let def = await getState(env, 'home_layout_default_' + device);
  if (!def) def = await getState(env, 'home_layout_default'); // migratie
  if (def) {
    await setState(env, 'home_layout_' + device, def);
  }
  return jsonOut({ status: 'ok', layout: def || null });
}

// ---- /api/link: entries aan elkaar koppelen (bolus/khd/beweging, alles met alles) ----

async function handleLink(env, params) {
  const id = Number(params.get('id'));
  if (!id) return jsonOut({ status: 'error', message: 'Geen id opgegeven.' });

  const linkToRaw = params.get('linkTo') || '';
  const linkTo = [...new Set(linkToRaw.split(',').map(s => Number(s.trim())).filter(n => n && n !== id))];

  await env.DB.prepare('DELETE FROM entry_links WHERE entry_a_id = ? OR entry_b_id = ?').bind(id, id).run();

  if (linkTo.length) {
    const now = fmtTimestamp(new Date());
    const stmts = linkTo.map(otherId =>
      env.DB.prepare('INSERT INTO entry_links (entry_a_id, entry_b_id, created_at) VALUES (?, ?, ?)').bind(id, otherId, now)
    );
    await env.DB.batch(stmts);
  }
  return jsonOut({ status: 'ok', message: 'Koppelingen bijgewerkt.', id, linkTo });
}

// ---- /summary: platte, server-side gerenderde HTML-samenvatting (voor AI's die geen JS/JSON/OAuth aankunnen) ----

async function handleSummary(env, params) {
  if (!env.READ_KEY || params.get('key') !== env.READ_KEY) {
    return new Response('Toegang geweigerd.', { status: 403, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }

  const data = await getData(env);
  const glucose = data.glucose;
  const latest = glucose[glucose.length - 1];
  const prev = glucose[glucose.length - 2];
  const trend = (latest && prev) ? (latest.glucose - prev.glucose) : 0;
  const trendLabel = trend > 0.05 ? 'stijgend' : (trend < -0.05 ? 'dalend' : 'stabiel');

  const cutoff24 = Date.now() - 24 * 3600000;
  const last24 = glucose.filter(g => new Date(g.ts).getTime() >= cutoff24);
  const low = last24.filter(g => g.glucose < 3.9).length;
  const high = last24.filter(g => g.glucose > 10.0).length;
  const inRange = last24.length - low - high;
  const pct = n => last24.length ? Math.round(n / last24.length * 100) : 0;
  const avg = last24.length ? (last24.reduce((s, g) => s + g.glucose, 0) / last24.length).toFixed(1) : '-';

  const allLog = data.foodLogRaw.slice().sort((a, b) => new Date(b.ts) - new Date(a.ts));
  const lastBolus = allLog.find(r => r.type === 'bolus');
  const lastMeal = allLog.find(r => r.type === 'khd');
  const lastExercise = allLog.find(r => r.type === 'beweging');
  const recent = allLog.slice(0, 15);

  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function fmt(ts) { return new Date(ts).toLocaleString('nl-NL', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }); }

  const html = '<!DOCTYPE html>\n' +
'<html lang="nl">\n' +
'<head><meta charset="utf-8"><title>Glucose-dashboard - samenvatting</title></head>\n' +
'<body>\n' +
'<h1>Glucose-dashboard - samenvatting</h1>\n' +
'<p>Gegenereerd op ' + esc(new Date().toLocaleString('nl-NL')) + '</p>\n' +
'<h2>Huidige status</h2>\n' +
'<ul>\n' +
'<li>Laatste glucosewaarde: ' + (latest ? esc(latest.glucose) + ' mmol/L' : 'onbekend') + (latest ? ' (' + esc(fmt(latest.ts)) + ')' : '') + '</li>\n' +
'<li>Trend: ' + esc(trendLabel) + '</li>\n' +
'</ul>\n' +
'<h2>Laatste 24 uur</h2>\n' +
'<ul>\n' +
'<li>Gemiddelde: ' + esc(avg) + ' mmol/L</li>\n' +
'<li>Low: ' + pct(low) + '%, In range: ' + pct(inRange) + '%, High: ' + pct(high) + '%</li>\n' +
'</ul>\n' +
'<h2>Laatste bolus</h2>\n' +
'<p>' + (lastBolus ? esc(lastBolus.amount) + 'E (' + esc(lastBolus.bolusType || 'onbekend type') + ') om ' + esc(fmt(lastBolus.ts)) + (lastBolus.context ? ' - ' + esc(lastBolus.context) : '') : 'Geen bolus gevonden.') + '</p>\n' +
'<h2>Laatste maaltijd</h2>\n' +
'<p>' + (lastMeal ? esc(lastMeal.desc) + ' (' + esc(lastMeal.amount) + 'g khd) om ' + esc(fmt(lastMeal.ts)) : 'Geen maaltijd gevonden.') + '</p>\n' +
'<h2>Laatste beweging</h2>\n' +
'<p>' + (lastExercise ? esc(lastExercise.desc) + ' om ' + esc(fmt(lastExercise.ts)) + (lastExercise.context ? ' (' + esc(lastExercise.context) + ')' : '') : 'Geen beweging gevonden.') + '</p>\n' +
'<h2>Recente log-entries (laatste 15)</h2>\n' +
'<ul>\n' +
recent.map(r => '<li>' + esc(fmt(r.ts)) + ' - ' + esc(r.type) + ': ' + esc(r.desc) + ' (' + esc(r.amount) + (r.type === 'bolus' ? 'E' : 'g') + ')' + (r.context ? ' - ' + esc(r.context) : '') + (r.tags ? ' [tags: ' + esc(r.tags) + ']' : '') + '</li>').join('\n') +
'\n</ul>\n' +
'</body>\n</html>';

  return new Response(html, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}

// ---- /export: volledige platte-tekst dump (glucose + logboek), on-demand uit de database ----

async function handleExport(env, params) {
  if (!env.READ_KEY || params.get('key') !== env.READ_KEY) {
    return new Response('Toegang geweigerd.', { status: 403, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }
  const days = Math.min(400, Math.max(1, Number(params.get('days')) || 7));
  const data = await getData(env, days);
  const cutoff = Date.now() - days * 24 * 3600000;

  function fmt(ts) { return new Date(ts).toLocaleString('nl-NL', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }); }
  function dateOnly(ts) { return new Date(ts).toLocaleDateString('nl-NL', { day: 'numeric', month: 'short', year: 'numeric' }); }

  const glucose = data.glucose.filter(g => new Date(g.ts).getTime() >= cutoff);
  const logs = data.foodLogRaw
    .filter(r => new Date(r.ts).getTime() >= cutoff)
    .sort((a, b) => new Date(b.ts) - new Date(a.ts));

  let out = '';
  out += 'GLUCOSE-DASHBOARD - VOLLEDIGE DATA-EXPORT\n';
  out += 'Periode: laatste ' + days + ' dagen. Gegenereerd: ' + new Date().toLocaleString('nl-NL') + '\n';
  out += 'Type 1 diabetes. Snelwerkend: Novorapid. Basaal: Lantus (normaal 14E per avond, 12E op bokstraining-dagen, lopend experiment).\n';
  out += '=================================================================\n\n';

  function nearbyGlucoseSnippet(ts) {
    const center = new Date(ts).getTime();
    const offsets = [[-30, '-30m'], [0, 'moment'], [30, '+30m'], [60, '+60m']];
    const parts = [];
    offsets.forEach(([offsetMin, label]) => {
      const target = center + offsetMin * 60000;
      let best = null, bestDiff = Infinity;
      data.glucose.forEach(g => {
        const diff = Math.abs(new Date(g.ts).getTime() - target);
        if (diff < bestDiff && diff < 10 * 60000) { bestDiff = diff; best = g.glucose; }
      });
      if (best != null) parts.push(label + ': ' + best);
    });
    return parts.length ? parts.join(', ') : null;
  }

  out += '--- LOGBOEK (' + logs.length + ' entries, meest recent eerst, altijd volledig) ---\n\n';
  logs.forEach(r => {
    out += '[' + fmt(r.ts) + '] ' + r.type.toUpperCase();
    if (r.type === 'bolus') out += ' ' + r.bolusType + ' - ' + r.amount + 'E' + (r.bgAtEntry != null ? ' (BG ' + r.bgAtEntry + ')' : '');
    else if (r.type === 'khd') out += ' - ' + r.desc + ' (' + r.amount + 'g khd)';
    else out += ' - ' + r.desc + (r.amount ? ' (' + r.amount + ')' : '');
    if (r.context) out += '\n  Context: ' + r.context;
    if (r.tags) out += '\n  Tags: ' + r.tags;
    if (r.links && r.links.length) out += '\n  Gekoppeld aan: ' + r.links.map(l => l.desc || l.type).join(', ');
    const snippet = nearbyGlucoseSnippet(r.ts);
    if (snippet) out += '\n  BG rond dit moment: ' + snippet;
    out += '\n\n';
  });

  if (days <= 3) {
    out += '--- GLUCOSEWAARDEN (' + glucose.length + ' metingen, elke ~5 min, chronologisch) ---\n\n';
    glucose.forEach(g => { out += fmt(g.ts) + ': ' + g.glucose + ' mmol/L\n'; });
  } else {
    const byDay = {};
    glucose.forEach(g => {
      const d = dateOnly(g.ts);
      (byDay[d] = byDay[d] || []).push(g.glucose);
    });
    const dayKeys = Object.keys(byDay).sort((a, b) => new Date(a) - new Date(b));
    out += '--- GLUCOSE PER DAG (' + dayKeys.length + ' dagen, samengevat - periode >3 dagen dus geen losse metingen) ---\n\n';
    dayKeys.forEach(d => {
      const vals = byDay[d];
      const avg = (vals.reduce((s, v) => s + v, 0) / vals.length).toFixed(1);
      const low = Math.round(vals.filter(v => v < 3.9).length / vals.length * 100);
      const high = Math.round(vals.filter(v => v > 10.0).length / vals.length * 100);
      const inRange = 100 - low - high;
      out += d + ': gemiddelde ' + avg + ' mmol/L, low ' + low + '%, in range ' + inRange + '%, high ' + high + '% (n=' + vals.length + ')\n';
    });
  }

  return new Response(out, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
}

// ---- Router ----

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/api/data') {
      if (!env.READ_KEY || url.searchParams.get('key') !== env.READ_KEY) {
        return jsonOut({ status: 'error', message: 'Toegang geweigerd.' }, 403);
      }
      return handleData(env, url.searchParams);
    }

    if (url.pathname === '/api/log') {
      if (!env.WRITE_KEY || url.searchParams.get('key') !== env.WRITE_KEY) {
        return jsonOut({ status: 'error', message: 'Toegang geweigerd.' }, 403);
      }
      return handleLog(env, url.searchParams);
    }

    if (url.pathname === '/api/admin/sync-check') {
      if (!env.WRITE_KEY || url.searchParams.get('key') !== env.WRITE_KEY) {
        return jsonOut({ status: 'error', message: 'Toegang geweigerd.' }, 403);
      }
      try {
        const newRows = await syncNightscout(env);
        return jsonOut({ status: 'ok', newRows });
      } catch (err) {
        return jsonOut({ status: 'error', message: String(err), stack: err.stack });
      }
    }

    if (url.pathname === '/api/update') {
      if (!env.WRITE_KEY || url.searchParams.get('key') !== env.WRITE_KEY) {
        return jsonOut({ status: 'error', message: 'Toegang geweigerd.' }, 403);
      }
      return handleUpdate(env, url.searchParams);
    }

    if (url.pathname === '/api/delete') {
      if (!env.WRITE_KEY || url.searchParams.get('key') !== env.WRITE_KEY) {
        return jsonOut({ status: 'error', message: 'Toegang geweigerd.' }, 403);
      }
      return handleDelete(env, url.searchParams);
    }

    if (url.pathname === '/api/link') {
      if (!env.WRITE_KEY || url.searchParams.get('key') !== env.WRITE_KEY) {
        return jsonOut({ status: 'error', message: 'Toegang geweigerd.' }, 403);
      }
      return handleLink(env, url.searchParams);
    }

    if (url.pathname === '/api/summary') {
      return handleApiSummary(env, url.searchParams);
    }

    if (url.pathname === '/export') {
      return handleExport(env, url.searchParams);
    }

    if (url.pathname === '/summary') {
      return handleSummary(env, url.searchParams);
    }

    if (url.pathname.startsWith('/s/')) {
      const pathKey = url.pathname.slice(3);
      return handleSummary(env, new URLSearchParams({ key: pathKey }));
    }

    if (url.pathname === '/api/layout/get') {
      if (!env.READ_KEY || url.searchParams.get('key') !== env.READ_KEY) {
        return jsonOut({ status: 'error', message: 'Toegang geweigerd.' }, 403);
      }
      return handleLayoutGet(env, url.searchParams);
    }

    if (url.pathname === '/api/layout/save') {
      if (!env.WRITE_KEY || url.searchParams.get('key') !== env.WRITE_KEY) {
        return jsonOut({ status: 'error', message: 'Toegang geweigerd.' }, 403);
      }
      return handleLayoutSave(env, url.searchParams);
    }

    if (url.pathname === '/api/layout/set-default') {
      if (!env.WRITE_KEY || url.searchParams.get('key') !== env.WRITE_KEY) {
        return jsonOut({ status: 'error', message: 'Toegang geweigerd.' }, 403);
      }
      return handleLayoutSetDefault(env, url.searchParams);
    }

    if (url.pathname === '/api/layout/reset') {
      if (!env.WRITE_KEY || url.searchParams.get('key') !== env.WRITE_KEY) {
        return jsonOut({ status: 'error', message: 'Toegang geweigerd.' }, 403);
      }
      return handleLayoutReset(env, url.searchParams);
    }

    if (url.pathname === '/mcp') {
      return handleMcp(request, env);
    }

    if (url.pathname.startsWith('/api/')) {
      return jsonOut({ status: 'error', message: 'Onbekend endpoint.' }, 404);
    }

    // Alles wat geen /api/ is: gewoon de statische site serveren
    return env.ASSETS.fetch(request);
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(syncNightscout(env));
  }
};
