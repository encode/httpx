import errno
import mailbox
import mimetypes
import os

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


def filename_from_content_disposition(response: httpx.Response) -> str:
    """
    Extract and validate filename from a Content-Disposition header.

    Eg...

    Content-Disposition: attachment; filename=example.tar.gz
    """
    content_disposition = response.headers.get("Content-Disposition")

    if content_disposition:
        msg = mailbox.Message("Content-Disposition: %s" % content_disposition)
        filename = msg.get_filename()
        if filename:
            # Basic sanitation.
            filename = os.path.basename(filename).lstrip(".").strip()
            if filename:
                return filename
    return ""


def filename_from_url(response: httpx.Response) -> str:
    content_type = response.headers.get("Content-Type")
    filename = response.url.path.rstrip("/")
    filename = os.path.basename(filename) if filename else "index"

    if "." not in filename and content_type:
        content_type = content_type.split(";")[0]
        if content_type == "text/plain":
            # mimetypes returns '.ksh' or '.bat'
            ext = ".txt"
        else:
            ext = mimetypes.guess_extension(content_type)

        if ext == ".htm":  # Python 3
            ext = ".html"

        if ext:
            filename += ext

    return filename


def trim_filename(filename: str, max_len: int) -> str:
    if len(filename) > max_len:
        trim_by = len(filename) - max_len
        name, ext = os.path.splitext(filename)
        if trim_by >= len(name):
            filename = filename[:-trim_by]
        else:
            filename = name[:-trim_by] + ext
    return filename


def get_filename_max_length(directory: str) -> int:
    max_len = 255
    try:
        pathconf = os.pathconf
    except AttributeError:
        pass  # non-posix
    else:
        try:
            max_len = pathconf(directory, "PC_NAME_MAX")
        except OSError as e:
            if e.errno != errno.EINVAL:
                raise
    return max_len


def trim_filename_if_needed(filename: str, directory=".", extra=0) -> str:
    max_len = get_filename_max_length(directory) - extra
    if len(filename) > max_len:
        filename = trim_filename(filename, max_len)
    return filename


def get_unique_filename(filename: str, exists=os.path.exists) -> str:
    attempt = 0
    while True:
        suffix = f"-{attempt}" if attempt > 0 else ""
        try_filename = trim_filename_if_needed(filename, extra=len(suffix))
        name, ext = os.path.splitext(filename)
        try_filename = f"{name}{suffix}{ext}"
        if not exists(try_filename):
            return try_filename
        attempt += 1


def get_download_filename(response: httpx.Response) -> str:
    filename = filename_from_content_disposition(response)
    if not filename:
        filename = filename_from_url(response)
    return get_unique_filename(filename)
