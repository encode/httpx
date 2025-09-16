import io
import types
import os


class Stream:
    def read(self, size: int=-1) -> bytes:
        raise NotImplementedError()

    def write(self, data: bytes) -> None:
        raise NotImplementedError()

    def close(self) -> None:
        raise NotImplementedError()

    @property
    def size(self) -> int | None:
        return None

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None
    ):
        self.close()


class ByteStream(Stream):
    def __init__(self, data: bytes = b''):
        self._buffer = io.BytesIO(data)
        self._size = len(data)

    def read(self, size: int=-1) -> bytes:
        return self._buffer.read(size)

    def close(self) -> None:
        self._buffer.close()

    @property
    def size(self) -> int | None:
        return self._size


class DuplexStream(Stream):
    """
    DuplexStream supports both `read` and `write` operations,
    which are applied to seperate buffers.

    This stream can be used for testing network parsers.
    """

    def __init__(self, data: bytes = b''):
        self._read_buffer = io.BytesIO(data)
        self._write_buffer = io.BytesIO()

    def read(self, size: int=-1) -> bytes:
        return self._read_buffer.read(size)

    def write(self, buffer: bytes):
        return self._write_buffer.write(buffer)

    def close(self) -> None:
        self._read_buffer.close()
        self._write_buffer.close()

    def input_bytes(self) -> bytes:
        return self._read_buffer.getvalue()

    def output_bytes(self) -> bytes:
        return self._write_buffer.getvalue()


class FileStream(Stream):
    def __init__(self, path):
        self._path = path
        self._fileobj = None
        self._size = None

    def read(self, size: int=-1) -> bytes:
        if self._fileobj is None:
            raise ValueError('I/O operation on unopened file')
        return self._fileobj.read(size)

    def open(self):
        self._fileobj = open(self._path, 'rb')
        self._size = os.path.getsize(self._path)
        return self

    def close(self) -> None:
        if self._fileobj is not None:
            self._fileobj.close()

    @property
    def size(self) -> int | None:
        return self._size

    def __enter__(self):
        self.open()
        return self


class HTTPStream(Stream):
    def __init__(self, next_chunk, complete):
        self._next_chunk = next_chunk
        self._complete = complete
        self._buffer = io.BytesIO()

    def read(self, size=-1) -> bytes:
        sections = []
        length = 0

        # If we have any data in the buffer read that and clear the buffer.
        buffered = self._buffer.read()
        if buffered:
            sections.append(buffered)
            length += len(buffered)
            self._buffer.seek(0)
            self._buffer.truncate(0)

        # Read each chunk in turn.
        while (size < 0) or (length < size):
            section = self._next_chunk()
            sections.append(section)
            length += len(section)
            if section == b'':
                break

        # If we've more data than requested, then push some back into the buffer.
        output = b''.join(sections)
        if size > -1 and len(output) > size:
            output, remainder = output[:size], output[size:]
            self._buffer.write(remainder)
            self._buffer.seek(0)

        return output

    def close(self) -> None:
        self._buffer.close()
        if self._complete is not None:
            self._complete()


class MultiPartStream(Stream):
    def __init__(self, form: list[tuple[str, str]], files: list[tuple[str, str]], boundary=''):
        self._form = list(form)
        self._files = list(files)
        self._boundary = boundary or os.urandom(16).hex()
        # Mutable state...
        self._form_progress = list(self._form)
        self._files_progress = list(self._files)
        self._filestream: FileStream | None = None
        self._complete = False
        self._buffer = io.BytesIO()

    def read(self, size=-1) -> bytes:
        sections = []
        length = 0

        # If we have any data in the buffer read that and clear the buffer.
        buffered = self._buffer.read()
        if buffered:
            sections.append(buffered)
            length += len(buffered)
            self._buffer.seek(0)
            self._buffer.truncate(0)

        # Read each multipart section in turn.
        while (size < 0) or (length < size):
            section = self._read_next_section()
            sections.append(section)
            length += len(section)
            if section == b'':
                break

        # If we've more data than requested, then push some back into the buffer.
        output = b''.join(sections)
        if size > -1 and len(output) > size:
            output, remainder = output[:size], output[size:]
            self._buffer.write(remainder)
            self._buffer.seek(0)

        return output

    def _read_next_section(self) -> bytes:
        if self._form_progress:
            # return a form item
            key, value = self._form_progress.pop(0)
            name = key.translate({10: "%0A", 13: "%0D", 34: "%22"})
            return (
                f"--{self._boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n'
                f"\r\n"
                f"{value}\r\n"
            ).encode("utf-8")
        elif self._files_progress and self._filestream is None:
            # return start of a file item
            key, value = self._files_progress.pop(0)
            self._filestream = FileStream(value).open()
            name = key.translate({10: "%0A", 13: "%0D", 34: "%22"})
            filename = os.path.basename(value)
            return (
                f"--{self._boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                f"\r\n"
            ).encode("utf-8")
        elif self._filestream is not None:
            chunk = self._filestream.read(64*1024)
            if chunk != b'':
                # return some bytes from file
                return chunk
            else:
                # return end of file item
                self._filestream.close()
                self._filestream = None
                return b"\r\n"
        elif not self._complete:
            # return final section of multipart
            self._complete = True
            return f"--{self._boundary}--\r\n".encode("utf-8")
        # return EOF marker
        return b""

    def close(self) -> None:
        if self._filestream is not None:
            self._filestream.close()
            self._filestream = None
        self._buffer.close()

    @property
    def size(self) -> int | None:
        return None
