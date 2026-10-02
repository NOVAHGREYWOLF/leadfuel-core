"""Fixtures for the leadfuel-way plugin tests."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # so `import kit` works in importlib mode

import pytest  # noqa: E402

from kit import HOOK_PATH, Transcript, load_module  # noqa: E402


@pytest.fixture(scope="session")
def hook():
    return load_module(HOOK_PATH, "way_hook_under_test")


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """No test may read the owner's real state or env: state goes to tmp_path, caps are defaults."""
    for var in ("SESSION_SOFT_TOKENS", "SESSION_HARD_TOKENS", "SESSION_GUARD_OFF", "WAY_ENFORCE_ROLES"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("WAY_STATE_DIR", str(tmp_path / "state"))


@pytest.fixture
def transcript(tmp_path):
    return Transcript(tmp_path / "session.jsonl")
