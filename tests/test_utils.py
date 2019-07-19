import pytest

from http3.utils import guess_json_utf


@pytest.mark.parametrize(
    "encoding",
    (
        "utf-32",
        "utf-8-sig",
        "utf-16",
        "utf-8",
        "utf-16-be",
        "utf-16-le",
        "utf-32-be",
        "utf-32-le",
    ),
)
def test_encoded(encoding):
    data = "{}".encode(encoding)
    assert guess_json_utf(data) == encoding


def test_bad_utf_like_encoding():
    assert guess_json_utf(b"\x00\x00\x00\x00") is None


@pytest.mark.parametrize(
    ("encoding", "expected"),
    (
        ("utf-16-be", "utf-16"),
        ("utf-16-le", "utf-16"),
        ("utf-32-be", "utf-32"),
        ("utf-32-le", "utf-32"),
    ),
)
def test_guess_by_bom(encoding, expected):
    data = "\ufeff{}".encode(encoding)
    assert guess_json_utf(data) == expected
