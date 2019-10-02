# Requests Compatibility Guide

HTTPX aims to be compatible with the `requests` API wherever possible.

This documentation outlines places where the API differs...

## QuickStart

Pretty much any API mentioned in the `requests` QuickStart should be identical
to the API in our own documentation. The following exceptions apply:

* `Response.url` - Returns a `URL` instance, rather than a string. Use `str(response.url)` if you need a string instance.
* `httpx.codes` - In our documentation we prefer the uppercased versions, such as `codes.NOT_FOUND`,
but also provide lower-cased versions for API compatibility with `requests`.
* `stream=True`. - Streaming responses provide the `.stream()` and `.raw()` byte iterator interfaces, rather than the `.iter_content()` method and the `.raw` socket interface.

## Advanced Usage

!!! warning
    TODO
