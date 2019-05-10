import asyncio
import typing
from types import TracebackType


class Parallel:
    def __init__(self, client):
        self.client = client
        self.pending_responses = {}

    def request_soon(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        task = loop.create_task(self.client.request(*args, **kwargs))
        pending = PendingResponse(task, self.pending_responses)
        self.pending_responses[task] = pending
        return pending

    async def next_response(self):
        tasks = list(self.pending_responses.keys())
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        task = done.pop()
        del self.pending_responses[task]
        return task.result()

    @property
    def has_pending_responses(self):
        return bool(self.pending_responses)

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        for task in self.pending_responses.keys():
            task.cancel()


class PendingResponse:
    def __init__(self, task, pending_responses):
        self.task = task
        self.pending_responses = pending_responses

    async def get_response(self):
        try:
            return await self.task
        finally:
            del self.pending_responses[self.task]
