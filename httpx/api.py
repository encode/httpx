import typing

from .client import Client
from .config import CertTypes, TimeoutTypes, VerifyTypes
from .models import (
    AuthTypes,
    CookieTypes,
    HeaderTypes,
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
    # files
    auth: AuthTypes = None,
    timeout: TimeoutTypes = None,
    allow_redirects: bool = True,
    # proxies
    cert: CertTypes = None,
    verify: VerifyTypes = True,
    stream: bool = False,
) -> Response:
    with Client() as client:
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
    )


def delete(
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
) -> Response:
    return request(
        "DELETE",
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
    )
