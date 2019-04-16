"""
Handlers for Content-Encoding.

See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding
"""
import typing
import zlib

from .compat import brotli


class Decoder:
    def decode(self, data: bytes) -> bytes:
        raise NotImplementedError()  # pragma: nocover

    def flush(self) -> bytes:
        raise NotImplementedError()  # pragma: nocover


class IdentityDecoder(Decoder):
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
        return self.decompressor.decompress(data)

    def flush(self) -> bytes:
        return self.decompressor.flush()


class GZipDecoder(Decoder):
    """
    Handle 'gzip' decoding.

    See: https://stackoverflow.com/questions/1838699
    """

    def __init__(self) -> None:
        self.decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)

    def decode(self, data: bytes) -> bytes:
        return self.decompressor.decompress(data)

    def flush(self) -> bytes:
        return self.decompressor.flush()


class BrotliDecoder(Decoder):
    """
    Handle 'brotli' decoding.

    Requires `pip install brotlipy`.
    See: https://brotlipy.readthedocs.io/
    """

    def __init__(self) -> None:
        assert (
            brotli is not None
        ), "The 'brotlipy' library must be installed to use 'BrotliDecoder'"
        self.decompressor = brotli.Decompressor()

    def decode(self, data: bytes) -> bytes:
        return self.decompressor.decompress(data)

    def flush(self) -> bytes:
        self.decompressor.finish()
        return b""


class MultiDecoder(Decoder):
    """
    Handle the case where mutliple encodings have been applied.
    """

    def __init__(self, children: typing.Sequence[Decoder]) -> None:
        """
        children should be a sequence of decoders in the order in which
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
    b"identity": IdentityDecoder,
    b"deflate": DeflateDecoder,
    b"gzip": GZipDecoder,
    b"br": BrotliDecoder,
}


if brotli is None:
    SUPPORTED_DECODERS.pop(b"br")  # pragma: nocover


ACCEPT_ENCODING = b", ".join(
    [key for key in SUPPORTED_DECODERS.keys() if key != b"identity"]
)
