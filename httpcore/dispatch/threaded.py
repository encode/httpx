from ..config import CertTypes, TimeoutTypes, VerifyTypes
from ..interfaces import AsyncDispatcher, ConcurrencyBackend, Dispatcher
from ..models import (
    AsyncRequest,
    AsyncResponse,
    AsyncResponseContent,
    Request,
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

        func = self.sync_dispatcher.send
        kwargs = {
            "request": request,
            "verify": verify,
            "cert": cert,
            "timeout": timeout,
        }
        sync_response = await self.backend.run_in_threadpool(func, **kwargs)
        assert isinstance(sync_response, Response)

        content = getattr(
            sync_response, "_raw_content", getattr(sync_response, "_raw_stream", None)
        )

        async_content = self._async_data(content)

        async def async_on_close() -> None:
            nonlocal concurrency_backend, sync_response
            await concurrency_backend.run_in_threadpool(sync_response.close)

        return AsyncResponse(
            status_code=sync_response.status_code,
            reason_phrase=sync_response.reason_phrase,
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

    def _async_data(self, data: ResponseContent) -> AsyncResponseContent:
        if isinstance(data, bytes):
            return data

        # Coerce an async iterator into an iterator, with each item in the
        # iteration run within the event loop.
        assert hasattr(data, "__iter__")
        return self.backend.iterate_in_threadpool(data)
