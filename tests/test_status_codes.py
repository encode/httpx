import http3


def test_status_code_as_int():
    assert http3.codes.NOT_FOUND == 404
    assert str(http3.codes.NOT_FOUND) == "404"


def test_lowercase_status_code():
    assert http3.codes.not_found == 404


def test_reason_phrase_for_status_code():
    assert http3.codes.get_reason_phrase(404) == "Not Found"


def test_reason_phrase_for_unknown_status_code():
    assert http3.codes.get_reason_phrase(499) == ""
