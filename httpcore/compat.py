import asyncio

if hasattr(asyncio, "run"):
    asyncio_run = asyncio.run

else:  # pragma: nocover

    def asyncio_run(main, *, debug=False):  # type: ignore
        if asyncio._get_running_loop() is not None:
            raise RuntimeError(
                "asyncio.run() cannot be called from a running event loop"
            )

        if not asyncio.iscoroutine(main):
            raise ValueError("a coroutine was expected, got {!r}".format(main))

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.set_debug(debug)
            return loop.run_until_complete(main)
        finally:
            try:
                _cancel_all_tasks(loop)
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                asyncio.set_event_loop(None)
                loop.close()

    def _cancel_all_tasks(loop):  # type: ignore
        to_cancel = asyncio.all_tasks(loop)
        if not to_cancel:
            return

        for task in to_cancel:
            task.cancel()

        loop.run_until_complete(
            tasks.gather(*to_cancel, loop=loop, return_exceptions=True)
        )

        for task in to_cancel:
            if task.cancelled():
                continue
            if task.exception() is not None:
                loop.call_exception_handler(
                    {
                        "message": "unhandled exception during asyncio.run() shutdown",
                        "exception": task.exception(),
                        "task": task,
                    }
                )
