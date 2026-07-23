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

async function handleData(env) {
  const glucoseRows = await env.DB.prepare(
    "SELECT timestamp, glucose FROM nightscout_data WHERE type = 'glucose' ORDER BY timestamp"
  ).all();
  const glucose = glucoseRows.results.map(r => ({ ts: r.timestamp.replace(' ', 'T'), glucose: r.glucose }));

  const treatmentRows = await env.DB.prepare(
    "SELECT timestamp, bolus FROM nightscout_data WHERE type = 'treatment' AND bolus > 0 ORDER BY timestamp"
  ).all();
  const treatments = treatmentRows.results.map(r => ({ ts: r.timestamp.replace(' ', 'T'), bolus: r.bolus }));

  const logRows = await env.DB.prepare(
    "SELECT id, timestamp, description, tags, amount, context, type FROM food_log ORDER BY timestamp"
  ).all();

  const foodLogRaw = logRows.results.map(r => ({
    id: r.id, ts: r.timestamp.replace(' ', 'T'), desc: r.description, tags: r.tags, amount: r.amount, context: r.context, type: r.type || ''
  }));

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

  return jsonOut({ glucose, treatments, meals, exercises, foodLogRaw });
}

// ---- /api/log: schrijven ----

async function handleLog(env, params) {
  const lastLogAt = await getState(env, 'last_log_at');
  const now = Date.now();
  if (lastLogAt && (now - Number(lastLogAt)) < 2000) {
    return jsonOut({ status: 'error', message: 'Te snel achter elkaar, probeer over een paar seconden opnieuw.' });
  }
  await setState(env, 'last_log_at', String(now));

  const ts = params.get('ts');
  const tsText = ts ? ts.replace('T', ' ') + ':00' : fmtTimestamp(new Date());

  const desc = params.get('desc') || '';
  const tags = params.get('tags') || '';
  const amount = params.get('carbs') !== null && params.get('carbs') !== '' ? Number(params.get('carbs')) : null;
  const context = params.get('context') || '';
  const type = params.get('type') || 'khd';

  await env.DB.prepare(
    'INSERT INTO food_log (timestamp, description, tags, amount, context, type) VALUES (?, ?, ?, ?, ?, ?)'
  ).bind(tsText, desc, tags, amount, context, type).run();

  return jsonOut({ status: 'ok', message: 'Gelogd: ' + tsText + ' - ' + desc, ts: tsText });
}

// ---- /api/update: een eigen log-entry bewerken ----

async function handleUpdate(env, params) {
  const id = params.get('id');
  if (!id) {
    return jsonOut({ status: 'error', message: 'Geen id opgegeven.' });
  }
  const desc = params.get('desc') || '';
  const tags = params.get('tags') || '';
  const amount = params.get('amount') !== null && params.get('amount') !== '' ? Number(params.get('amount')) : null;
  const context = params.get('context') || '';

  const result = await env.DB.prepare(
    'UPDATE food_log SET description = ?, tags = ?, amount = ?, context = ? WHERE id = ?'
  ).bind(desc, tags, amount, context, id).run();

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
  const NS_URL = env.NS_URL;
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
    "SELECT timestamp, type FROM nightscout_data WHERE timestamp >= ?"
  ).bind(fmtTimestamp(sinceDate)).all();
  const existingKeys = new Set(existingRows.results.map(r => r.timestamp + '|' + r.type));

  const newRows = [];

  entries.forEach(e => {
    if (!e.sgv) return;
    const ts = e.date ? new Date(e.date) : new Date(e.dateString);
    if (isNaN(ts.getTime())) return;
    const tsText = fmtTimestamp(ts);
    const key = tsText + '|glucose';
    if (existingKeys.has(key)) return;
    existingKeys.add(key);
    newRows.push({ ts, sql: 'glucose', vals: [tsText, 'glucose', (e.sgv / 18).toFixed(1), null, null, null] });
  });

  treatmentsData.forEach(t => {
    const ts = new Date(t.created_at);
    if (isNaN(ts.getTime())) return;
    const tsText = fmtTimestamp(ts);
    const key = tsText + '|treatment';
    if (existingKeys.has(key)) return;
    existingKeys.add(key);
    newRows.push({ ts, sql: 'treatment', vals: [tsText, 'treatment', null, t.carbs || null, t.insulin || null, t.notes || null] });
  });

  newRows.sort((a, b) => a.ts - b.ts);

  if (newRows.length > 0) {
    const stmts = newRows.map(r =>
      env.DB.prepare('INSERT INTO nightscout_data (timestamp, type, glucose, amount, bolus, notes) VALUES (?, ?, ?, ?, ?, ?)').bind(...r.vals)
    );
    for (let i = 0; i < stmts.length; i += 100) {
      await env.DB.batch(stmts.slice(i, i + 100));
    }
    await setState(env, 'last_sync_iso', newRows[newRows.length - 1].ts.toISOString());
  }

  return newRows.length;
}

// ---- Router ----

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/api/data') {
      if (!env.READ_KEY || url.searchParams.get('key') !== env.READ_KEY) {
        return jsonOut({ status: 'error', message: 'Toegang geweigerd.' }, 403);
      }
      return handleData(env);
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
