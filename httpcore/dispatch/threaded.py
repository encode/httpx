from ..config import CertTypes, TimeoutTypes, VerifyTypes
from ..interfaces import AsyncDispatcher, ConcurrencyBackend, Dispatcher
from ..models import AsyncRequest, AsyncResponse, Request, Response


class ThreadedDispatcher(AsyncDispatcher):
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
        func = self.sync_dispatcher.send
        kwargs = {
            "request": request,
            "verify": verify,
            "cert": cert,
            "timeout": timeout,
        }
        return await self.backend.run_in_threadpool(func, **kwargs)

    async def close(self) -> None:
        func = self.sync_dispatcher.close
        await self.backend.run_in_threadpool(func)
