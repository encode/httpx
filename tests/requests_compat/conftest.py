import sys

import pytest

import httpx


def pytest_configure(config):
    # Allow to 'import requests' without having to write 'import httpx as requests'.
    # This means we *could* literally copy-paste Requests test code as-is, if relevant.
    sys.modules["requests"] = httpx


@pytest.fixture(autouse=True)
def patch_httpx(monkeypatch):
    """Monkey-patch Requests APIs onto HTTPX."""
    monkeypatch.setattr(httpx, "session", httpx.Client, raising=False)
