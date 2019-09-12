"""Test compatibility with the Requests high-level API."""
import pytest

import requests


@pytest.mark.copied_from(
    "https://github.com/psf/requests/blob/v2.22.0/tests/test_requests.py#L61-L70"
)
def test_entrypoints():
    requests.session
    requests.session().get
    requests.session().head
    requests.get
    requests.head
    requests.put
    requests.patch
    requests.post


@pytest.mark.copied_from(
    "https://github.com/psf/requests/blob/v2.22.0/tests/test_requests.py#L72",
    changes=["added noqa comment to silence flake8"],
)
@pytest.mark.xfail(
    reason="PoolManager has no obvious equivalent in HTTPX", raises=ImportError
)
def test_poolmanager_entrypoint():
    # Not really an entry point, but people rely on it.
    from requests.packages.urllib3.poolmanager import PoolManager  # noqa: F401
