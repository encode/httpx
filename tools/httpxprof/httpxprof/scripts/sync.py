import tqdm

import httpx
from httpxprof.config import SERVER_URL


def main() -> None:
    with httpx.Client() as client:
        for _ in tqdm.tqdm(range(1000)):
            client.get(SERVER_URL)


main()
