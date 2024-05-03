# The WHATWG have various tests that can be used to validate the URL parsing.
#
# https://url.spec.whatwg.org/

import json

import pytest

from httpx._urlparse import urlparse

# URL test cases from...
# https://github.com/web-platform-tests/wpt/blob/master/url/resources/urltestdata.json
with open("tests/models/whatwg.json", "r") as input:
    test_cases = json.load(input)
    test_cases = [
        item
        for item in test_cases
        if not isinstance(item, str) and not item.get("failure")
    ]


@pytest.mark.parametrize("test_case", test_cases)
def test_urlparse(test_case):
    p = urlparse(test_case["href"])

    protocol = p.scheme + ":"
    hostname = f"[{p.host}]" if ":" in p.host else p.host
    port = "" if p.port is None else str(p.port)
    path = p.path
    search = "" if p.query in (None, "") else "?" + str(p.query)
    hash = "" if p.fragment in (None, "") else "#" + str(p.fragment)

    assert protocol == test_case["protocol"]
    assert hostname.lower() == test_case["hostname"].lower()
    assert port == test_case["port"]
    assert path == test_case["pathname"]
    assert search == test_case["search"]
    assert hash == test_case["hash"]
