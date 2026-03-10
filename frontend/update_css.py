"""Fix topbar wrapping, enlarge composer, tighten layout."""
css_path = r"d:\voicespirit\frontend\src\styles.css"

with open(css_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

def find_block(lines, selector):
    for i, line in enumerate(lines):
        s = line.strip()
        if s == selector + " {" or s == selector + "{" or s.startswith(selector + " {"):
            return i
    return -1

def find_block_end(lines, start_idx):
    depth = 0
    for i in range(start_idx, len(lines)):
        for ch in lines[i]:
            if ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return i
    return len(lines) - 1

def replace_range(lines, start_idx, end_idx, new_css):
    if new_css:
        new_lines = [l + "\n" for l in new_css.split("\n")]
    else:
        new_lines = []
    return lines[:start_idx] + new_lines + lines[end_idx + 1:]

# 1. Fix topbar to not wrap — make it flex properly
idx = find_block(lines, ".vsTopbar")
if idx >= 0:
    end = find_block_end(lines, idx)
    lines = replace_range(lines, idx, end, """.vsTopbar {
  height: 52px;
  border-bottom: 1px solid #eaedf5;
  background: rgba(252, 252, 254, 0.95);
  backdrop-filter: blur(10px);
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}""")
    print("[OK] .vsTopbar")

# 2. Fix .vsTopbarLeft to use flex: 1
idx = find_block(lines, ".vsTopbarLeft")
if idx >= 0:
    end = find_block_end(lines, idx)
    lines = replace_range(lines, idx, end, """.vsTopbarLeft {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
}""")
    print("[OK] .vsTopbarLeft")

# 3. Fix .vsTopbarField model input — remove min-width
idx = find_block(lines, ".vsTopbarField")
if idx >= 0:
    end = find_block_end(lines, idx)
    lines = replace_range(lines, idx, end, """.vsTopbarField {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #8e96ab;
  font-weight: 600;
  white-space: nowrap;
}

.vsTopbarField select,
.vsTopbarField input {
  border: 1px solid #e8ebf2;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 13px;
  color: #3b4255;
  background: #fff;
  outline: none;
  min-width: 0;
}

.vsTopbarField select:focus,
.vsTopbarField input:focus {
  border-color: #c4b5fd;
  box-shadow: 0 0 0 2px rgba(124, 92, 255, 0.08);
}

.vsTopbarModelField {
  flex: 1;
  min-width: 0;
}

.vsTopbarModelField input {
  width: 100%;
  min-width: 0;
}""")
    print("[OK] .vsTopbarField")

# 4. Remove vsTopbarActions, vsTopbarBtn, vsTopbarIconBtn (no longer used)
for sel in [".vsTopbarActions", ".vsTopbarBtn", ".vsTopbarBtn:hover", 
            ".vsTopbarIconBtn", ".vsTopbarIconBtn:hover"]:
    idx = find_block(lines, sel)
    if idx >= 0:
        end = find_block_end(lines, idx)
        lines = lines[:idx] + lines[end + 1:]
        # Remove trailing blank line
        if idx < len(lines) and lines[idx].strip() == "":
            lines = lines[:idx] + lines[idx + 1:]
        print(f"[DEL] {sel}")

# 5. Enlarge .vsComposer
idx = find_block(lines, ".vsComposer")
if idx >= 0:
    l = lines[idx].strip()
    if ":focus" not in l and "textarea" not in l and "Toolbar" not in l:
        end = find_block_end(lines, idx)
        lines = replace_range(lines, idx, end, """.vsComposer {
  border: 1px solid #e0e3ed;
  border-radius: 22px;
  background: #ffffff;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.04);
  padding: 16px 20px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: border-color 0.2s, box-shadow 0.2s;
}""")
        print("[OK] .vsComposer enlarged")

# 6. Fix textarea min-height
idx = find_block(lines, ".vsComposer textarea")
if idx >= 0:
    l = lines[idx].strip()
    if "::" not in l and ":focus" not in l:
        end = find_block_end(lines, idx)
        lines = replace_range(lines, idx, end, """.vsComposer textarea {
  border: 0;
  background: transparent;
  padding: 2px 4px;
  min-height: 52px;
  max-height: 240px;
  resize: none;
  box-shadow: none;
  line-height: 1.6;
  color: #1e2330;
  font-size: 15px;
  outline: none;
}""")
        print("[OK] .vsComposer textarea enlarged")

# 7. Tighten gap in .vsChatCentered
idx = find_block(lines, ".vsChatCentered")
if idx >= 0:
    end = find_block_end(lines, idx)
    lines = replace_range(lines, idx, end, """.vsChatCentered {
  width: min(680px, calc(100% - 48px));
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  animation: fadeUp 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}""")
    print("[OK] .vsChatCentered tightened")

# 8. Remove .vsModelTag (no longer used)
idx = find_block(lines, ".vsModelTag")
if idx >= 0:
    end = find_block_end(lines, idx)
    lines = lines[:idx] + lines[end + 1:]
    if idx < len(lines) and lines[idx].strip() == "":
        lines = lines[:idx] + lines[idx + 1:]
    print("[DEL] .vsModelTag")

# 9. Remove .vsTopbarDivider (keep it simple with gap)
# Actually keep it, it's a subtle visual separator

with open(css_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("\n✅ CSS cleanup applied!")
