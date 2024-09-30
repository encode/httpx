"""
Custom transport for Pyodide on Emscripten.

In sync mode it relies on use of the Javascript Promise Integration
feature which is currently experimental in webassembly and only works
in some places. Specifically in chrome JSPI is behind either a flag or an
origin trial, in node 20 or newer you need the --experimental-wasm-stack-switching
flag. Firefox is not currently supported.

See https://github.com/WebAssembly/js-promise-integration/

In async mode it uses pyodide's pyfetch api, which should work
anywhere that pyodide works.
"""

from __future__ import annotations

import typing
from types import TracebackType
from warnings import warn

import js
import pyodide

from .._config import DEFAULT_LIMITS, Limits
from .._exceptions import (
    ConnectError,
    ConnectTimeout,
    ReadError,
    ReadTimeout,
    RequestError,
)
from .._models import Request, Response
from .._types import AsyncByteStream, CertTypes, ProxyTypes, SyncByteStream, VerifyTypes
from .base import AsyncBaseTransport, BaseTransport

T = typing.TypeVar("T", bound="EmscriptenTransport")
A = typing.TypeVar("A", bound="AsyncEmscriptenTransport")

SOCKET_OPTION = typing.Union[
    typing.Tuple[int, int, int],
    typing.Tuple[int, int, typing.Union[bytes, bytearray]],
    typing.Tuple[int, int, None, int],
]

__all__ = ["AsyncEmscriptenTransport", "EmscriptenTransport"]

"""
There are some headers that trigger unintended CORS preflight requests.
See also https://github.com/koenvo/pyodide-http/issues/22
"""
HEADERS_TO_IGNORE = ("user-agent",)


def _run_sync_with_timeout(
    promise: typing.Awaitable[pyodide.ffi.JsProxy],
    timeout: float,
    abort_controller_js: pyodide.ffi.JsProxy,
    TimeoutExceptionType: type[RequestError],
    ErrorExceptionType: type[RequestError],
) -> pyodide.ffi.JsProxy:
    """await a javascript promise synchronously with a timeout set via the
       AbortController and return the resulting javascript proxy

    Args:
        promise (Awaitable): Javascript promise to await
        timeout (float): Timeout in seconds
        abort_controller_js (Any): A javascript AbortController object, used on timeout
        TimeoutExceptionType (type[Exception]): An exception type to raise on timeout
        ErrorExceptionType (type[Exception]): An exception type to raise on error

    Raises:
        TimeoutExceptionType: If the request times out
        ErrorExceptionType: If the request raises a Javascript exception

    Returns:
        _type_: The result of awaiting the promise.
    """
    timer_id = None
    if timeout > 0:
        timer_id = js.setTimeout(
            abort_controller_js.abort.bind(abort_controller_js), int(timeout * 1000)
        )
    try:
        from pyodide.ffi import run_sync

        # run_sync here uses WebAssembly Javascript Promise Integration to
        # suspend python until the Javascript promise resolves.
        return run_sync(promise)
    except pyodide.ffi.JsException as err:
        if err.name == "AbortError":
            raise TimeoutExceptionType(message="Request timed out")
        else:
            raise ErrorExceptionType(message=err.message)
    finally:
        if timer_id is not None:
            js.clearTimeout(timer_id)


async def _run_async_with_timeout(
    promise: typing.Awaitable[pyodide.ffi.JsProxy],
    timeout: float,
    abort_controller_js: pyodide.ffi.JsProxy,
    TimeoutExceptionType: type[RequestError],
    ErrorExceptionType: type[RequestError],
) -> pyodide.ffi.JsProxy:
    """await a javascript promise asynchronously with a timeout set via the
       AbortController

    Args:
        promise (Awaitable): Javascript promise to await
        timeout (float): Timeout in seconds
        abort_controller_js (Any): A javascript AbortController object, used on timeout
        TimeoutExceptionType (type[Exception]): An exception type to raise on timeout
        ErrorExceptionType (type[Exception]): An exception type to raise on error

    Raises:
        TimeoutException: If the request times out
        NetworkError: If the request raises a Javascript exception

    Returns:
        _type_: The result of awaiting the promise.
    """
    timer_id = None
    if timeout > 0:
        timer_id = js.setTimeout(
            abort_controller_js.abort.bind(abort_controller_js), int(timeout * 1000)
        )
    try:
        return await promise
    except pyodide.ffi.JsException as err:
        if err.name == "AbortError":
            raise TimeoutExceptionType(message="Request timed out")
        else:
            raise ErrorExceptionType(message=err.message)
    finally:
        if timer_id is not None:
            js.clearTimeout(timer_id)


class EmscriptenStream(SyncByteStream):
    def __init__(
        self,
        response_stream_js: pyodide.ffi.JsProxy,
        timeout: float,
        abort_controller_js: pyodide.ffi.JsProxy,
    ) -> None:
        self._stream_js = response_stream_js
        self.timeout = timeout
        self.abort_controller_js = abort_controller_js

    def __iter__(self) -> typing.Iterator[bytes]:
        while True:
            result_js = _run_sync_with_timeout(
                self._stream_js.read(),
                self.timeout,
                self.abort_controller_js,
                ReadTimeout,
                ReadError,
            )
            if result_js.done:
                return
            else:
                this_buffer = result_js.value.to_py()
                yield this_buffer

    def close(self) -> None:
        if self._stream_js is not None and hasattr(self._stream_js, "Close"):
            self._stream_js.Close()
        self._stream_js = None


class EmscriptenTransport(BaseTransport):
    def __init__(
        self,
        verify: VerifyTypes = True,
        cert: CertTypes | None = None,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        trust_env: bool = True,
        proxy: ProxyTypes | None = None,
        uds: str | None = None,
        local_address: str | None = None,
        retries: int = 0,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> None:
        if proxy is not None:
            warn("HTTPX does not support custom proxy setting on Emscripten")

    def __enter__(self: T) -> T:  # Use generics for subclass support.
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        pass

    def handle_request(
        self,
        request: Request,
    ) -> Response:
        assert isinstance(request.stream, SyncByteStream)
        req_body: bytes | None = b"".join(request.stream)
        if req_body is not None and len(req_body) == 0:
            req_body = None
        conn_timeout = 0.0
        read_timeout = 0.0
        if "timeout" in request.extensions:
            timeout_dict = request.extensions["timeout"]
            if timeout_dict is not None:
                if "connect" in timeout_dict:
                    conn_timeout = timeout_dict["connect"]
                if "read" in timeout_dict:
                    read_timeout = timeout_dict["connect"]
        abort_controller_js = js.AbortController.new()
        headers = {
            k: v for k, v in request.headers.items() if k not in HEADERS_TO_IGNORE
        }
        fetch_data = {
            "headers": headers,
            "body": pyodide.ffi.to_js(req_body),
            "method": request.method,
            "signal": abort_controller_js.signal,
        }

        fetcher_promise_js = js.fetch(
            request.url,
            pyodide.ffi.to_js(fetch_data, dict_converter=js.Object.fromEntries),
        )

        response_js = _run_sync_with_timeout(
            fetcher_promise_js,
            conn_timeout,
            abort_controller_js,
            ConnectTimeout,
            ConnectError,
        )

        headers = {}
        header_iter = response_js.headers.entries()
        while True:
            iter_value_js = header_iter.next()
            if getattr(iter_value_js, "done", False):
                break
            else:
                headers[str(iter_value_js.value[0])] = str(iter_value_js.value[1])
        # fix content-encoding headers because the javascript fetch handles that
        headers["content-encoding"] = "identity"
        status_code = response_js.status

        if response_js.body is not None:
            # get a reader from the fetch response
            body_stream_js = response_js.body.getReader()
            return Response(
                status_code=status_code,
                headers=headers,
                stream=EmscriptenStream(
                    body_stream_js, read_timeout, abort_controller_js
                ),
            )
        else:
            return Response(
                status_code=status_code,
                headers=headers,
                stream=None,
            )
        
    def _no_jspi_fallback():
        pass

    def close(self) -> None:
        pass


class AsyncEmscriptenStream(AsyncByteStream):
    def __init__(
        self,
        response_stream_js: pyodide.ffi.JsProxy,
        timeout: float,
        abort_controller_js: pyodide.ffi.JsProxy,
    ) -> None:
        self._stream_js = response_stream_js
        self.timeout = timeout
        self.abort_controller_js = abort_controller_js

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        while self._stream_js is not None:
            result_js = await _run_async_with_timeout(
                self._stream_js.read(),
                self.timeout,
                self.abort_controller_js,
                ReadTimeout,
                ReadError,
            )
            if result_js.done:
                return
            else:
                this_buffer = result_js.value.to_py()
                yield this_buffer

    async def aclose(self) -> None:
        if self._stream_js is not None and hasattr(self._stream_js, "Close"):
            self._stream_js.Close()
        self._stream_js = None


class AsyncEmscriptenTransport(AsyncBaseTransport):
    def __init__(
        self,
        verify: VerifyTypes = True,
        cert: CertTypes | None = None,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        trust_env: bool = True,
        proxy: ProxyTypes | None = None,
        uds: str | None = None,
        local_address: str | None = None,
        retries: int = 0,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> None:
        if proxy is not None:
            warn("HTTPX does not support custom proxy setting on Emscripten")

    async def __aenter__(self: A) -> A:  # Use generics for subclass support.
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        pass

    async def handle_async_request(
        self,
        request: Request,
    ) -> Response:
        assert isinstance(request.stream, AsyncByteStream)
        body_data: bytes = b""
        async for x in request.stream:
            body_data += x
        if len(body_data) == 0:
            req_body = None
        else:
            req_body = body_data
        print(req_body)
        conn_timeout = 0.0
        read_timeout = 0.0
        if "timeout" in request.extensions:
            timeout_dict = request.extensions["timeout"]
            if timeout_dict is not None:
                if "connect" in timeout_dict:
                    conn_timeout = timeout_dict["connect"]
                if "read" in timeout_dict:
                    read_timeout = timeout_dict["connect"]

        abort_controller_js = js.AbortController.new()
        headers = {
            k: v for k, v in request.headers.items() if k not in HEADERS_TO_IGNORE
        }
        fetch_data = {
            "headers": headers,
            "body": pyodide.ffi.to_js(req_body),
            "method": request.method,
            "signal": abort_controller_js.signal,
        }

        fetcher_promise_js = js.fetch(
            request.url,
            pyodide.ffi.to_js(fetch_data, dict_converter=js.Object.fromEntries),
        )
        response_js = await _run_async_with_timeout(
            fetcher_promise_js,
            conn_timeout,
            abort_controller_js,
            ConnectTimeout,
            ConnectError,
        )

        headers = {}
        header_iter = response_js.headers.entries()
        while True:
            iter_value_js = header_iter.next()
            if getattr(iter_value_js, "done", False):
                break
            else:
                headers[str(iter_value_js.value[0])] = str(iter_value_js.value[1])
        status_code = response_js.status

        if response_js.body is not None:
            # get a reader from the fetch response
            body_stream_js = response_js.body.getReader()
            return Response(
                status_code=status_code,
                headers=headers,
                stream=AsyncEmscriptenStream(
                    body_stream_js, read_timeout, abort_controller_js
                ),
            )
        else:
            return Response(
                status_code=status_code,
                headers=headers,
                stream=None,
            )

    async def aclose(self) -> None:
        pass
