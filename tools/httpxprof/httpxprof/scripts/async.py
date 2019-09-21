import asyncio
import httpx
import tqdm


async def main() -> None:
    async with httpx.AsyncClient() as client:
        for _ in tqdm.tqdm(range(1000)):
            await client.get("http://localhost:8000")


asyncio.run(main())
