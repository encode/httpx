from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import pytest

import httpx
import httpx._client as client_module


def test_retry_after_503():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503 if attempts == 1 else 200)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, max_retries=1) as client:
        response = client.get("https://example.com")

    assert response.status_code == 200
    assert attempts == 2


@pytest.mark.anyio
async def test_async_retry_after_503():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503 if attempts == 1 else 200)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, max_retries=1) as client:
        response = await client.get("https://example.com")

    assert response.status_code == 200
    assert attempts == 2


def test_retry_after_seconds(monkeypatch):
    attempts = 0
    delays = []

    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        return httpx.Response(200)

    monkeypatch.setattr(client_module.time, "sleep", delays.append)
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, max_retries=1) as client:
        response = client.get("https://example.com")

    assert response.status_code == 200
    assert delays == [3.0]


def test_retry_after_http_date(monkeypatch):
    attempts = 0
    delays = []

    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            return httpx.Response(
                429,
                headers={"Retry-After": format_datetime(retry_at, usegmt=True)},
            )
        return httpx.Response(200)

    monkeypatch.setattr(client_module.time, "sleep", delays.append)
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, max_retries=1) as client:
        response = client.get("https://example.com")

    assert response.status_code == 200
    assert attempts == 2
    assert len(delays) == 1
    assert 28 <= delays[0] <= 30


def test_exponential_backoff_uses_jitter(monkeypatch):
    attempts = 0
    bounds = []
    delays = []

    def uniform(low, high):
        bounds.append((low, high))
        return high

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(200 if attempts == 3 else 503)

    monkeypatch.setattr(client_module.random, "uniform", uniform)
    monkeypatch.setattr(client_module.time, "sleep", delays.append)
    transport = httpx.MockTransport(handler)
    with httpx.Client(
        transport=transport, max_retries=2, retry_backoff_base=0.25
    ) as client:
        response = client.get("https://example.com")

    assert response.status_code == 200
    assert bounds == [(0.0, 0.25), (0.0, 0.5)]
    assert delays == [0.25, 0.5]


@pytest.mark.anyio
async def test_async_retry_after_http_date(monkeypatch):
    attempts = 0
    delays = []

    async def sleep(delay):
        delays.append(delay)

    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            return httpx.Response(
                503,
                headers={"Retry-After": format_datetime(retry_at, usegmt=True)},
            )
        return httpx.Response(200)

    monkeypatch.setattr(client_module.anyio, "sleep", sleep)
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, max_retries=1) as client:
        response = await client.get("https://example.com")

    assert response.status_code == 200
    assert len(delays) == 1
    assert 28 <= delays[0] <= 30


def test_post_is_not_retried():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, max_retries=2) as client:
        response = client.post("https://example.com")

    assert response.status_code == 503
    assert attempts == 1


def test_generator_body_is_not_retried():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    with httpx.Client(
        transport=transport,
        max_retries=2,
        retry_methods=("POST",),
    ) as client:
        response = client.post(
            "https://example.com",
            content=(part for part in [b"body"]),
        )

    assert response.status_code == 503
    assert attempts == 1


def test_retry_methods_can_include_post_and_replay_body():
    bodies = []

    def handler(request):
        bodies.append(request.content)
        return httpx.Response(503 if len(bodies) == 1 else 200)

    transport = httpx.MockTransport(handler)
    with httpx.Client(
        transport=transport,
        max_retries=1,
        retry_methods=("GET", "POST"),
        retry_backoff_base=0,
    ) as client:
        response = client.post("https://example.com", content=b"body")

    assert response.status_code == 200
    assert bodies == [b"body", b"body"]


@pytest.mark.anyio
async def test_async_post_is_not_retried():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, max_retries=2) as client:
        response = await client.post("https://example.com")

    assert response.status_code == 503
    assert attempts == 1


@pytest.mark.anyio
async def test_async_generator_body_is_not_retried():
    attempts = 0

    async def content():
        yield b"body"

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        max_retries=2,
        retry_methods=("POST",),
    ) as client:
        response = await client.post(
            "https://example.com",
            content=content(),
        )

    assert response.status_code == 503
    assert attempts == 1


@pytest.mark.anyio
async def test_async_retry_methods_can_include_post_and_replay_body():
    bodies = []

    def handler(request):
        bodies.append(request.content)
        return httpx.Response(503 if len(bodies) == 1 else 200)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        max_retries=1,
        retry_methods=("GET", "POST"),
        retry_backoff_base=0,
    ) as client:
        response = await client.post("https://example.com", content=b"body")

    assert response.status_code == 200
    assert bodies == [b"body", b"body"]


def test_retries_exhausted_returns_last_response():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    with httpx.Client(
        transport=transport, max_retries=2, retry_backoff_base=0
    ) as client:
        response = client.get("https://example.com")

    assert response.status_code == 503
    assert attempts == 3


@pytest.mark.anyio
async def test_async_retries_exhausted_returns_last_response():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport, max_retries=2, retry_backoff_base=0
    ) as client:
        response = await client.get("https://example.com")

    assert response.status_code == 503
    assert attempts == 3


def test_retries_are_disabled_by_default():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        response = client.get("https://example.com")

    assert response.status_code == 503
    assert attempts == 1
