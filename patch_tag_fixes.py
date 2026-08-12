#!/usr/bin/env python3
"""
Patch: tag-autocomplete fixes (alleen-taggen / spaties in tags / taggen bij edit).
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

# --- Fix 1a: quickLog mag alleen-tag entries opslaan ---
apply(
    """  const { clean: desc, tags: extractedTags } = getChipInputContent('qlDesc');
  const carbs = document.getElementById('qlCarbs').value.trim();
  const context = document.getElementById('qlContext').value.trim();
  const ts = buildTs('ql', 'qlTimeOnly');
  const status = document.getElementById('qlStatus');
  if (!desc){ status.textContent = 'Vul in wat je hebt gegeten.'; return; }

  const tags = extractedTags.join(',');""",
    """  const { clean: descRaw, tags: extractedTags } = getChipInputContent('qlDesc');
  const carbs = document.getElementById('qlCarbs').value.trim();
  const context = document.getElementById('qlContext').value.trim();
  const ts = buildTs('ql', 'qlTimeOnly');
  const status = document.getElementById('qlStatus');
  if (!descRaw && !extractedTags.length){ status.textContent = 'Vul in wat je hebt gegeten.'; return; }
  const desc = descRaw || extractedTags.map(t => '@' + t).join(' ');

  const tags = extractedTags.join(',');""",
    "quickLog: alleen-tag toestaan",
)

# --- Fix 1b: quickExercise mag alleen-tag entries opslaan ---
apply(
    """  const { clean: desc, tags: extractedTags } = getChipInputContent('qeActivity');
  const duration = document.getElementById('qeDuration').value.trim();
  const ts = buildTs('qe', 'qeTimeOnly');
  const status = document.getElementById('qeStatus');
  if (!desc){ status.textContent = 'Vul de activiteit in.'; return; }""",
    """  const { clean: descRaw, tags: extractedTags } = getChipInputContent('qeActivity');
  const duration = document.getElementById('qeDuration').value.trim();
  const ts = buildTs('qe', 'qeTimeOnly');
  const status = document.getElementById('qeStatus');
  if (!descRaw && !extractedTags.length){ status.textContent = 'Vul de activiteit in.'; return; }
  const desc = descRaw || extractedTags.map(t => '@' + t).join(' ');""",
    "quickExercise: alleen-tag toestaan",
)

# --- Fix 2: spaties toestaan in de live @-tag matcher ---
apply(
    "  const m = upToCursor.match(/@([a-zA-Z0-9\\-]*)$/);",
    "  const m = upToCursor.match(/@([a-zA-Z0-9\\- ]*)$/);",
    "spaties toestaan in tag-matcher",
)

apply(
    """    const token = findActiveAtTokenCE(input);
    if (!token) { dropdown.style.display = 'none'; return; }
    const all = DATA.tagFrequency || [];
    let matches = all.filter(t => t.tag.startsWith(token.partial)).slice(0, 6);
    const isNew = !matches.length && token.partial.length > 0;
    if (isNew) matches = [{ tag: token.partial, isNew: true }];""",
    """    const token = findActiveAtTokenCE(input);
    if (!token) { dropdown.style.display = 'none'; return; }
    const partial = token.partial.trim().replace(/\\s+/g, ' ');
    const all = DATA.tagFrequency || [];
    let matches = all.filter(t => t.tag.startsWith(partial)).slice(0, 6);
    const isNew = !matches.length && partial.length > 0;
    if (isNew) matches = [{ tag: partial, isNew: true }];""",
    "spaties normaliseren in nieuw-tag voorstel",
)

# --- Fix 3: helpers voor rdmDesc chip-content ---
apply(
    "function findActiveAtTokenCE(el){",
    """function escapeHtml(str){
  return String(str||'').replace(/[&<>"]/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }[c]));
}

function rdmDescInnerHtml(desc, tagsStr, colorClass){
  let html = escapeHtml(desc);
  const tags = (tagsStr||'').split(',').map(t => t.trim()).filter(Boolean);
  if (tags.length) {
    html += (html ? '&nbsp;' : '') + tags.map(t =>
      '<span class="tagChip ' + colorClass + '" contenteditable="false" data-tag="' + escapeHtml(t) + '">@' + escapeHtml(t) + '</span>'
    ).join('&nbsp;');
  }
  return html;
}

function findActiveAtTokenCE(el){""",
    "escapeHtml + rdmDescInnerHtml helpers toevoegen",
)

# --- Fix 3: rdmDesc omzetten naar chipInput, Tags-veld read-only ---
apply(
    """      '<input id="rdmDesc" value="' + (row.desc||'').replace(/"/g,'&quot;') + '" placeholder="Beschrijving" style="' + fieldStyle + '">' +
      '<div style="display:flex; gap:6px;">' +
        '<input id="rdmAmount" type="number" value="' + (row.amount != null ? row.amount : '') + '" placeholder="Aantal" style="flex:1; ' + fieldStyle + '">' +
        '<input id="rdmTags" value="' + (row.tags||'').replace(/"/g,'&quot;') + '" placeholder="Tags" style="flex:2; ' + fieldStyle + '">' +
      '</div>' +""",
    """      '<div style="position:relative;">' +
        '<div id="rdmDesc" class="chipInput" contenteditable="true" data-placeholder="Beschrijving (@tag om te taggen)" style="' + fieldStyle + '">' + rdmDescInnerHtml(row.desc, row.tags, 'tagChip-' + row.type) + '</div>' +
        '<div id="rdmDescAutocomplete" style="display:none; position:absolute; top:100%; left:0; right:0; margin-top:4px; background:rgba(28,28,30,0.92); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); border:0.5px solid rgba(255,255,255,0.14); border-radius:10px; box-shadow:0 8px 24px rgba(0,0,0,0.35); z-index:20; max-height:160px; overflow-y:auto;"></div>' +
      '</div>' +
      '<div style="display:flex; gap:6px;">' +
        '<input id="rdmAmount" type="number" value="' + (row.amount != null ? row.amount : '') + '" placeholder="Aantal" style="flex:1; ' + fieldStyle + '">' +
        '<input id="rdmTags" value="' + (row.tags||'').replace(/"/g,'&quot;') + '" placeholder="Tags" readonly style="flex:2; ' + fieldStyle + ' opacity:0.6; cursor:not-allowed;">' +
      '</div>' +""",
    "rdmDesc omzetten naar chipInput + Tags-veld read-only",
)

# --- Fix 3: autocomplete koppelen bij het openen van de modal ---
apply(
    """  document.getElementById('rdModalOverlay').style.display = 'flex';
  renderModalChart(row, accent);
}""",
    """  document.getElementById('rdModalOverlay').style.display = 'flex';
  renderModalChart(row, accent);

  const rdmColorClass = 'tagChip-' + row.type;
  attachTagAutocomplete('rdmDesc', rdmColorClass);
  const rdmDescEl = document.getElementById('rdmDesc');
  const rdmTagsEl = document.getElementById('rdmTags');
  if (rdmDescEl && rdmTagsEl) {
    rdmDescEl.addEventListener('input', () => {
      rdmTagsEl.value = getChipInputContent('rdmDesc').tags.join(',');
    });
  }
}""",
    "attachTagAutocomplete koppelen aan rdmDesc bij modal-open",
)

# --- Fix 3: saveRdModal leest chip-content ---
apply(
    """async function saveRdModal(id){
  const desc = document.getElementById('rdmDesc').value;
  const amount = document.getElementById('rdmAmount').value;
  const tags = document.getElementById('rdmTags').value;
  const context = document.getElementById('rdmContext').value;""",
    """async function saveRdModal(id){
  const { clean: descRaw, tags: extractedTags } = getChipInputContent('rdmDesc');
  const desc = descRaw || extractedTags.map(t => '@' + t).join(' ');
  const amount = document.getElementById('rdmAmount').value;
  const tags = extractedTags.join(',');
  const context = document.getElementById('rdmContext').value;""",
    "saveRdModal: desc/tags uit chipInput lezen",
)

PATH.write_text(src)
print("\nAlle 8 patches toegepast.")
