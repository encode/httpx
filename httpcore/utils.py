import codecs
import http
import typing


def normalize_header_key(value: typing.AnyStr, encoding: str = None) -> bytes:
    """
    Coerce str/bytes into a strictly byte-wise HTTP header key.
    """
    if isinstance(value, bytes):
        return value.lower()
    return value.encode(encoding or "ascii").lower()


def normalize_header_value(value: typing.AnyStr, encoding: str = None) -> bytes:
    """
    Coerce str/bytes into a strictly byte-wise HTTP header value.
    """
    if isinstance(value, bytes):
        return value
    return value.encode(encoding or "ascii")


def get_reason_phrase(status_code: int) -> str:
    """
    Return an HTTP reason phrase such as "OK" for 200, or "Not Found" for 404.
    """
    try:
        return http.HTTPStatus(status_code).phrase
    except ValueError as exc:
        return ""


def is_known_encoding(encoding: str) -> bool:
    """
    Return `True` if `encoding` is a known codec.
    """
    try:
        codecs.lookup(encoding)
    except LookupError:
        return False
    return True
