from ..models import Response


class AsyncFixes:
    @staticmethod
    async def read_response(response: Response) -> bytes:
        return await response.aread()

    @staticmethod
    async def close_response(response: Response) -> None:
        await response.aclose()


class SyncFixes:
    @staticmethod
    def read_response(response: Response) -> bytes:
        return response.read()

    @staticmethod
    def close_response(response: Response) -> None:
        response.close()
