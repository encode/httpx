class ASGIStream:
    def __init__(self, recieve):
        pass

    async def __iter__(self) -> bytes:
        ...


class ASGIApp:
    def __init__(routes) -> None:
        self.router = Router(routes)

    async def __call__(scope, receive, send) -> None:
        method = ...
        url = ...
        stream = ...
        extensions = ...
        request = httpx.Request(method, url, stream=stream, extensions=extensions)
        response = await self.handle(request)
        await send(...)
        async for chunk in response.stream:
            ...
        await send(...)

    async def handle(request) -> Response:
        pass
