path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Locate start of the block (logModalBackdrop div)
start = next(i for i, l in enumerate(lines) if 'id="logModalBackdrop"' in l)
assert lines[start].strip().startswith('<div id="logModalBackdrop"'), \
    f"Unexpected content at start line {start}: {lines[start]!r}"

# Locate end of the block: the closing </div> for logPanelsSection,
# which is the line right before viewGrafiek's own closing </div>
# (a bare "</div>" line with no leading spaces).
end = None
for i in range(start, len(lines)):
    if lines[i].rstrip('\n') == '</div>':
        end = i - 1  # last line of the block is the one just before this
        break
assert end is not None, "Could not find viewGrafiek closing </div>"
assert lines[end].strip() == '</div>', f"Unexpected end line {end}: {lines[end]!r}"

# viewgrafiek_close is the bare </div> line itself
viewgrafiek_close = end + 1
assert lines[viewgrafiek_close].rstrip('\n') == '</div>'

block = lines[start:end+1]  # the logModalBackdrop + logPanelsSection block

# Remove the block from its current (nested, wrong) position
new_lines = lines[:start] + lines[end+1:]

# Recompute the viewGrafiek closing div's new index after removal
shift = end + 1 - start  # number of lines removed
new_viewgrafiek_close = viewgrafiek_close - shift
assert new_lines[new_viewgrafiek_close].rstrip('\n') == '</div>', \
    f"Sanity check failed at {new_viewgrafiek_close}: {new_lines[new_viewgrafiek_close]!r}"

# Re-insert the block right after viewGrafiek's closing </div> (plus a blank line for spacing)
insert_at = new_viewgrafiek_close + 1
new_lines = new_lines[:insert_at] + ['\n'] + block + new_lines[insert_at:]

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Moved logModalBackdrop + logPanelsSection outside of #viewGrafiek.")
