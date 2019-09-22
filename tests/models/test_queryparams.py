import pytest

from httpx import QueryParams


@pytest.mark.parametrize(
    "source",
    [
        "a=123&a=456&b=789",
        {"a": ["123", "456"], "b": 789},
        {"a": ("123", "456"), "b": 789},
    ],
)
def test_queryparams(source):
    q = QueryParams(source)
    assert "a" in q
    assert "A" not in q
    assert "c" not in q
    assert q["a"] == "456"
    assert q.get("a") == "456"
    assert q.get("nope", default=None) is None
    assert q.getlist("a") == ["123", "456"]
    assert list(q.keys()) == ["a", "b"]
    assert list(q.values()) == ["456", "789"]
    assert list(q.items()) == [("a", "456"), ("b", "789")]
    assert len(q) == 2
    assert list(q) == ["a", "b"]
    assert dict(q) == {"a": "456", "b": "789"}
    assert str(q) == "a=123&a=456&b=789"
    assert repr(q) == "QueryParams('a=123&a=456&b=789')"


@pytest.mark.parametrize(
    "one, other",
    [
        [
            QueryParams({"a": "123", "b": "456"}),
            QueryParams([("a", "123"), ("b", "456")]),
        ],
        [QueryParams({"a": "123", "b": "456"}), QueryParams("a=123&b=456")],
        [QueryParams({"a": "123", "b": "456"}), QueryParams({"b": "456", "a": "123"})],
        [QueryParams(), QueryParams({})],
        [QueryParams([("a", "123"), ("a", "456")]), QueryParams("a=123&a=456")],
        [
            QueryParams([("a", "123"), ("a", "456")]),
            QueryParams(QueryParams([("a", "123"), ("a", "456")])),
        ],
    ],
)
def test_queryparams_equality(one, other):
    assert one == other


@pytest.mark.parametrize(
    "source, output",
    [
        ({"a": True}, "a=true"),
        ({"a": False}, "a=false"),
        ({"a": ""}, "a="),
        ({"a": None}, "a="),
        ({"a": 1.23}, "a=1.23"),
        ({"a": 123}, "a=123"),
        ({"a": b"123"}, "a=123"),
    ],
)
def test_queryparam_types(source, output):
    q = QueryParams(source)
    assert str(q) == output
