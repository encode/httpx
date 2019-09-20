import contextlib
import time
import typing


async def app(scope: dict, receive: typing.Callable, send: typing.Callable) -> None:
    assert scope["type"] == "http"
    res = b"Hello, world"
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/plain"],
                [b"content-length", b"%d" % len(res)],
            ],
        }
    )
    await send({"type": "http.response.body", "body": res})


@contextlib.contextmanager
def timeit() -> typing.Iterator[None]:
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"Took {elapsed:.2f} seconds")
