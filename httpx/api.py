import typing

from .client import Client
from .config import CertTypes, TimeoutTypes, VerifyTypes
from .models import (
    AuthTypes,
    CookieTypes,
    HeaderTypes,
    ProxiesTypes,
    QueryParamTypes,
    RequestData,
    RequestFiles,
    Response,
    URLTypes,
)


def request(
    method: str,
    url: URLTypes,
    *,
    params: QueryParamTypes = None,
    data: RequestData = None,
    files: RequestFiles = None,
    json: typing.Any = None,
    headers: HeaderTypes = None,
    cookies: CookieTypes = None,
    auth: AuthTypes = None,
    timeout: TimeoutTypes = None,
    allow_redirects: bool = True,
    cert: CertTypes = None,
    verify: VerifyTypes = True,
    stream: bool = False,
    trust_env: bool = None,
    proxies: ProxiesTypes = None,
) -> Response:
    """
    Constructs and sends a `Request`.

    **Parameters:**

    * **method** - HTTP method for the new `Request` object: `GET`, `OPTIONS`,
    `HEAD`, `POST`, `PUT`, `PATCH`, or `DELETE`.
    * **url** - URL for the new `Request` object.
    * **params** - *(optional)* Query parameters to include in the URL, as a
    string, dictionary, or list of two-tuples.
    * **data** - *(optional)* Data to include in the body of the request, as a
    dictionary
    * **files** - *(optional)* A dictionary of upload files to include in the
    body of the request.
    * **json** - *(optional)* A JSON serializable object to include in the body
    of the request.
    * **headers** - *(optional)* Dictionary of HTTP headers to include on the
    request.
    * **cookies** - *(optional)* Dictionary of Cookie items to include in the
    request.
    * **auth** - *(optional)* An authentication class to use when sending the
    request.
    * **timeout** - *(optional)* The timeout configuration to use when sending
    the request.
    * **allow_redirects** - *(optional)* Enables or disables HTTP redirects.
    * **cert** - *(optional)* Either a path to an SSL certificate file, or
    two-tuple of (certificate file, key file), or a three-tuple of (certificate
    file, key file, password).
    * **verify** - *(optional)* Enables or disables SSL verification.
    * **trust_env** - *(optional)* Enables or disables usage of environment
    variables for configuration.
    * **proxies** - *(optional)* A dictionary mapping HTTP protocols to proxy
    URLs.

    **Returns:** `Response`

    Usage:

    ```
    >>> import httpx
    >>> response = httpx.request('GET', 'https://httpbin.org/get')
    >>> response
    <Response [200 OK]>
    ```
    """
    with Client(http_versions=["HTTP/1.1"]) as client:
        return client.request(
            method=method,
            url=url,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            cert=cert,
            verify=verify,
            timeout=timeout,
            trust_env=trust_env,
        )


def get(
    url: URLTypes,
    *,
    params: QueryParamTypes = None,
    headers: HeaderTypes = None,
    cookies: CookieTypes = None,
    stream: bool = False,
    auth: AuthTypes = None,
    allow_redirects: bool = True,
    cert: CertTypes = None,
    verify: VerifyTypes = True,
    timeout: TimeoutTypes = None,
    trust_env: bool = None,
    proxies: ProxiesTypes = None,
) -> Response:
    return request(
        "GET",
        url,
        params=params,
        headers=headers,
        cookies=cookies,
        stream=stream,
        auth=auth,
        allow_redirects=allow_redirects,
        cert=cert,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )


def options(
    url: URLTypes,
    *,
    params: QueryParamTypes = None,
    headers: HeaderTypes = None,
    cookies: CookieTypes = None,
    stream: bool = False,
    auth: AuthTypes = None,
    allow_redirects: bool = True,
    cert: CertTypes = None,
    verify: VerifyTypes = True,
    timeout: TimeoutTypes = None,
    trust_env: bool = None,
    proxies: ProxiesTypes = None,
) -> Response:
    return request(
        "OPTIONS",
        url,
        params=params,
        headers=headers,
        cookies=cookies,
        stream=stream,
        auth=auth,
        allow_redirects=allow_redirects,
        cert=cert,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )


def head(
    url: URLTypes,
    *,
    params: QueryParamTypes = None,
    headers: HeaderTypes = None,
    cookies: CookieTypes = None,
    stream: bool = False,
    auth: AuthTypes = None,
    allow_redirects: bool = False,  #  Note: Differs to usual default.
    cert: CertTypes = None,
    verify: VerifyTypes = True,
    timeout: TimeoutTypes = None,
    trust_env: bool = None,
    proxies: ProxiesTypes = None,
) -> Response:
    return request(
        "HEAD",
        url,
        params=params,
        headers=headers,
        cookies=cookies,
        stream=stream,
        auth=auth,
        allow_redirects=allow_redirects,
        cert=cert,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )


def post(
    url: URLTypes,
    *,
    data: RequestData = None,
    files: RequestFiles = None,
    json: typing.Any = None,
    params: QueryParamTypes = None,
    headers: HeaderTypes = None,
    cookies: CookieTypes = None,
    stream: bool = False,
    auth: AuthTypes = None,
    allow_redirects: bool = True,
    cert: CertTypes = None,
    verify: VerifyTypes = True,
    timeout: TimeoutTypes = None,
    trust_env: bool = None,
    proxies: ProxiesTypes = None,
) -> Response:
    return request(
        "POST",
        url,
        data=data,
        files=files,
        json=json,
        params=params,
        headers=headers,
        cookies=cookies,
        stream=stream,
        auth=auth,
        allow_redirects=allow_redirects,
        cert=cert,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )


def put(
    url: URLTypes,
    *,
    data: RequestData = None,
    files: RequestFiles = None,
    json: typing.Any = None,
    params: QueryParamTypes = None,
    headers: HeaderTypes = None,
    cookies: CookieTypes = None,
    stream: bool = False,
    auth: AuthTypes = None,
    allow_redirects: bool = True,
    cert: CertTypes = None,
    verify: VerifyTypes = True,
    timeout: TimeoutTypes = None,
    trust_env: bool = None,
    proxies: ProxiesTypes = None,
) -> Response:
    return request(
        "PUT",
        url,
        data=data,
        files=files,
        json=json,
        params=params,
        headers=headers,
        cookies=cookies,
        stream=stream,
        auth=auth,
        allow_redirects=allow_redirects,
        cert=cert,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )


def patch(
    url: URLTypes,
    *,
    data: RequestData = None,
    files: RequestFiles = None,
    json: typing.Any = None,
    params: QueryParamTypes = None,
    headers: HeaderTypes = None,
    cookies: CookieTypes = None,
    stream: bool = False,
    auth: AuthTypes = None,
    allow_redirects: bool = True,
    cert: CertTypes = None,
    verify: VerifyTypes = True,
    timeout: TimeoutTypes = None,
    trust_env: bool = None,
    proxies: ProxiesTypes = None,
) -> Response:
    return request(
        "PATCH",
        url,
        data=data,
        files=files,
        json=json,
        params=params,
        headers=headers,
        cookies=cookies,
        stream=stream,
        auth=auth,
        allow_redirects=allow_redirects,
        cert=cert,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )


def delete(
    url: URLTypes,
    *,
    params: QueryParamTypes = None,
    headers: HeaderTypes = None,
    cookies: CookieTypes = None,
    stream: bool = False,
    auth: AuthTypes = None,
    allow_redirects: bool = True,
    cert: CertTypes = None,
    verify: VerifyTypes = True,
    timeout: TimeoutTypes = None,
    trust_env: bool = None,
    proxies: ProxiesTypes = None,
) -> Response:
    return request(
        "DELETE",
        url,
        params=params,
        headers=headers,
        cookies=cookies,
        stream=stream,
        auth=auth,
        allow_redirects=allow_redirects,
        cert=cert,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )
