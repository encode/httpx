"""
Handlers for Content-Encoding.

See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding
"""
import typing
import zlib

import httpcore.exceptions

try:
    import brotli
except ImportError:  # pragma: nocover
    brotli = None


class Decoder:
    def decode(self, data: bytes) -> bytes:
        raise NotImplementedError()  # pragma: nocover

    def flush(self) -> bytes:
        raise NotImplementedError()  # pragma: nocover


class IdentityDecoder(Decoder):
    """
    Handle unencoded data.
    """

    def decode(self, data: bytes) -> bytes:
        return data

    def flush(self) -> bytes:
        return b""


class DeflateDecoder(Decoder):
    """
    Handle 'deflate' decoding.

    See: https://stackoverflow.com/questions/1838699
    """

    def __init__(self) -> None:
        self.decompressor = zlib.decompressobj(-zlib.MAX_WBITS)

    def decode(self, data: bytes) -> bytes:
        try:
            return self.decompressor.decompress(data)
        except zlib.error as exc:
            raise httpcore.exceptions.DecodingError from exc

    def flush(self) -> bytes:
        try:
            return self.decompressor.flush()
        except zlib.error as exc:  # pragma: nocover
            raise httpcore.exceptions.DecodingError from exc


class GZipDecoder(Decoder):
    """
    Handle 'gzip' decoding.

    See: https://stackoverflow.com/questions/1838699
    """

    def __init__(self) -> None:
        self.decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)

    def decode(self, data: bytes) -> bytes:
        try:
            return self.decompressor.decompress(data)
        except zlib.error as exc:
            raise httpcore.exceptions.DecodingError from exc

    def flush(self) -> bytes:
        try:
            return self.decompressor.flush()
        except zlib.error as exc:  # pragma: nocover
            raise httpcore.exceptions.DecodingError from exc


class BrotliDecoder(Decoder):
    """
    Handle 'brotli' decoding.

    Requires `pip install brotlipy`. See: https://brotlipy.readthedocs.io/
    """

    def __init__(self) -> None:
        assert (
            brotli is not None
        ), "The 'brotlipy' library must be installed to use 'BrotliDecoder'"
        self.decompressor = brotli.Decompressor()

    def decode(self, data: bytes) -> bytes:
        try:
            return self.decompressor.decompress(data)
        except brotli.Error as exc:
            raise httpcore.exceptions.DecodingError from exc

    def flush(self) -> bytes:
        try:
            self.decompressor.finish()
            return b""
        except brotli.Error as exc:  # pragma: nocover
            raise httpcore.exceptions.DecodingError from exc


class MultiDecoder(Decoder):
    """
    Handle the case where multiple encodings have been applied.
    """

    def __init__(self, children: typing.Sequence[Decoder]) -> None:
        """
        'children' should be a sequence of decoders in the order in which
        each was applied.
        """
        # Note that we reverse the order for decoding.
        self.children = list(reversed(children))

    def decode(self, data: bytes) -> bytes:
        for child in self.children:
            data = child.decode(data)
        return data

    def flush(self) -> bytes:
        data = b""
        for child in self.children:
            data = child.decode(data) + child.flush()
        return data


SUPPORTED_DECODERS = {
    "identity": IdentityDecoder,
    "deflate": DeflateDecoder,
    "gzip": GZipDecoder,
    "br": BrotliDecoder,
}


if brotli is None:
    SUPPORTED_DECODERS.pop("br")  # pragma: nocover


ACCEPT_ENCODING = ", ".join(
    [key for key in SUPPORTED_DECODERS.keys() if key != "identity"]
)
