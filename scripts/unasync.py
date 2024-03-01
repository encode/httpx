#!venv/bin/python
import os
import re
import sys
from pprint import pprint

SUBS = [
    ('from .._backends.auto import AutoBackend', 'from .._backends.sync import SyncBackend'),
    ('from .._transports.asgi import ASGITransport', 'from .._transports.wsgi import WSGITransport'),
    ('import trio as concurrency', 'from tests import concurrency'),
    ('BoundAsyncStream', 'BoundSyncStream'),
    ('AsyncByteStream', 'SyncByteStream'),
    ('ASGITransport', 'WSGITransport'),
    ('StopAsyncIteration', 'StopIteration'),
    ('async_start', 'sync_start'),
    ('async_elapsed', 'sync_elapsed'),
    ('async_auth_flow', 'sync_auth_flow'),
    ('AsyncIterator', 'Iterator'),
    ('Async([A-Z][A-Za-z0-9_]*)', r'\2'),
    ('async def', 'def'),
    ('async with', 'with'),
    ('async for', 'for'),
    ('await ', ''),
    ('handle_async_request', 'handle_request'),
    ('aclose', 'close'),
    ('aiter_stream', 'iter_stream'),
    ('aread', 'read'),
    ('asend', 'send'),
    ('asynccontextmanager', 'contextmanager'),
    ('__aenter__', '__enter__'),
    ('__aexit__', '__exit__'),
    ('__aiter__', '__iter__'),
    ('__anext__', '__next__'),
    ('@pytest.mark.anyio', ''),
    ('@pytest.mark.trio', ''),
    ('AutoBackend', 'SyncBackend'),
]
COMPILED_SUBS = [
    (re.compile(r'(^|\b)' + regex + r'($|\b)'), repl)
    for regex, repl in SUBS
]

USED_SUBS = set()

def unasync_line(line):
    for index, (regex, repl) in enumerate(COMPILED_SUBS):
        old_line = line
        line = re.sub(regex, repl, line)
        if old_line != line:
            USED_SUBS.add(index)
    return line


def unasync_file(in_path, out_path):
    with open(in_path, "r") as in_file:
        with open(out_path, "w", newline="") as out_file:
            for line in in_file.readlines():
                line = unasync_line(line)
                out_file.write(line)


def unasync_file_check(in_path, out_path):
    with open(in_path, "r") as in_file:
        with open(out_path, "r") as out_file:
            for in_line, out_line in zip(in_file.readlines(), out_file.readlines()):
                expected = unasync_line(in_line)
                if out_line != expected:
                    print(f'unasync mismatch between {in_path!r} and {out_path!r}')
                    print(f'Async code:         {in_line!r}')
                    print(f'Expected sync code: {expected!r}')
                    print(f'Actual sync code:   {out_line!r}')
                    sys.exit(1)


def unasync_dir(in_dir, out_dir, check_only=False):
    for dirpath, dirnames, filenames in os.walk(in_dir):
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            rel_dir = os.path.relpath(dirpath, in_dir)
            in_path = os.path.normpath(os.path.join(in_dir, rel_dir, filename))
            out_path = os.path.normpath(os.path.join(out_dir, rel_dir, filename))
            print(in_path, '->', out_path)
            if check_only:
                unasync_file_check(in_path, out_path)
            else:
                unasync_file(in_path, out_path)


def main():
    check_only = '--check' in sys.argv

    FILES_TO_UNASYNC = [
        ("httpx/_clients/_async_client.py", "httpx/_clients/_sync_client.py")
    ]

    for in_path, out_path in FILES_TO_UNASYNC:
        if check_only:
            unasync_file_check(in_path, out_path)
        else:
            unasync_file(in_path, out_path)

    if len(USED_SUBS) != len(SUBS):
        unused_subs = [SUBS[i] for i in range(len(SUBS)) if i not in USED_SUBS]

        print("These patterns were not used:")
        pprint(unused_subs)
        exit(1)   
        

if __name__ == '__main__':
    main()