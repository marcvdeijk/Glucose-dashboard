import { glucoseRows, treatmentRows, mealRows, exerciseRows } from './migrate-data.js';

const MIGRATION_KEY = 'mig-e4hog8yo1o3wsy6j';

async function batchInsert(env, sql, rows, chunkSize = 100) {
  let inserted = 0;
  for (let i = 0; i < rows.length; i += chunkSize) {
    const chunk = rows.slice(i, i + chunkSize);
    const stmts = chunk.map(r => env.DB.prepare(sql).bind(...r));
    await env.DB.batch(stmts);
    inserted += chunk.length;
  }
  return inserted;
}

async function runMigration(env) {
  let inserted = 0;
  inserted += await batchInsert(env,
    'INSERT INTO nightscout_data (timestamp, type, glucose, amount, bolus, notes) VALUES (?, "glucose", ?, NULL, NULL, NULL)',
    glucoseRows);
  inserted += await batchInsert(env,
    'INSERT INTO nightscout_data (timestamp, type, glucose, amount, bolus, notes) VALUES (?, "treatment", NULL, NULL, ?, NULL)',
    treatmentRows);
  inserted += await batchInsert(env,
    'INSERT INTO food_log (timestamp, description, tags, amount, context, type) VALUES (?, ?, ?, ?, ?, ?)',
    mealRows);
  inserted += await batchInsert(env,
    'INSERT INTO food_log (timestamp, description, tags, amount, context, type) VALUES (?, ?, ?, NULL, ?, "beweging")',
    exerciseRows);
  return inserted;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/api/admin/migrate') {
      if (url.searchParams.get('key') !== MIGRATION_KEY) {
        return new Response(JSON.stringify({ status: 'error', message: 'Ongeldige sleutel.' }), {
          status: 403,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      try {
        const count = await runMigration(env);
        return new Response(JSON.stringify({ status: 'ok', inserted: count }), {
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (err) {
        return new Response(JSON.stringify({ status: 'error', message: String(err) }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    if (url.pathname.startsWith('/api/')) {
      return new Response(JSON.stringify({ status: 'error', message: 'API nog niet geimplementeerd (volgt in Fase 3).' }), {
        status: 501,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Alles wat geen /api/ is: gewoon de statische site serveren
    return env.ASSETS.fetch(request);
  }
};
