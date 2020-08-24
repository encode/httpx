from httpx._config import EventHooks


def callable():
    pass  # pragma: nocover


def test_event_hooks_init():
    # Empty init

    e = EventHooks()
    assert dict(e) == {"request": [], "response": []}

    # Init from args

    e = EventHooks({"request": callable})
    assert dict(e) == {
        "request": [callable],
        "response": [],
    }

    e = EventHooks({"request": [callable]})
    assert dict(e) == {
        "request": [callable],
        "response": [],
    }

    e = EventHooks({"request": [callable, callable]})
    assert dict(e) == {
        "request": [callable, callable],
        "response": [],
    }

    # Init from kwargs

    e = EventHooks(request=callable)
    assert dict(e) == {
        "request": [callable],
        "response": [],
    }

    e = EventHooks(request=[callable])
    assert dict(e) == {
        "request": [callable],
        "response": [],
    }

    e = EventHooks(request=[callable, callable])
    assert dict(e) == {
        "request": [callable, callable],
        "response": [],
    }


def test_del_event_hooks():
    e = EventHooks({"request": callable})
    del e["request"]
    assert dict(e) == {
        "request": [],
        "response": [],
    }


def test_set_event_hooks():
    e = EventHooks()

    e["request"] = callable
    e["response"] = [callable, callable]
    assert dict(e) == {
        "request": [callable],
        "response": [callable, callable],
    }


def test_event_hooks_basics():
    e = EventHooks(request=callable, response=callable)
    assert len(e) == 2
    assert str(e) == (f"{{'request': [{callable!r}], 'response': [{callable!r}]}}")
    assert repr(e) == (
        f"EventHooks({{'request': [{callable!r}], 'response': [{callable!r}]}})"
    )
