"""Import smoke: the stdlib-only core modules load, so a bare `pytest` on main collects something."""
import importlib

import pytest

MODULES = ["consent", "constitution", "knowledge", "mcp", "privacy", "service_auth", "service_client", "warden"]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module(f"leadfuel_core.{name}")
