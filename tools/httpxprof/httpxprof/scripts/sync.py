import httpx
import tqdm


def main() -> None:
    with httpx.Client() as client:
        for _ in tqdm.tqdm(range(1000)):
            client.get("http://localhost:8000")


main()
