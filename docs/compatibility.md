# Requests Compatibility Guide

HTTP3 aims to be compatible with the `requests` API wherever possible.

This documentation outlines places where the API differs...

## QuickStart

Pretty much all the API mentioned in the `requests` QuickStart should be identical
to the API in our own documentation. The following exceptions apply:

* `Response.url` - Returns a `URL` instance, rather than a string. Use `str(response.url)` if you need a string instance.
* `Response.status_code` - Returns an integer, which may be a `StatusCode` IntEnum. This has the same behaviour as any other integer, except that it provides more information in the instance representation.
* `http3.codes` - In our documentation we prefer the uppercased versions, such as `codes.NOT_FOUND`,
but also provide lower-cased versions for API compatibility with `requests`.
* `stream=True`. - Streaming responses provide the `.stream()` and `.raw()` byte iterator interfaces, rather than the `.iter_content()` method and the `.raw` socket interface.

## Advanced Usage

!!! warning
    TODO
