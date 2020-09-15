"""
Handlers for Content-Encoding.

See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding
"""
import codecs
import typing
import zlib

try:
    import brotli
except ImportError:  # pragma: nocover
    brotli = None


class ContentDecoder:
    def decode(self, data: bytes) -> bytes:
        raise NotImplementedError()  # pragma: nocover

    def flush(self) -> bytes:
        raise NotImplementedError()  # pragma: nocover


class IdentityDecoder(ContentDecoder):
    """
    Handle unencoded data.
    """

    def decode(self, data: bytes) -> bytes:
        return data

    def flush(self) -> bytes:
        return b""


class DeflateDecoder(ContentDecoder):
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
            raise ValueError(str(exc))

    def flush(self) -> bytes:
        try:
            return self.decompressor.flush()
        except zlib.error as exc:  # pragma: nocover
            raise ValueError(str(exc))


class GZipDecoder(ContentDecoder):
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
            raise ValueError(str(exc))

    def flush(self) -> bytes:
        try:
            return self.decompressor.flush()
        except zlib.error as exc:  # pragma: nocover
            raise ValueError(str(exc))


class BrotliDecoder(ContentDecoder):
    """
    Handle 'brotli' decoding.

    Requires `pip install brotlipy`. See: https://brotlipy.readthedocs.io/
        or   `pip install brotli`. See https://github.com/google/brotli
    Supports both 'brotlipy' and 'Brotli' packages since they share an import
    name. The top branches are for 'brotlipy' and bottom branches for 'Brotli'
    """

    def __init__(self) -> None:
        if brotli is None:  # pragma: nocover
            raise ImportError(
                "Using 'BrotliDecoder', but the 'brotlipy' or 'brotli' library "
                "is not installed."
                "Make sure to install httpx using `pip install httpx[brotli]`."
            ) from None

        self.decompressor = brotli.Decompressor()
        self.seen_data = False
        if hasattr(self.decompressor, "decompress"):
            self._decompress = self.decompressor.decompress
        else:
            self._decompress = self.decompressor.process  # pragma: nocover

    def decode(self, data: bytes) -> bytes:
        if not data:
            return b""
        self.seen_data = True
        try:
            return self._decompress(data)
        except brotli.error as exc:
            raise ValueError(str(exc))

    def flush(self) -> bytes:
        if not self.seen_data:
            return b""
        try:
            if hasattr(self.decompressor, "finish"):
                self.decompressor.finish()
            return b""
        except brotli.error as exc:  # pragma: nocover
            raise ValueError(str(exc))


class MultiDecoder(ContentDecoder):
    """
    Handle the case where multiple encodings have been applied.
    """

    def __init__(self, children: typing.Sequence[ContentDecoder]) -> None:
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
        self.decoder: typing.Optional[codecs.IncrementalDecoder] = None
        if encoding is not None:
            self.decoder = codecs.getincrementaldecoder(encoding)(errors="strict")

    def decode(self, data: bytes) -> str:
        """
        If an encoding is explicitly specified, then we use that.
        Otherwise our strategy is to attempt UTF-8, and fallback to Windows 1252.

        Note that UTF-8 is a strict superset of ascii, and Windows 1252 is a
        superset of the non-control characters in iso-8859-1, so we essentially
        end up supporting any of ascii, utf-8, iso-8859-1, cp1252.

        Given that UTF-8 is now by *far* the most widely used encoding, this
        should be a pretty robust strategy for cases where a charset has
        not been explicitly included.

        Useful stats on the prevalence of different charsets in the wild...

        * https://w3techs.com/technologies/overview/character_encoding
        * https://w3techs.com/technologies/history_overview/character_encoding

        The HTML5 spec also has some useful guidelines, suggesting defaults of
        either UTF-8 or Windows 1252 in most cases...

        * https://dev.w3.org/html5/spec-LC/Overview.html
        """
        if self.decoder is None:
            # If this is the first decode pass then we need to determine which
            # encoding to use by attempting UTF-8 and raising any decode errors.
            attempt_utf_8 = codecs.getincrementaldecoder("utf-8")(errors="strict")
            try:
                attempt_utf_8.decode(data)
            except UnicodeDecodeError:
                # Could not decode as UTF-8. Use Windows 1252.
                self.decoder = codecs.getincrementaldecoder("cp1252")(errors="replace")
            else:
                # Can decode as UTF-8. Use UTF-8 with lenient error settings.
                self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

        return self.decoder.decode(data)

    def flush(self) -> str:
        if self.decoder is None:
            return ""
        return self.decoder.decode(b"", True)


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

        if text and self.buffer and self.buffer[-1] == "\r":
            if text.startswith("\n"):
                # Handle the case where we have an "\r\n" split across
                # our previous input, and our new chunk.
                lines.append(self.buffer[:-1] + "\n")
                self.buffer = ""
                text = text[1:]
            else:
                # Handle the case where we have "\r" at the end of our
                # previous input.
                lines.append(self.buffer[:-1] + "\n")
                self.buffer = ""

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
                    self.buffer += text
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
