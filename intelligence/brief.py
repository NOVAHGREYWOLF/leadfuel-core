"""own-5: the morning brief and the evening close, a deterministic template.

Local data in, plain text out. No model call and no network: the template is the
first build, a local model may later only rephrase its output. A section with no
data says so ("nothing recorded") rather than inventing a line, and a missing
input is never read as an empty good day.
"""
from __future__ import annotations

from typing import Mapping, Sequence

MORNING_SECTIONS = (
    ("overnight", "Overnight"),
    ("moves", "The three moves that matter"),
    ("waiting", "Waiting on you"),
)
EVENING_SECTIONS = (
    ("done", "Done"),
    ("paid", "What the game paid"),
    ("learned", "What was learned"),
    ("tomorrow", "Tried tomorrow"),
)
# Words per minute for the one spoken minute, a deliberate under-estimate.
SPOKEN_WORDS_PER_MINUTE = 140
MAX_MOVES = 3


def _items(data: Mapping[str, Sequence[str]], key: str) -> list[str]:
    raw = data.get(key)
    if not raw:
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def _render(title: str, sections, data: Mapping[str, Sequence[str]]) -> str:
    lines = [title]
    for key, heading in sections:
        items = _items(data, key)
        if key == "moves":
            items = items[:MAX_MOVES]
        lines.append("")
        lines.append(heading)
        if not items:
            lines.append("- nothing recorded")
        else:
            lines.extend(f"- {i}" for i in items)
    return "\n".join(lines) + "\n"


def morning_brief(data: Mapping[str, Sequence[str]]) -> str:
    return _render("Morning brief", MORNING_SECTIONS, data)


def evening_close(data: Mapping[str, Sequence[str]]) -> str:
    return _render("Evening close", EVENING_SECTIONS, data)


def spoken_minute(text: str) -> str:
    """Trim text to what one spoken minute holds, cutting at a line boundary."""
    budget = SPOKEN_WORDS_PER_MINUTE
    out: list[str] = []
    for line in text.splitlines():
        n = len(line.split())
        if n > budget:
            break
        budget -= n
        out.append(line)
    return "\n".join(out).strip() + "\n"
