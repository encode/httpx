# Environment Variables

The HTTPX library can be configured via environment variables.

Here is a list of environment variables that HTTPX recognizes and what function they serve:

- `SSLKEYLOGFILE`: Save ssl keys into specified file. See more in [SSL docs](advanced/ssl.md#sslkeylogfile).
- `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`: set the proxy to be used for http, https, or all requests respectively. See more in [Transports docs](advanced/transports.md#environment-variables).
- `NO_PROXY`: disables the proxy for specific urls. See more in [Transports docs](advanced/transports.md#environment-variables).
