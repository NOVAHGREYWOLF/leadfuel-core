"""Plugin (loaded by pytest.ini with -p, because conftest hooks do not run for the root itself). The repo root is itself the `leadfuel_core` package (see pyproject.toml), so its __init__.py
uses relative imports and cannot be imported as a top-level module. Without this hook pytest
treats the root as a Package and fails every test's setup importing it."""
import pytest


def pytest_collect_directory(path, parent):
    if path == parent.config.rootpath:
        return pytest.Dir.from_parent(parent, path=path)
