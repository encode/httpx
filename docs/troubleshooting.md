# Troubleshooting

This page lists some common problems or issues you could encounter while developing with HTTPX, as well as possible solutions.

## Proxies

---

### "`The handshake operation timed out`" on HTTPS requests when using a proxy

**Description**: When using a proxy and making an HTTPS request, you see an exception looking like this:

```console
httpx.ProxyError: _ssl.c:1091: The handshake operation timed out
```

**Similar issues**: [encode/httpx#1412](https://github.com/encode/httpx/issues/1412), [encode/httpx#1433](https://github.com/encode/httpx/issues/1433)

**Resolution**: it is likely that you've set up your proxies like this...

```python
proxies = {
  "http": "http://myproxy.org",
  "https": "https://myproxy.org",
}
```

Using this setup, you're telling HTTPX to connect to the proxy using HTTP for HTTP requests, and using HTTPS for HTTPS requests.

But if you get the error above, it is likely that your proxy doesn't support connecting via HTTPS. Don't worry: that's a [common gotcha](advanced.md#example).

Change the scheme of your HTTPS proxy to `http://...` instead of `https://...`:

```python
proxies = {
  "http": "http://myproxy.org",
  "https": "http://myproxy.org",
}
```

This can be simplified to:

```python
proxies = "http://myproxy.org"
```

For more information, see [Proxies: FORWARD vs TUNNEL](advanced.md#forward-vs-tunnel).

---

### Error when making requests to an HTTPS proxy

**Description**: your proxy _does_ support connecting via HTTPS, but you are seeing errors along the lines of...

```console
httpx.ProxyError: [SSL: PRE_MAC_LENGTH_TOO_LONG] invalid alert (_ssl.c:1091)
```

**Similar issues**: [encode/httpx#1424](https://github.com/encode/httpx/issues/1424).

**Resolution**: HTTPX does not properly support HTTPS proxies at this time. If that's something you're interested in having, please see [encode/httpx#1434](https://github.com/encode/httpx/issues/1434) and consider lending a hand there.
