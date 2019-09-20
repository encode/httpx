import asyncio
import httpx


async def main():
    async with httpx.AsyncClient() as client:
        for _ in range(1000):
            await client.get("http://localhost:8000")


asyncio.run(main())
