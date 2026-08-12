#!/usr/bin/env python3
"""
Patch: MCP write-tool delete_entry (aanvulling op log_entry/update_entry).
Hergebruikt de bestaande handleDelete - zelfde bevestig-eerst werkwijze.
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
    """  {
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
    """  {
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
  },
  {
    name: 'delete_entry',
    description: 'Verwijdert een bestaande entry definitief (op id). Toon de gebruiker ALTIJD eerst een samenvatting van de entry (tijd, type, waarden) en wacht op expliciet akkoord voordat je deze tool aanroept - dit kan niet ongedaan gemaakt worden.',
    inputSchema: {
      type: 'object',
      properties: {
        id: { type: 'number', description: 'Id van de te verwijderen entry (uit get_glucose_data / foodLogRaw).' }
      },
      required: ['id']
    }
  }
];""",
    "MCP_TOOLS: delete_entry toevoegen",
)

apply(
    """    if (toolName === 'update_entry') {
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
    """    if (toolName === 'update_entry') {
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

    if (toolName === 'delete_entry') {
      try {
        const usp = new URLSearchParams();
        Object.entries(args).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== '') usp.set(k, String(v)); });
        const result = await handleDelete(env, usp);
        const resultJson = await result.json();
        return mcpResult(id, { content: [{ type: 'text', text: JSON.stringify(resultJson) }] });
      } catch (err) {
        return mcpResult(id, { content: [{ type: 'text', text: 'Fout bij verwijderen: ' + String(err) }], isError: true });
      }
    }

    return mcpError(id, -32602, 'Onbekende tool: ' + toolName);
  }""",
    "tools/call: delete_entry afhandelen",
)

PATH.write_text(src)
print("\nAlle 2 patches toegepast.")
