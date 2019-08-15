import os

import pytest

from httpx.utils import get_netrc_login, guess_json_utf


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


def test_bad_get_netrc_login():
    assert get_netrc_login("url") is None

    os.environ["NETRC"] = "tests/.netrc"
    assert get_netrc_login("url") is None

    os.environ["NETRC"] = "wrongpath"
    assert get_netrc_login("url") is None

    from httpx import utils

    utils.NETRC_STATIC_FILES = ()
    os.environ["NETRC"] = ""
    assert utils.get_netrc_login("url") is None


def test_get_netrc_login():
    os.environ["NETRC"] = "tests/.netrc"
    assert get_netrc_login("netrcexample.org") == (
        "example-username",
        None,
        "example-password",
    )
