import re
from typing import Any

SCRIPT_LINE_PATTERN = re.compile(r"^([ABab])[：:]\s*(.+)$")

def parse_script_from_text(text: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for raw in text.strip().splitlines():
        line = raw.strip()
        if not line:
            continue
        match = SCRIPT_LINE_PATTERN.match(line)
        if not match:
            continue
        role = match.group(1).strip().upper()
        content = match.group(2).strip()
        if content:
            result.append({"role": role, "text": content})
    return result

def parse_script_with_fallback(text: str) -> list[dict[str, str]]:
    parsed = parse_script_from_text(text)
    if len(parsed) >= 2:
        return parsed

    candidates = [line.strip() for line in text.splitlines() if line.strip()]
    if len(candidates) < 2:
        blocks = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
        candidates = blocks

    fallback: list[dict[str, str]] = []
    for idx, line in enumerate(candidates):
        role = "A" if idx % 2 == 0 else "B"
        fallback.append({"role": role, "text": line})
    return fallback

def normalize_script_lines(script_lines: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in script_lines:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "A")).strip().upper()[:1] or "A"
        if role not in {"A", "B"}:
            role = "A"
        text = str(item.get("text", item.get("content", ""))).strip()
        if not text:
            continue
        normalized.append({"role": role, "text": text})
    return normalized
