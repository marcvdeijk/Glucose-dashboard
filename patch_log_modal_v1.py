import re

path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

def patch(old, new, label):
    global text
    count = text.count(old)
    assert count == 1, f"[{label}] expected 1 occurrence, found {count}"
    text = text.replace(old, new, 1)

# 1. Add "Loggen" button to the Ruwe data (Logboek) toggle row.
old_toggle_row = '''    <button type="button" id="rdToggle-beweging" onclick="toggleRdType('beweging')" title="Beweging" style="width:38px; height:38px; padding:0; display:flex; align-items:center; justify-content:center; border-radius:10px; border:0.5px solid transparent; cursor:pointer; box-sizing:border-box;"><svg width="15" height="15" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8" fill="currentColor"/></svg></button>
  </div>'''
new_toggle_row = '''    <button type="button" id="rdToggle-beweging" onclick="toggleRdType('beweging')" title="Beweging" style="width:38px; height:38px; padding:0; display:flex; align-items:center; justify-content:center; border-radius:10px; border:0.5px solid transparent; cursor:pointer; box-sizing:border-box;"><svg width="15" height="15" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8" fill="currentColor"/></svg></button>
    <button type="button" id="rdLogBtn" onclick="openLogModal()" title="Nieuwe log-entry" style="margin-left:auto; height:38px; padding:0 16px; background:#7f77dd; color:#1a1730; border:none; border-radius:10px; font-weight:600; font-size:14px; cursor:pointer; display:flex; align-items:center; gap:6px;">+ Loggen</button>
  </div>'''
patch(old_toggle_row, new_toggle_row, "rd toggle row -> add Loggen button")

# 2. Add modal backdrop + close button right before logPanelsSection.
old_log_panels_open = '''  <div id="logPanelsSection" style="display:none; background:rgba(28,28,30,0.55); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); border:0.5px solid rgba(255,255,255,0.12); border-radius:20px; box-shadow:0 8px 30px rgba(0,0,0,0.25); padding:16px 18px; margin:16px 0;">
    <div style="display:flex; justify-content:space-around; align-items:center; padding-bottom:10px; margin-bottom:12px; border-bottom:1px solid #45454a;">'''
new_log_panels_open = '''  <div id="logModalBackdrop" onclick="closeLogModal()" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.55); z-index:999;"></div>
  <div id="logPanelsSection" style="display:none; background:rgba(28,28,30,0.55); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); border:0.5px solid rgba(255,255,255,0.12); border-radius:20px; box-shadow:0 8px 30px rgba(0,0,0,0.25); padding:16px 18px; margin:16px 0;">
    <div id="logModalCloseRow" style="display:none; justify-content:flex-end; margin:-4px -4px 8px 0;">
      <button type="button" onclick="closeLogModal()" style="background:transparent; border:none; color:#8a8a86; cursor:pointer; padding:4px;">''' + "&#10005;" + '''</button>
    </div>
    <div style="display:flex; justify-content:space-around; align-items:center; padding-bottom:10px; margin-bottom:12px; border-bottom:1px solid #45454a;">'''
patch(old_log_panels_open, new_log_panels_open, "logPanelsSection -> add backdrop + close row")

# 3. Track current tab + open/close modal functions inside showTab region.
old_showtab = '''function showTab(tab){
  const showShared = (tab === 'home' || tab === 'log');'''
new_showtab = '''let currentTab = 'home';

function showTab(tab){
  currentTab = tab;
  const showShared = (tab === 'home' || tab === 'log');'''
patch(old_showtab, new_showtab, "showTab -> track currentTab")

old_showtab_end = '''  if (tab === 'home') { renderHomeTiles(); renderHomeTrendChart(); renderCombinedChart(); renderIcrText(); }
}'''
new_showtab_end = '''  if (tab === 'home') { renderHomeTiles(); renderHomeTrendChart(); renderCombinedChart(); renderIcrText(); }
}

function openLogModal(){
  document.getElementById('logModalBackdrop').style.display = 'block';
  document.getElementById('logModalCloseRow').style.display = 'flex';
  const panel = document.getElementById('logPanelsSection');
  panel.style.display = 'block';
  panel.style.position = 'fixed';
  panel.style.top = '50%';
  panel.style.left = '50%';
  panel.style.transform = 'translate(-50%, -50%)';
  panel.style.width = '92%';
  panel.style.maxWidth = '480px';
  panel.style.maxHeight = '85vh';
  panel.style.overflowY = 'auto';
  panel.style.zIndex = '1000';
  document.body.style.overflow = 'hidden';
}

function closeLogModal(){
  document.getElementById('logModalBackdrop').style.display = 'none';
  document.getElementById('logModalCloseRow').style.display = 'none';
  const panel = document.getElementById('logPanelsSection');
  panel.style.position = '';
  panel.style.top = '';
  panel.style.left = '';
  panel.style.transform = '';
  panel.style.width = '';
  panel.style.maxWidth = '';
  panel.style.maxHeight = '';
  panel.style.overflowY = '';
  panel.style.zIndex = '';
  document.body.style.overflow = '';
  if (currentTab !== 'log') panel.style.display = 'none';
}'''
patch(old_showtab_end, new_showtab_end, "showTab -> add openLogModal/closeLogModal")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Patch applied successfully.")
