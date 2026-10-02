"""Plain helpers for the leadfuel-way tests: constants, transcript builders. Fixtures live in conftest.py.

Test modules import this as `kit`; conftest.py puts this folder on sys.path first, so it works in
pytest's `importlib` import mode too (which the repo needs: see pyproject.toml).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
HOOK_PATH = PLUGIN / "hooks" / "way_hook.py"

OPUS = "claude-opus-5-5"
SONNET = "claude-sonnet-5-5"
HAIKU = "claude-haiku-4-5-20251001"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def assistant(tokens: int, model: str = SONNET, sidechain: bool = False, content=None) -> dict:
    return {
        "type": "assistant",
        "isSidechain": sidechain,
        "message": {
            "model": model,
            "usage": {"input_tokens": tokens, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
            "content": content if content is not None else [{"type": "text", "text": "ok"}],
        },
    }


def tool_use(name: str, **inp) -> dict:
    return assistant(1, content=[{"type": "tool_use", "id": "t1", "name": name, "input": inp}])


def title_rec(title: str) -> dict:
    return {"type": "custom-title", "customTitle": title}


class Transcript:
    """A transcript file that grows, like the real one."""

    def __init__(self, path: Path):
        self.path = path
        path.write_bytes(b"")

    def add(self, *recs: dict) -> int:
        with self.path.open("ab") as fh:
            for rec in recs:
                fh.write((json.dumps(rec) + "\n").encode("utf-8"))
        return self.size

    @property
    def size(self) -> int:
        return self.path.stat().st_size


def event(name: str, transcript: Transcript, **extra) -> dict:
    return {"hook_event_name": name, "session_id": "sess-1", "transcript_path": str(transcript.path), **extra}
