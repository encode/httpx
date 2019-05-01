Client(...)

    .request(method, url, ...)

    .get(url, ...)
    .options(url, ...)
    .head(url, ...)
    .post(url, ...)
    .put(url, ...)
    .patch(url, ...)
    .delete(url, ...)

    .prepare_request(request)
    .send(request, ...)
    .close()


Adapter()

    .prepare_request(request)
    .send(request)
    .close()


+ EnvironmentAdapter
+ RedirectAdapter
+ CookieAdapter
+ AuthAdapter
+ ConnectionPool
  + HTTPConnection
    + HTTP11Connection
    + HTTP2Connection



Response(...)
    .status_code    - int
    .reason_phrase  - str
    .protocol       - "HTTP/2" or "HTTP/1.1"
    .url            - URL
    .headers        - Headers

    .content        - bytes
    .text           - str
    .encoding       - str
    .json()         - Any

    .read()         - bytes
    .stream()       - bytes iterator
    .raw()          - bytes iterator
    .close()        - None

    .is_redirect    - bool
    .request        - Request
    .cookies        - Cookies
    .history        - List[Response]

    .raise_for_status()
    .next()


Request(...)
    .method
    .url
    .headers

    ...


Headers

URL

Origin

Cookies


# Sync

SyncClient
SyncResponse
SyncRequest
SyncAdapter



SSE
HTTP/2 server push support
Concurrency
