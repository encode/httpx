import typing

from ._client import Client
from ._content import Content
from ._headers import Headers
from ._streams import Stream
from ._urls import URL


__all__ = ['get', 'post', 'put', 'patch', 'delete']


def get(
    url: URL | str,
    headers: Headers | typing.Mapping[str, str] | None = None,
):
    with Client() as client:
        return client.request("GET", url=url, headers=headers)

def post(
    url: URL | str,
    headers: Headers | typing.Mapping[str, str] | None = None,
    content: Content | Stream | bytes | None = None,
):
    with Client() as client:
        return client.request("POST", url, headers=headers, content=content)

def put(
    url: URL | str,
    headers: Headers | typing.Mapping[str, str] | None = None,
    content: Content | Stream | bytes | None = None,
):
    with Client() as client:
        return client.request("PUT", url, headers=headers, content=content)

def patch(
    url: URL | str,
    headers: Headers | typing.Mapping[str, str] | None = None,
    content: Content | Stream | bytes | None = None,
):
    with Client() as client:
        return client.request("PATCH", url, headers=headers, content=content)

def delete(
    url: URL | str,
    headers: Headers | typing.Mapping[str, str] | None = None,
):
    with Client() as client:
        return client.request("DELETE", url=url, headers=headers)
