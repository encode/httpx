import asyncio
import typing
from types import TracebackType

from .client import AsyncClient
from .config import SSLConfig, TimeoutConfig
from .models import (
    AuthTypes,
    CookieTypes,
    HeaderTypes,
    QueryParamTypes,
    RequestData,
    Response,
    SyncResponse,
    URLTypes,
)


class AsyncParallel:
    def __init__(self, client: AsyncClient = None) -> None:
        self.client = AsyncClient() if client is None else client
        self.manage_client_context = client is None
        self.pending_responses = (
            {}
        )  # type: typing.Dict[asyncio.Future, AsyncPendingResponse]

    async def request(
        self,
        method: str,
        url: URLTypes,
        *,
        data: RequestData = b"",
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> "AsyncPendingResponse":
        loop = asyncio.get_event_loop()
        coroutine = self.client.request(
            method=method,
            url=url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )
        task = loop.create_task(coroutine)
        pending = AsyncPendingResponse(task, self.pending_responses)
        self.pending_responses[task] = pending
        return pending

    async def next_response(self) -> Response:
        tasks = list(self.pending_responses.keys())
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        task = done.pop()
        del self.pending_responses[task]
        return task.result()

    @property
    def has_pending_responses(self) -> bool:
        return bool(self.pending_responses)

    async def close(self) -> None:
        for task in self.pending_responses.keys():
            task.cancel()
        if self.manage_client_context:
            await self.client.close()

    async def __aenter__(self) -> "AsyncParallel":
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        await self.close()

    async def get(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> "AsyncPendingResponse":
        return await self.request(
            "GET",
            url,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def options(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> "AsyncPendingResponse":
        return await self.request(
            "OPTIONS",
            url,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def head(
        self,
        url: URLTypes,
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = False,  #  Note: Differs to usual default.
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> "AsyncPendingResponse":
        return await self.request(
            "HEAD",
            url,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def post(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> "AsyncPendingResponse":
        return await self.request(
            "POST",
            url,
            data=data,
            json=json,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def put(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> "AsyncPendingResponse":
        return await self.request(
            "PUT",
            url,
            data=data,
            json=json,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def patch(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> "AsyncPendingResponse":
        return await self.request(
            "PATCH",
            url,
            data=data,
            json=json,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    async def delete(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        json: typing.Any = None,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        stream: bool = False,
        auth: AuthTypes = None,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> "AsyncPendingResponse":
        return await self.request(
            "DELETE",
            url,
            data=data,
            json=json,
            headers=headers,
            cookies=cookies,
            stream=stream,
            auth=auth,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )


class AsyncPendingResponse:
    def __init__(
        self,
        task: asyncio.Task,
        pending_responses: typing.Dict[asyncio.Future, "AsyncPendingResponse"],
    ) -> None:
        self.task = task
        self.pending_responses = pending_responses

    async def get_response(self) -> Response:
        try:
            return await self.task
        finally:
            del self.pending_responses[self.task]
