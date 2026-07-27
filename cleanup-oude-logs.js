// Eenmalig opschoonscript voor bestaande food_log-entries.
// Haalt alle data op, herkent oude bolus/beweging-logs, en update ze naar het
// nieuwe, schone format (geen 'zelf-gemeld-bolus'-tag, geen [BEWEGING]-prefix meer).
//
// Gebruik:
//   node cleanup-oude-logs.js            -> laat alleen zien wat er zou veranderen
//   node cleanup-oude-logs.js --apply    -> voert de wijzigingen ook echt door

const READ_KEY = 'mvd-read-sob3zauq94';
const WRITE_KEY = 'mvd-write-q79zvh9s02';
const BASE = 'https://glucose-dashboard.marcvdeijk.workers.dev';

const APPLY = process.argv.includes('--apply');

const bewegingRegex = /^\[BEWEGING\] (Duursport|HIIT|Krachttraining) - (.+?)(?: \((\d+) min\))?$/;
const bolusDescRegex = /^Bolus ([\d.]+)E \(zelf gemeld\)$/;
const bolusContextRegex = /^\[ZELF GEMELD, NIET IN ZUKKA\] (.+?) - controleer of dit ook in Zukka wordt gelogd om dubbele telling te voorkomen\.$/;

function cleanRow(r) {
  let newDesc = r.desc;
  let newTags = r.tags;
  let newContext = r.context;
  let changed = false;

  if (r.type === 'beweging') {
    const m = (r.desc || '').match(bewegingRegex);
    if (m) {
      newDesc = m[2];
      newTags = m[1].toLowerCase();
      changed = true;
    }
  }

  if (r.type === 'bolus') {
    const dm = (r.desc || '').match(bolusDescRegex);
    if (dm) {
      newDesc = 'Bolus ' + dm[1] + 'E';
      changed = true;
    }
    if (r.tags === 'zelf-gemeld-bolus') {
      newTags = '';
      changed = true;
    }
    const cm = (r.context || '').match(bolusContextRegex);
    if (cm) {
      newContext = cm[1] === 'Geen reden opgegeven' ? '' : cm[1];
      changed = true;
    }
  }

  if (!changed) return null;
  return { id: r.id, ts: r.ts.slice(0, 16), type: r.type, newDesc, newTags, newContext, oldDesc: r.desc, oldTags: r.tags, oldContext: r.context };
}

async function main() {
  const res = await fetch(BASE + '/api/data?key=' + READ_KEY);
  const data = await res.json();
  const changes = data.foodLogRaw.map(cleanRow).filter(Boolean);

  console.log(`${changes.length} entries gevonden om op te schonen.\n`);

  for (const c of changes) {
    console.log(`#${c.id} (${c.type}, ${c.ts})`);
    console.log(`  desc:    "${c.oldDesc}" -> "${c.newDesc}"`);
    console.log(`  tags:    "${c.oldTags}" -> "${c.newTags}"`);
    console.log(`  context: "${c.oldContext}" -> "${c.newContext}"`);
    console.log('');
  }

  if (!APPLY) {
    console.log('Dit was een droogloop (geen wijzigingen doorgevoerd).');
    console.log('Ziet dit er goed uit? Draai dan: node cleanup-oude-logs.js --apply');
    return;
  }

  console.log('Wijzigingen doorvoeren...\n');
  for (const c of changes) {
    const url = BASE + '/api/update?key=' + WRITE_KEY +
      '&id=' + c.id +
      '&desc=' + encodeURIComponent(c.newDesc) +
      '&tags=' + encodeURIComponent(c.newTags) +
      '&context=' + encodeURIComponent(c.newContext) +
      '&ts=' + encodeURIComponent(c.ts) +
      '&type=' + encodeURIComponent(c.type);
    const r = await fetch(url);
    const j = await r.json();
    console.log(`#${c.id}: ${j.status}`);
    await new Promise(resolve => setTimeout(resolve, 2100));
  }
  console.log('\nKlaar.');
}

main().catch(err => {
  console.error('Fout:', err);
  process.exit(1);
});
