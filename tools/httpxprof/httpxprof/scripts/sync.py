import httpx


def main() -> None:
    with httpx.Client() as client:
        for _ in range(1000):
            client.get("http://localhost:8000")


main()
