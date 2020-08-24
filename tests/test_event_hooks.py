from httpx._config import EventHooks


def callable():
    pass  # pragma: nocover


def test_event_hooks_init():
    # Empty init

    e = EventHooks()
    assert dict(e) == {"request": [], "auth": [], "redirect": [], "response": []}

    # Init from args

    e = EventHooks({"request": callable})
    assert dict(e) == {
        "request": [callable],
        "auth": [],
        "redirect": [],
        "response": [],
    }

    e = EventHooks({"request": [callable]})
    assert dict(e) == {
        "request": [callable],
        "auth": [],
        "redirect": [],
        "response": [],
    }

    e = EventHooks({"request": [callable, callable]})
    assert dict(e) == {
        "request": [callable, callable],
        "auth": [],
        "redirect": [],
        "response": [],
    }

    # Init from kwargs

    e = EventHooks(request=callable)
    assert dict(e) == {
        "request": [callable],
        "auth": [],
        "redirect": [],
        "response": [],
    }

    e = EventHooks(request=[callable])
    assert dict(e) == {
        "request": [callable],
        "auth": [],
        "redirect": [],
        "response": [],
    }

    e = EventHooks(request=[callable, callable])
    assert dict(e) == {
        "request": [callable, callable],
        "auth": [],
        "redirect": [],
        "response": [],
    }


def test_del_event_hooks():
    e = EventHooks({"request": callable})
    del e["request"]
    assert dict(e) == {
        "request": [],
        "auth": [],
        "redirect": [],
        "response": [],
    }


def test_set_event_hooks():
    e = EventHooks()

    e["request"] = callable
    e["redirect"] = [callable]
    e["response"] = [callable, callable]
    assert dict(e) == {
        "request": [callable],
        "auth": [],
        "redirect": [callable],
        "response": [callable, callable],
    }


def test_event_hooks_basics():
    e = EventHooks(request=callable, response=callable)
    assert len(e) == 4
    assert str(e) == (
        "{"
        f"'request': [{callable!r}], "
        "'auth': [], "
        "'redirect': [], "
        f"'response': [{callable!r}]"
        "}"
    )
    assert repr(e) == (
        "EventHooks({"
        f"'request': [{callable!r}], "
        "'auth': [], "
        "'redirect': [], "
        f"'response': [{callable!r}]"
        "})"
    )
