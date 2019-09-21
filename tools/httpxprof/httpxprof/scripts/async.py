import asyncio

import tqdm

import httpx
from httpxprof.config import SERVER_URL


async def main() -> None:
    async with httpx.AsyncClient() as client:
        for _ in tqdm.tqdm(range(1000)):
            await client.get(SERVER_URL)


asyncio.run(main())
