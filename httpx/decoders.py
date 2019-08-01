"""
Handlers for Content-Encoding.

See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding
"""
import codecs
import typing
import zlib

import chardet

from .exceptions import DecodingError
from .utils import is_known_encoding

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
            raise DecodingError from exc

    def flush(self) -> bytes:
        try:
            return self.decompressor.flush()
        except zlib.error as exc:  # pragma: nocover
            raise DecodingError from exc


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
            raise DecodingError from exc

    def flush(self) -> bytes:
        try:
            return self.decompressor.flush()
        except zlib.error as exc:  # pragma: nocover
            raise DecodingError from exc


class BrotliDecoder(Decoder):
    """
    Handle 'brotli' decoding.

    Requires `pip install brotlipy`. See: https://brotlipy.readthedocs.io/
        or   `pip install brotli`. See https://github.com/google/brotli
    Supports both 'brotlipy' and 'Brotli' packages since they share an import
    name. The top branches are for 'brotlipy' and bottom branches for 'Brotli'
    """

    def __init__(self) -> None:
        assert (
            brotli is not None
        ), "The 'brotlipy' or 'brotli' library must be installed to use 'BrotliDecoder'"
        self.decompressor = brotli.Decompressor()

    def decode(self, data: bytes) -> bytes:
        try:
            if hasattr(self.decompressor, "decompress"):
                return self.decompressor.decompress(data)
            return self.decompressor.process(data)  # pragma: nocover
        except brotli.error as exc:
            raise DecodingError from exc

    def flush(self) -> bytes:
        try:
            if hasattr(self.decompressor, "finish"):
                self.decompressor.finish()
            return b""
        except brotli.error as exc:  # pragma: nocover
            raise DecodingError from exc


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


class TextDecoder:
    """
    Handles incrementally decoding bytes into text
    """

    def __init__(self, encoding: typing.Optional[str] = None):
        self.buffer = bytearray()
        self.decoder = (
            None if encoding is None else codecs.getincrementaldecoder(encoding)()
        )
        self.detector = chardet.universaldetector.UniversalDetector()

    def decode(self, data: bytes) -> str:
        try:
            if self.decoder is not None:
                text = self.decoder.decode(data)
            else:
                text = ""
                self.detector.feed(data)
                self.buffer += data

                # If we don't wait for enough data chardet gives bad results.
                if len(self.buffer) >= 512:
                    detected_encoding = self._detector_result()

                    # If we actually detected the encoding we create a decoder right away.
                    # Apparently this is possible to do per the chardet docs but I couldn't
                    # get it to trigger during incremental decoding hence the 'nocover' :-(
                    if detected_encoding:  # pragma: nocover
                        self.decoder = codecs.getincrementaldecoder(detected_encoding)()
                        text = self.decoder.decode(bytes(self.buffer), False)
                        self.buffer = None

                    # Should be more than enough data to process, we don't want to buffer too long
                    # as chardet will wait until detector.close() is used to give back common
                    # encodings like 'utf-8'.
                    elif len(self.buffer) >= 4096:
                        self.detector.close()
                        self.decoder = codecs.getincrementaldecoder(
                            self._detector_result(default="utf-8")
                        )()
                        text = self.decoder.decode(bytes(self.buffer), False)
                        self.buffer = None

            return text
        except UnicodeDecodeError:  # pragma: nocover
            raise DecodingError from None

    def flush(self) -> str:
        try:
            if self.decoder is None:
                self.detector.close()
                return bytes(self.buffer).decode(
                    self._detector_result(min_confidence=0.5, default="utf-8")
                )

            return self.decoder.decode(b"", True)
        except UnicodeDecodeError:  # pragma: nocover
            raise DecodingError from None

    def _detector_result(
        self, min_confidence=0.75, default=None
    ) -> typing.Optional[str]:
        detected_encoding = (
            self.detector.result["encoding"]
            if self.detector.done
            and self.detector.result["confidence"] >= min_confidence
            else None
        )
        return (
            detected_encoding
            if detected_encoding and is_known_encoding(detected_encoding)
            else default
        )


SUPPORTED_DECODERS = {
    "identity": IdentityDecoder,
    "gzip": GZipDecoder,
    "deflate": DeflateDecoder,
    "br": BrotliDecoder,
}


if brotli is None:
    SUPPORTED_DECODERS.pop("br")  # pragma: nocover


ACCEPT_ENCODING = ", ".join(
    [key for key in SUPPORTED_DECODERS.keys() if key != "identity"]
)
