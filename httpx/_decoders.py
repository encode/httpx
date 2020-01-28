"""
Handlers for Content-Encoding.

See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding
"""
import codecs
import typing
import zlib

import chardet

from ._exceptions import DecodingError

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
        self.first_attempt = True
        self.decompressor = zlib.decompressobj()

    def decode(self, data: bytes) -> bytes:
        was_first_attempt = self.first_attempt
        self.first_attempt = False
        try:
            return self.decompressor.decompress(data)
        except zlib.error as exc:
            if was_first_attempt:
                self.decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
                return self.decode(data)
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
        self.seen_data = False

    def decode(self, data: bytes) -> bytes:
        if not data:
            return b""
        self.seen_data = True
        try:
            if hasattr(self.decompressor, "decompress"):
                return self.decompressor.decompress(data)
            return self.decompressor.process(data)  # pragma: nocover
        except brotli.error as exc:
            raise DecodingError from exc

    def flush(self) -> bytes:
        if not self.seen_data:
            return b""
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
        self.decoder: typing.Optional[codecs.IncrementalDecoder] = (
            None if encoding is None else codecs.getincrementaldecoder(encoding)()
        )
        self.detector = chardet.universaldetector.UniversalDetector()

        # This buffer is only needed if 'decoder' is 'None'
        # we want to trigger errors if data is getting added to
        # our internal buffer for some silly reason while
        # a decoder is discovered.
        self.buffer: typing.Optional[bytearray] = None if self.decoder else bytearray()

    def decode(self, data: bytes) -> str:
        try:
            if self.decoder is not None:
                text = self.decoder.decode(data)
            else:
                assert self.buffer is not None
                text = ""
                self.detector.feed(data)
                self.buffer += data

                # Should be more than enough data to process, we don't
                # want to buffer too long as chardet will wait until
                # detector.close() is used to give back common
                # encodings like 'utf-8'.
                if len(self.buffer) >= 4096:
                    self.decoder = codecs.getincrementaldecoder(
                        self._detector_result()
                    )()
                    text = self.decoder.decode(bytes(self.buffer), False)
                    self.buffer = None

            return text
        except UnicodeDecodeError:  # pragma: nocover
            raise DecodingError() from None

    def flush(self) -> str:
        try:
            if self.decoder is None:
                # Empty string case as chardet is guaranteed to not have a guess.
                assert self.buffer is not None
                if len(self.buffer) == 0:
                    return ""
                return bytes(self.buffer).decode(self._detector_result())

            return self.decoder.decode(b"", True)
        except UnicodeDecodeError:  # pragma: nocover
            raise DecodingError() from None

    def _detector_result(self) -> str:
        self.detector.close()
        result = self.detector.result["encoding"]
        if not result:  # pragma: nocover
            raise DecodingError("Unable to determine encoding of content")

        return result


class LineDecoder:
    """
    Handles incrementally reading lines from text.

    Uses universal line decoding, supporting any of `\n`, `\r`, or `\r\n`
    as line endings, normalizing to `\n`.
    """

    def __init__(self) -> None:
        self.buffer = ""

    def decode(self, text: str) -> typing.List[str]:
        lines = []

        if text.startswith("\n") and self.buffer and self.buffer[-1] == "\r":
            # Handle the case where we have an "\r\n" split across
            # our previous input, and our new chunk.
            lines.append(self.buffer[:-1] + "\n")
            self.buffer = ""
            text = text[1:]

        while text:
            num_chars = len(text)
            for idx in range(num_chars):
                char = text[idx]
                next_char = None if idx + 1 == num_chars else text[idx + 1]
                if char == "\n":
                    lines.append(self.buffer + text[: idx + 1])
                    self.buffer = ""
                    text = text[idx + 1 :]
                    break
                elif char == "\r" and next_char == "\n":
                    lines.append(self.buffer + text[:idx] + "\n")
                    self.buffer = ""
                    text = text[idx + 2 :]
                    break
                elif char == "\r" and next_char is not None:
                    lines.append(self.buffer + text[:idx] + "\n")
                    self.buffer = ""
                    text = text[idx + 1 :]
                    break
                elif next_char is None:
                    self.buffer = text
                    text = ""
                    break

        return lines

    def flush(self) -> typing.List[str]:
        if self.buffer.endswith("\r"):
            # Handle the case where we had a trailing '\r', which could have
            # been a '\r\n' pair.
            lines = [self.buffer[:-1] + "\n"]
        elif self.buffer:
            lines = [self.buffer]
        else:
            lines = []
        self.buffer = ""
        return lines


SUPPORTED_DECODERS = {
    "identity": IdentityDecoder,
    "gzip": GZipDecoder,
    "deflate": DeflateDecoder,
    "br": BrotliDecoder,
}


if brotli is None:
    SUPPORTED_DECODERS.pop("br")  # pragma: nocover
