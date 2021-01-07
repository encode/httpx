import pytest

import httpx


@pytest.mark.parametrize(
    "source",
    [
        "a=123&a=456&b=789",
        {"a": ["123", "456"], "b": 789},
        {"a": ("123", "456"), "b": 789},
        [("a", "123"), ("a", "456"), ("b", "789")],
        (("a", "123"), ("a", "456"), ("b", "789")),
    ],
)
def test_queryparams(source):
    q = httpx.QueryParams(source)
    assert "a" in q
    assert "A" not in q
    assert "c" not in q
    assert q["a"] == "456"
    assert q.get("a") == "456"
    assert q.get("nope", default=None) is None
    assert q.get_list("a") == ["123", "456"]

    assert list(q.keys()) == ["a", "b"]
    assert list(q.values()) == ["456", "789"]
    assert list(q.items()) == [("a", "456"), ("b", "789")]
    assert len(q) == 2
    assert list(q) == ["a", "b"]
    assert dict(q) == {"a": "456", "b": "789"}
    assert str(q) == "a=123&a=456&b=789"
    assert repr(q) == "QueryParams('a=123&a=456&b=789')"
    assert httpx.QueryParams({"a": "123", "b": "456"}) == httpx.QueryParams(
        [("a", "123"), ("b", "456")]
    )
    assert httpx.QueryParams({"a": "123", "b": "456"}) == httpx.QueryParams(
        "a=123&b=456"
    )
    assert httpx.QueryParams({"a": "123", "b": "456"}) == httpx.QueryParams(
        {"b": "456", "a": "123"}
    )
    assert httpx.QueryParams() == httpx.QueryParams({})
    assert httpx.QueryParams([("a", "123"), ("a", "456")]) == httpx.QueryParams(
        "a=123&a=456"
    )
    assert httpx.QueryParams({"a": "123", "b": "456"}) != "invalid"

    q = httpx.QueryParams([("a", "123"), ("a", "456")])
    assert httpx.QueryParams(q) == q


def test_queryparam_types():
    q = httpx.QueryParams(None)
    assert str(q) == ""

    q = httpx.QueryParams({"a": True})
    assert str(q) == "a=true"

    q = httpx.QueryParams({"a": False})
    assert str(q) == "a=false"

    q = httpx.QueryParams({"a": ""})
    assert str(q) == "a="

    q = httpx.QueryParams({"a": None})
    assert str(q) == "a="

    q = httpx.QueryParams({"a": 1.23})
    assert str(q) == "a=1.23"

    q = httpx.QueryParams({"a": 123})
    assert str(q) == "a=123"

    q = httpx.QueryParams({"a": [1, 2]})
    assert str(q) == "a=1&a=2"


def test_queryparam_setters():
    q = httpx.QueryParams({"a": 1})
    q.update([])

    assert str(q) == "a=1"

    q = httpx.QueryParams([("a", 1), ("a", 2)])
    q["a"] = "3"
    assert str(q) == "a=3"

    q = httpx.QueryParams([("a", 1), ("b", 1)])
    u = httpx.QueryParams([("b", 2), ("b", 3)])
    q.update(u)

    assert str(q) == "a=1&b=2&b=3"
    assert q["b"] == u["b"]
