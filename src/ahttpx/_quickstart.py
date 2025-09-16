import typing

from ._client import Client
from ._content import Content
from ._headers import Headers
from ._streams import Stream
from ._urls import URL


__all__ = ['get', 'post', 'put', 'patch', 'delete']


async def get(
    url: URL | str,
    headers: Headers | typing.Mapping[str, str] | None = None,
):
    async with Client() as client:
        return await client.request("GET", url=url, headers=headers)

async def post(
    url: URL | str,
    headers: Headers | typing.Mapping[str, str] | None = None,
    content: Content | Stream | bytes | None = None,
):
    async with Client() as client:
        return await client.request("POST", url, headers=headers, content=content)

async def put(
    url: URL | str,
    headers: Headers | typing.Mapping[str, str] | None = None,
    content: Content | Stream | bytes | None = None,
):
    async with Client() as client:
        return await client.request("PUT", url, headers=headers, content=content)

async def patch(
    url: URL | str,
    headers: Headers | typing.Mapping[str, str] | None = None,
    content: Content | Stream | bytes | None = None,
):
    async with Client() as client:
        return await client.request("PATCH", url, headers=headers, content=content)

async def delete(
    url: URL | str,
    headers: Headers | typing.Mapping[str, str] | None = None,
):
    async with Client() as client:
        return await client.request("DELETE", url=url, headers=headers)
