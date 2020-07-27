import pytest

import httpx


def test_status_code_as_int():
    assert httpx.codes.NOT_FOUND == 404
    assert str(httpx.codes.NOT_FOUND) == "404"


def test_status_code_value_lookup():
    assert httpx.codes(404) == 404


def test_status_code_phrase_lookup():
    assert httpx.codes["NOT_FOUND"] == 404


def test_lowercase_status_code():
    assert httpx.codes.not_found == 404  # type: ignore


def test_reason_phrase_for_status_code():
    assert httpx.codes.get_reason_phrase(404) == "Not Found"


def test_reason_phrase_for_unknown_status_code():
    assert httpx.codes.get_reason_phrase(499) == ""


def test_deprecated_status_code_class():
    with pytest.warns(DeprecationWarning):
        assert httpx.StatusCode.NOT_FOUND == 404

    with pytest.warns(DeprecationWarning):
        assert httpx.StatusCode(404) == 404

    with pytest.warns(DeprecationWarning):
        assert httpx.StatusCode["NOT_FOUND"] == 404
