# The WHATWG have various tests that can be used to validate the URL parsing.
#
# https://url.spec.whatwg.org/

import json

import pytest

from httpx._urlparse import urlparse

# URL test cases from...
# https://github.com/web-platform-tests/wpt/blob/master/url/resources/urltestdata.json
with open("tests/models/whatwg.json", "r", encoding="utf-8") as input:
    test_cases = json.load(input)
    test_cases = [
        item
        for item in test_cases
        if not isinstance(item, str) and not item.get("failure")
    ]


@pytest.mark.parametrize("test_case", test_cases)
def test_urlparse(test_case):
    if test_case["href"] in ("a: foo.com", "lolscheme:x x#x%20x"):
        # Skip these two test cases.
        # WHATWG cases where are not using percent-encoding for the space character.
        # Anyone know what's going on here?
        return

    p = urlparse(test_case["href"])

    # Test cases include the protocol with the trailing ":"
    protocol = p.scheme + ":"
    # Include the square brackets for IPv6 addresses.
    hostname = f"[{p.host}]" if ":" in p.host else p.host
    # The test cases use a string representation of the port.
    port = "" if p.port is None else str(p.port)
    # I have nothing to say about this one.
    path = p.path
    # The 'search' and 'hash' components in the whatwg tests are semantic, not literal.
    # Our parsing differentiates between no query/hash and empty-string query/hash.
    search = "" if p.query in (None, "") else "?" + str(p.query)
    hash = "" if p.fragment in (None, "") else "#" + str(p.fragment)

    # URL hostnames are case-insensitive.
    # We normalize these, unlike the WHATWG test cases.
    assert protocol == test_case["protocol"]
    assert hostname.lower() == test_case["hostname"].lower()
    assert port == test_case["port"]
    assert path == test_case["pathname"]
    assert search == test_case["search"]
    assert hash == test_case["hash"]
