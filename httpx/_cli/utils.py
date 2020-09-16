import pygments.lexers
import pygments.util

import httpx


def get_lexer_for_response(response: httpx.Response) -> str:
    content_type = response.headers.get("Content-Type")
    if content_type is not None:
        mime_type, _, _ = content_type.partition(";")
        try:
            return pygments.lexers.get_lexer_for_mimetype(mime_type.strip()).name
        except pygments.util.ClassNotFound:  # pragma: nocover
            pass
    return ""  # pragma: nocover


def format_request_headers(request: httpx.Request) -> str:
    target = request.url.raw[-1].decode("ascii")
    lines = [f"{request.method} {target} HTTP/1.1"] + [
        f"{name}: {value}" for name, value in request.headers.items()
    ]
    return "\n".join(lines)


def format_response_headers(response: httpx.Response) -> str:
    lines = [
        f"{response.http_version} {response.status_code} {response.reason_phrase}"
    ] + [f"{name}: {value}" for name, value in response.headers.items()]
    return "\n".join(lines)
