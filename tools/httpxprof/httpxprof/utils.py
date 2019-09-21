import contextlib
import time
import multiprocessing
import typing

import uvicorn


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
def server() -> typing.Iterator[None]:
    config = uvicorn.Config(
        app=app, lifespan="off", loop="asyncio", log_level="warning"
    )
    server = uvicorn.Server(config)

    proc = multiprocessing.Process(target=server.run)
    proc.start()

    # Wait a bit for the uvicorn server process to be ready to accept connections.
    time.sleep(0.2)
    print("Server started.")

    try:
        yield
    finally:
        print("Stopping server...")
        proc.terminate()
        proc.join()


@contextlib.contextmanager
def timeit() -> typing.Iterator[None]:
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"Took {elapsed:.2f} seconds")
