from ..config import CertTypes, TimeoutTypes, VerifyTypes
from ..interfaces import AsyncDispatcher, ConcurrencyBackend, Dispatcher
from ..models import (
    AsyncRequest,
    AsyncRequestData,
    AsyncResponse,
    AsyncResponseContent,
    Request,
    RequestData,
    Response,
    ResponseContent,
)


class ThreadedDispatcher(AsyncDispatcher):
    """
    The ThreadedDispatcher class is used to mediate between the Client
    (which always uses async under the hood), and a synchronous `Dispatch`
    class.
    """

    def __init__(self, dispatch: Dispatcher, backend: ConcurrencyBackend) -> None:
        self.sync_dispatcher = dispatch
        self.backend = backend

    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        concurrency_backend = self.backend

        data = getattr(request, "content", getattr(request, "content_aiter", None))
        sync_data = self._sync_request_data(data)

        sync_request = Request(
            method=request.method,
            url=request.url,
            headers=request.headers,
            data=sync_data,
        )

        func = self.sync_dispatcher.send
        kwargs = {
            "request": sync_request,
            "verify": verify,
            "cert": cert,
            "timeout": timeout,
        }
        sync_response = await self.backend.run_in_threadpool(func, **kwargs)
        assert isinstance(sync_response, Response)

        content = getattr(
            sync_response, "_raw_content", getattr(sync_response, "_raw_stream", None)
        )

        async_content = self._async_response_content(content)

        async def async_on_close() -> None:
            nonlocal concurrency_backend, sync_response
            await concurrency_backend.run_in_threadpool(sync_response.close)

        return AsyncResponse(
            status_code=sync_response.status_code,
            protocol=sync_response.protocol,
            headers=sync_response.headers,
            content=async_content,
            on_close=async_on_close,
            request=request,
            history=sync_response.history,
        )

    async def close(self) -> None:
        """
        The `.close()` method runs the `Dispatcher.close()` within a threadpool,
        so as not to block the async event loop.
        """
        func = self.sync_dispatcher.close
        await self.backend.run_in_threadpool(func)

    def _async_response_content(self, content: ResponseContent) -> AsyncResponseContent:
        if isinstance(content, bytes):
            return content

        # Coerce an async iterator into an iterator, with each item in the
        # iteration run within the event loop.
        assert hasattr(content, "__iter__")
        return self.backend.iterate_in_threadpool(content)

    def _sync_request_data(self, data: AsyncRequestData) -> RequestData:
        if isinstance(data, bytes):
            return data

        return self.backend.iterate(data)
