"""
The `httpx.MountPoints()` transport allows routing based on the request
scheme, host and port.

For instance...

# Send 'http' requests via a proxy.
transport = httpx.MountPoints({
    "http://": httpx.HTTPTransport(proxy="http://127.0.0.1:8080"),
    "https://": httpx.HTTPTransport(),
})
client = httpx.Client(transport=transport)

# Send requests to 'example.com' via a proxy.
# Matches 'example.com', does not match 'www.example.com'.
transport = httpx.MountPoints({
    "all://example.com": httpx.HTTPTransport(proxy="http://127.0.0.1:8080"),
    "all://": httpx.HTTPTransport(),
})

# Send requests to subdomains of 'example.com' via a proxy.
# Matches 'www.example.com', does not match 'example.com'.
transport = httpx.MountPoints({
    "all://*.example.com": httpx.HTTPTransport(proxy="http://127.0.0.1:8080"),
    "all://": httpx.HTTPTransport(),
})

# Send requests to 'example.com' and subdomains of 'example.com' via a proxy.
transport = httpx.MountPoints({
    "all://*example.com": httpx.HTTPTransport(proxy="http://127.0.0.1:8080"),
    "all://": httpx.HTTPTransport(),
})

# Send requests to port 1234 via a proxy.
transport = httpx.MountPoints({
    "all://*:1234": httpx.HTTPTransport(proxy="http://127.0.0.1:8080"),
    "all://": httpx.HTTPTransport(),
})


default_transport = httpx.HTTPTransport()
proxy_transport = httpx.HTTPTransport(proxy="http://127.0.0.1:8080")


transport = httpx.MountPoints(
    "all://localhost": default_transport,
    "all://127.0.0.1": default_transport,
    "all://": proxy_transport,
)
"""
from .base import AsyncBaseTransport, BaseTransport
from .._exceptions import InvalidURL
from ..models import Request, Response
from .._urls import URL

import ipaddress
import re
import typing
from urllib.request import getproxies


class MountPoints(BaseTransport, AsyncBaseTransport):
    def __init__(
        self, mounts: typing.Dict[str, typing.Union[BaseTransport, AsyncBaseTransport]]
    ) -> None:
        self._mounts = [(URLPattern(key), value) for key, value in mounts.items()]
        self._mounts = sorted(self._mounts, key=lambda x: x[0])

    def _transport_for_url(self, url: URL) -> BaseTransport:
        """
        Returns the transport instance that should be used for a given URL.
        This will either be the standard connection pool, or a proxy.
        """
        for pattern, transport in self._mounts:
            if pattern.matches(url):
                return transport

        raise InvalidURL("No transport mounted for URL '{url}'")

    def handle_request(self, request: Request) -> Response:
        transport = self._transport_for_url(request.url)
        return transport.handle_request(request)

    async def handle_async_request(self, request: Request) -> Response:
        transport = self._transport_for_url(request.url)
        return await transport.handle_async_request(request)

    def close(self) -> None:
        for _, transport in self._mounts:
            transport.close()

    async def aclose(self) -> None:
        for _, transport in self._mounts:
            await transport.aclose()


class URLPattern:
    """
    A utility class currently used for making lookups against proxy keys...

    # Wildcard matching...
    >>> pattern = URLPattern("all://")
    >>> pattern.matches(httpx.URL("http://example.com"))
    True

    # Witch scheme matching...
    >>> pattern = URLPattern("https://")
    >>> pattern.matches(httpx.URL("https://example.com"))
    True
    >>> pattern.matches(httpx.URL("http://example.com"))
    False

    # With domain matching...
    >>> pattern = URLPattern("https://example.com")
    >>> pattern.matches(httpx.URL("https://example.com"))
    True
    >>> pattern.matches(httpx.URL("http://example.com"))
    False
    >>> pattern.matches(httpx.URL("https://other.com"))
    False

    # Wildcard scheme, with domain matching...
    >>> pattern = URLPattern("all://example.com")
    >>> pattern.matches(httpx.URL("https://example.com"))
    True
    >>> pattern.matches(httpx.URL("http://example.com"))
    True
    >>> pattern.matches(httpx.URL("https://other.com"))
    False

    # With port matching...
    >>> pattern = URLPattern("https://example.com:1234")
    >>> pattern.matches(httpx.URL("https://example.com:1234"))
    True
    >>> pattern.matches(httpx.URL("https://example.com"))
    False
    """

    def __init__(self, pattern: str) -> None:
        if pattern and ":" not in pattern:
            raise ValueError(
                f"Proxy keys should use proper URL forms rather "
                f"than plain scheme strings. "
                f'Instead of "{pattern}", use "{pattern}://"'
            )

        url = URL(pattern)
        self.pattern = pattern
        self.scheme = "" if url.scheme == "all" else url.scheme
        self.host = "" if url.host == "*" else url.host
        self.port = url.port
        if not url.host or url.host == "*":
            self.host_regex: typing.Optional[typing.Pattern[str]] = None
        elif url.host.startswith("*."):
            # *.example.com should match "www.example.com", but not "example.com"
            domain = re.escape(url.host[2:])
            self.host_regex = re.compile(f"^.+\\.{domain}$")
        elif url.host.startswith("*"):
            # *example.com should match "www.example.com" and "example.com"
            domain = re.escape(url.host[1:])
            self.host_regex = re.compile(f"^(.+\\.)?{domain}$")
        else:
            # example.com should match "example.com" but not "www.example.com"
            domain = re.escape(url.host)
            self.host_regex = re.compile(f"^{domain}$")

    def matches(self, other: "URL") -> bool:
        if self.scheme and self.scheme != other.scheme:
            return False
        if (
            self.host
            and self.host_regex is not None
            and not self.host_regex.match(other.host)
        ):
            return False
        if self.port is not None and self.port != other.port:
            return False
        return True

    @property
    def priority(self) -> typing.Tuple[int, int, int]:
        """
        The priority allows URLPattern instances to be sortable, so that
        we can match from most specific to least specific.
        """
        # URLs with a port should take priority over URLs without a port.
        port_priority = 0 if self.port is not None else 1
        # Longer hostnames should match first.
        host_priority = -len(self.host)
        # Longer schemes should match first.
        scheme_priority = -len(self.scheme)
        return (port_priority, host_priority, scheme_priority)

    def __hash__(self) -> int:
        return hash(self.pattern)

    def __lt__(self, other: "URLPattern") -> bool:
        return self.priority < other.priority

    def __eq__(self, other: typing.Any) -> bool:
        return isinstance(other, URLPattern) and self.pattern == other.pattern


def get_environment_proxies() -> typing.Dict[str, typing.Optional[str]]:
    """
    Gets proxy information from the environment
    """

    # urllib.request.getproxies() falls back on System
    # Registry and Config for proxies on Windows and macOS.
    # We don't want to propagate non-HTTP proxies into
    # our configuration such as 'TRAVIS_APT_PROXY'.
    proxy_info = getproxies()
    mounts: typing.Dict[str, typing.Optional[str]] = {}

    for scheme in ("http", "https", "all"):
        if proxy_info.get(scheme):
            hostname = proxy_info[scheme]
            mounts[f"{scheme}://"] = (
                hostname if "://" in hostname else f"http://{hostname}"
            )

    no_proxy_hosts = [host.strip() for host in proxy_info.get("no", "").split(",")]
    for hostname in no_proxy_hosts:
        # See https://curl.haxx.se/libcurl/c/CURLOPT_NOPROXY.html for details
        # on how names in `NO_PROXY` are handled.
        if hostname == "*":
            # If NO_PROXY=* is used or if "*" occurs as any one of the comma
            # separated hostnames, then we should just bypass any information
            # from HTTP_PROXY, HTTPS_PROXY, ALL_PROXY, and always ignore
            # proxies.
            return {}
        elif hostname:
            # NO_PROXY=.google.com is marked as "all://*.google.com,
            #   which disables "www.google.com" but not "google.com"
            # NO_PROXY=google.com is marked as "all://*google.com,
            #   which disables "www.google.com" and "google.com".
            #   (But not "wwwgoogle.com")
            # NO_PROXY can include domains, IPv6, IPv4 addresses and "localhost"
            #   NO_PROXY=example.com,::1,localhost,192.168.0.0/16
            if is_ipv4_hostname(hostname):
                mounts[f"all://{hostname}"] = None
            elif is_ipv6_hostname(hostname):
                mounts[f"all://[{hostname}]"] = None
            elif hostname.lower() == "localhost":
                mounts[f"all://{hostname}"] = None
            else:
                mounts[f"all://*{hostname}"] = None

    return mounts


def is_ipv4_hostname(hostname: str) -> bool:
    try:
        ipaddress.IPv4Address(hostname.split("/")[0])
    except Exception:
        return False
    return True


def is_ipv6_hostname(hostname: str) -> bool:
    try:
        ipaddress.IPv6Address(hostname.split("/")[0])
    except Exception:
        return False
    return True
