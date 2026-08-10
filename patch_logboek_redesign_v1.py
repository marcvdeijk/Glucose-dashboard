path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

def patch(old, new, label):
    global text
    count = text.count(old)
    assert count == 1, f"[{label}] expected 1 occurrence, found {count}"
    text = text.replace(old, new, 1)

# 1. Tag chip: add visible border so pills read clearly.
patch(
    '.rdChip.tag { background:rgba(93,202,165,0.14); color:#94ddc4; }',
    '.rdChip.tag { background:rgba(93,202,165,0.16); color:#94ddc4; border:0.5px solid rgba(93,202,165,0.4); }',
    "tag chip border"
)

# 2. Remove the "Log" nav button (pencil icon).
patch(
    '''  <button id="tabGrafiek" onclick="showTab('log')" title="Log" style="width:40px; height:40px; background:transparent; color:#b7b7b2; border:0.5px solid rgba(255,255,255,0.14); border-radius:10px; padding:0; cursor:pointer; display:flex; align-items:center; justify-content:center;"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg></button>
''',
    '',
    "remove tabGrafiek nav button"
)

# 3. showTab(): viewGrafiek only tied to 'home' now; drop logPanelsSection display line; drop tabGrafiek from tabs map.
patch(
    '''  const showShared = (tab === 'home' || tab === 'log');
  document.getElementById('viewGrafiek').style.display = showShared ? 'block' : 'none';''',
    '''  document.getElementById('viewGrafiek').style.display = (tab === 'home') ? 'block' : 'none';''',
    "showTab showShared"
)
patch(
    '''  document.getElementById('homeTilesSection').style.display = tab === 'home' ? 'block' : 'none';
  document.getElementById('logPanelsSection').style.display = tab === 'log' ? 'block' : 'none';

  const tabs = { tabHome: 'home', tabGrafiek: 'log', tabHoogtepunten: 'hoogtepunten', tabRuweData: 'ruwedata' };''',
    '''  document.getElementById('homeTilesSection').style.display = tab === 'home' ? 'block' : 'none';

  const tabs = { tabHome: 'home', tabHoogtepunten: 'hoogtepunten', tabRuweData: 'ruwedata' };''',
    "showTab tabs map + logPanelsSection line"
)

# 4. closeLogModal(): no more 'log' tab to stay open on — always hide.
patch(
    '''  document.body.style.overflow = '';
  if (currentTab !== 'log') panel.style.display = 'none';
}''',
    '''  document.body.style.overflow = '';
  panel.style.display = 'none';
}''',
    "closeLogModal always hide"
)

# 5. Table header: 8 columns -> 5 (Tijd, Type, Entry, Tags, chevron).
patch(
    '''      <colgroup>
        <col style="width:7%">
        <col style="width:20%">
        <col style="width:6%">
        <col style="width:10%">
        <col style="width:26%">
        <col style="width:11%">
        <col style="width:14%">
        <col style="width:6%">
      </colgroup>
      <thead>
        <tr style="text-align:left; border-bottom:0.5px solid rgba(255,255,255,0.10); color:#8a8a86;">
          <th style="padding:10px 12px; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Tijd</th>
          <th style="padding:10px 12px; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Beschrijving</th>
          <th style="padding:10px 12px; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Aantal</th>
          <th style="padding:10px 12px; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Type</th>
          <th style="padding:10px 12px; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Context</th>
          <th style="padding:10px 12px; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Tags</th>
          <th style="padding:10px 12px; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Gekoppeld</th>
          <th style="padding:10px 12px;"></th>
        </tr>
      </thead>''',
    '''      <colgroup>
        <col style="width:9%">
        <col style="width:16%">
        <col style="width:1fr">
        <col style="width:16%">
        <col style="width:6%">
      </colgroup>
      <thead>
        <tr style="text-align:left; border-bottom:0.5px solid rgba(255,255,255,0.10); color:#8a8a86;">
          <th style="padding:9px 14px; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:0.4px;">Tijd</th>
          <th style="padding:9px 14px; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:0.4px;">Type</th>
          <th style="padding:9px 14px; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:0.4px;">Entry</th>
          <th style="padding:9px 14px; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:0.4px;">Tags</th>
          <th style="padding:9px 14px;"></th>
        </tr>
      </thead>''',
    "table header 8->5 cols"
)

# 6. Row-building JS: merge Beschrijving/Aantal/Context/Gekoppeld into one Entry column.
patch(
    '''  rows.forEach(r => {
    const tr = document.createElement('tr');
    tr.id = 'rdRow-' + r.id;
    tr.className = 'rdRowClickable';
    tr.style.borderBottom = '0.5px solid rgba(255,255,255,0.07)';
    tr.onclick = () => openRdModal(r.id);
    const accent = typeAccent(r.type);
    const typeLabel =
      '<div style="display:flex; align-items:center; gap:7px;">' +
        '<div style="width:20px; height:20px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:' + accent.bg + '; flex-shrink:0;">' + accent.icon + '</div>' +
        '<span>' + r.type + (r.bolusType ? ' (' + r.bolusType + ')' : '') + '</span>' +
      '</div>';
    const contextLabel = (r.type === 'bolus' && r.bgAtEntry != null)
      ? (bgPillHtml(r.bgAtEntry) + (r.context ? ' <span style="color:#8a8a86;">' + r.context + '</span>' : ''))
      : (r.type === 'khd' && r.absorptionScore != null)
        ? (absorptionPillHtml(r.absorptionScore) + (r.context ? ' <span style="color:#8a8a86;">' + r.context + '</span>' : ''))
        : (r.context ? '<span style="color:#8a8a86;">' + r.context + '</span>' : '');
    const tagChips = r.tags ? r.tags.split(/[,;]/).map(t => t.trim()).filter(Boolean).map(t => '<span class="rdChip tag">' + t + '</span>').join('') : '';
    const linkChips = r.links.length ? r.links.map(l => '<span class="rdChip link">&#8596; ' + (l.desc||l.type) + '</span>').join('') : '<span style="color:#75746f;">–</span>';
    tr.innerHTML =
      '<td data-label="Tijd" class="rd-time" style="padding:9px 12px; white-space:nowrap; color:#b7b7b2; font-size:12px;">' + fmtDayTime(r.ts) + '</td>' +
      '<td data-label="Beschrijving" class="rd-desc" style="padding:9px 12px; word-wrap:break-word; font-weight:500;">' + (r.desc||'') + '</td>' +
      '<td data-label="Aantal" class="rd-amount" style="padding:9px 12px;">' + (r.amount !== '' && r.amount != null ? r.amount : '') + '</td>' +
      '<td data-label="Type" class="rd-type" style="padding:9px 12px;">' + typeLabel + '</td>' +
      '<td data-label="Context" class="rd-context" style="padding:9px 12px; word-wrap:break-word; font-size:12px;">' + contextLabel + '</td>' +
      '<td data-label="Tags" class="rd-tags" style="padding:9px 12px; word-wrap:break-word;"><div class="rdChips" style="margin-top:0;">' + tagChips + '</div></td>' +
      '<td data-label="Gekoppeld" class="rd-links" style="padding:9px 12px; word-wrap:break-word;"><div class="rdChips" style="margin-top:0;">' + linkChips + '</div></td>' +
      '<td style="padding:9px 12px; color:#75746f;">' + ICON_CHEVRON + '</td>';
    body.appendChild(tr);
  });''',
    '''  rows.forEach((r, idx) => {
    const tr = document.createElement('tr');
    tr.id = 'rdRow-' + r.id;
    tr.className = 'rdRowClickable';
    tr.style.borderBottom = '0.5px solid rgba(255,255,255,0.06)';
    tr.style.background = (idx % 2 === 1) ? 'rgba(255,255,255,0.015)' : 'transparent';
    tr.onclick = () => openRdModal(r.id);
    const accent = typeAccent(r.type);
    const typeLabel =
      '<div style="display:flex; align-items:center; gap:6px;">' +
        '<span style="width:16px; height:16px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:' + accent.bg + '; flex-shrink:0;">' + accent.icon + '</span>' +
        '<span style="font-size:12px; color:#b7b7b2;">' + r.type.charAt(0).toUpperCase() + r.type.slice(1) + '</span>' +
      '</div>';
    const title = rdPrimaryLine(r);
    const metaParts = [];
    if (r.type === 'bolus' && r.bolusType) metaParts.push('<span style="color:#75746f;">' + r.bolusType + '</span>');
    if (r.type === 'bolus' && r.bgAtEntry != null) metaParts.push(bgPillHtml(r.bgAtEntry));
    if (r.type === 'khd' && r.absorptionScore != null) metaParts.push(absorptionPillHtml(r.absorptionScore));
    if (r.context) metaParts.push('<span style="color:#75746f;">' + r.context + '</span>');
    if (r.links.length) r.links.forEach(l => metaParts.push('<span style="color:#75746f;">&#8596; ' + (l.desc||l.type) + '</span>'));
    const metaLine = metaParts.length ? '<div style="display:flex; align-items:center; gap:6px; margin-top:3px; font-size:11px; flex-wrap:wrap;">' + metaParts.join('') + '</div>' : '';
    const tagChips = r.tags ? r.tags.split(/[,;]/).map(t => t.trim()).filter(Boolean).map(t => '<span class="rdChip tag">' + t + '</span>').join('') : '';
    tr.innerHTML =
      '<td data-label="Tijd" class="rd-time" style="padding:11px 14px; white-space:nowrap; color:#8a8a86; font-size:12px; vertical-align:middle;">' + fmtDayTime(r.ts) + '</td>' +
      '<td data-label="Type" class="rd-type" style="padding:11px 14px; vertical-align:middle;">' + typeLabel + '</td>' +
      '<td data-label="Entry" class="rd-desc" style="padding:11px 14px; word-wrap:break-word; vertical-align:middle;"><div style="font-size:14px; font-weight:600; color:#e4e4e0;">' + title + '</div>' + metaLine + '</td>' +
      '<td data-label="Tags" class="rd-tags" style="padding:11px 14px; word-wrap:break-word; vertical-align:middle;"><div class="rdChips" style="margin-top:0;">' + tagChips + '</div></td>' +
      '<td style="padding:11px 14px; color:#5f5e5a; vertical-align:middle;">' + ICON_CHEVRON + '</td>';
    body.appendChild(tr);
  });''',
    "row building -> merged Entry column"
)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Logboek redesign + Log-tab removal patch applied successfully.")
