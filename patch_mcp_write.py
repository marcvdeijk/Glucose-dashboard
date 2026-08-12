#!/usr/bin/env python3
"""
Patch: MCP write-tools (log_entry, update_entry) voor de proefweek.
Voegt twee schrijfbare tools toe aan de bestaande MCP-server, die intern
handleLog/handleUpdate hergebruiken - de write-key blijft server-side,
Claude ziet 'm nooit.
Draai dit vanuit ~/Desktop/Glucose-dashboard.
"""
import pathlib

PATH = pathlib.Path("src/index.js")
src = PATH.read_text()

def apply(old, new, label):
    global src
    count = src.count(old)
    assert count == 1, f"[{label}] anchor gevonden {count}x, verwacht 1x"
    src = src.replace(old, new)
    print(f"OK: {label}")

apply(
    """// ---- /mcp: Model Context Protocol server (Fase 1 - alleen lezen) ----

const MCP_TOOLS = [
  {
    name: 'get_glucose_data',
    description: 'Haalt de actuele en historische diabetesdata op: glucosewaarden, insuline-bolussen, maaltijden (koolhydraten), beweging/sport, en de ruwe logboek-entries. Gebruik dit om vragen te beantwoorden over de huidige bloedglucose, recente maaltijden, laatste bolus, of trends over tijd.',
    inputSchema: { type: 'object', properties: {}, required: [] }
  }
];""",
    """// ---- /mcp: Model Context Protocol server ----

const MCP_TOOLS = [
  {
    name: 'get_glucose_data',
    description: 'Haalt de actuele en historische diabetesdata op: glucosewaarden, insuline-bolussen, maaltijden (koolhydraten), beweging/sport, en de ruwe logboek-entries. Gebruik dit om vragen te beantwoorden over de huidige bloedglucose, recente maaltijden, laatste bolus, of trends over tijd.',
    inputSchema: { type: 'object', properties: {}, required: [] }
  },
  {
    name: 'log_entry',
    description: 'Logt een nieuwe entry (maaltijd/khd, bolus, of beweging) in het glucose-dashboard. Toon de gebruiker ALTIJD eerst een samenvatting van wat je gaat loggen en wacht op expliciet akkoord voordat je deze tool aanroept.',
    inputSchema: {
      type: 'object',
      properties: {
        type: { type: 'string', enum: ['khd', 'bolus', 'beweging'], description: 'Type entry.' },
        desc: { type: 'string', description: 'Beschrijving (bv. maaltijdnaam, of gebruik @tag voor tags).' },
        carbs: { type: 'number', description: 'Koolhydraten in gram (alleen bij type khd).' },
        amount: { type: 'number', description: 'Aantal eenheden insuline (bij bolus) of duur in minuten (bij beweging).' },
        tags: { type: 'string', description: 'Komma-gescheiden tags (optioneel, meestal via @tag in desc).' },
        context: { type: 'string', description: 'Vrije context/notitie (optioneel).' },
        bolusType: { type: 'string', enum: ['regulier', 'pre-bolus', 'correctie', 'na-bolus'], description: 'Alleen bij type bolus.' },
        absorptionScore: { type: 'number', description: '0-5 verwerkingsschaal (alleen bij type khd, indien geen macro\\'s bekend zijn).' },
        fat: { type: 'number', description: 'Vet in gram (alleen bij type khd).' },
        protein: { type: 'number', description: 'Eiwit in gram (alleen bij type khd).' },
        calories: { type: 'number', description: 'Calorieen (optioneel, alleen bij type khd).' },
        ts: { type: 'string', description: 'Tijdstip in formaat YYYY-MM-DDTHH:MM (optioneel, standaard nu).' }
      },
      required: ['type', 'desc']
    }
  },
  {
    name: 'update_entry',
    description: 'Werkt een bestaande entry bij (op id). Toon de gebruiker ALTIJD eerst een samenvatting van de wijziging en wacht op expliciet akkoord voordat je deze tool aanroept.',
    inputSchema: {
      type: 'object',
      properties: {
        id: { type: 'number', description: 'Id van de bij te werken entry (uit get_glucose_data / foodLogRaw).' },
        type: { type: 'string', enum: ['khd', 'bolus', 'beweging'] },
        desc: { type: 'string' },
        amount: { type: 'number' },
        tags: { type: 'string' },
        context: { type: 'string' },
        bolusType: { type: 'string', enum: ['regulier', 'pre-bolus', 'correctie', 'na-bolus'] },
        absorptionScore: { type: 'number' },
        fat: { type: 'number' },
        protein: { type: 'number' },
        calories: { type: 'number' },
        ts: { type: 'string' }
      },
      required: ['id']
    }
  }
];""",
    "MCP_TOOLS: log_entry + update_entry toevoegen",
)

apply(
    """  if (method === 'tools/call') {
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
  }""",
    """  if (method === 'tools/call') {
    const toolName = params && params.name;
    const args = (params && params.arguments) || {};

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

    if (toolName === 'log_entry') {
      try {
        const usp = new URLSearchParams();
        Object.entries(args).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== '') usp.set(k, String(v)); });
        if (!usp.has('source')) usp.set('source', 'Claude');
        const result = await handleLog(env, usp);
        const resultJson = await result.json();
        return mcpResult(id, { content: [{ type: 'text', text: JSON.stringify(resultJson) }] });
      } catch (err) {
        return mcpResult(id, { content: [{ type: 'text', text: 'Fout bij loggen: ' + String(err) }], isError: true });
      }
    }

    if (toolName === 'update_entry') {
      try {
        const usp = new URLSearchParams();
        Object.entries(args).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== '') usp.set(k, String(v)); });
        const result = await handleUpdate(env, usp);
        const resultJson = await result.json();
        return mcpResult(id, { content: [{ type: 'text', text: JSON.stringify(resultJson) }] });
      } catch (err) {
        return mcpResult(id, { content: [{ type: 'text', text: 'Fout bij bijwerken: ' + String(err) }], isError: true });
      }
    }

    return mcpError(id, -32602, 'Onbekende tool: ' + toolName);
  }""",
    "tools/call: log_entry + update_entry afhandelen",
)

PATH.write_text(src)
print("\nAlle 2 patches toegepast.")
