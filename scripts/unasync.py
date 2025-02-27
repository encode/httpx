#!venv/bin/python
import os
import re
import sys
from pprint import pprint

SUBS = [
    # httpx specific
    ("AsyncByteStream", "SyncByteStream"),
    ("async_auth_flow", "sync_auth_flow"),
    ("handle_async_request", "handle_request"),
    # general
    ("AsyncIterator", "Iterator"),
    ("from anyio import Lock", "from threading import Lock"),
    ("Async([A-Z][A-Za-z0-9_]*)", r"\2"),
    ("async def", "def"),
    ("async with", "with"),
    ("async for", "for"),
    ("await ", ""),
    ("aclose", "close"),
    ("aread", "read"),
    ("__aenter__", "__enter__"),
    ("__aexit__", "__exit__"),
    ("__aiter__", "__iter__"),
    ("@pytest.mark.anyio", ""),
]
COMPILED_SUBS = [
    (re.compile(r"(^|\b)" + regex + r"($|\b)"), repl) for regex, repl in SUBS
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
                    print(f"unasync mismatch between {in_path!r} and {out_path!r}")
                    print(f"Async code:         {in_line!r}")
                    print(f"Expected sync code: {expected!r}")
                    print(f"Actual sync code:   {out_line!r}")
                    sys.exit(1)


def unasync_dir(in_dir, out_dir, check_only=False):
    for dirpath, dirnames, filenames in os.walk(in_dir):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            rel_dir = os.path.relpath(dirpath, in_dir)
            in_path = os.path.normpath(os.path.join(in_dir, rel_dir, filename))
            out_path = os.path.normpath(os.path.join(out_dir, rel_dir, filename))
            print(in_path, "->", out_path)
            if check_only:
                unasync_file_check(in_path, out_path)
            else:
                unasync_file(in_path, out_path)


def main():
    check_only = "--check" in sys.argv
    unasync_dir("tests/client/async", "tests/client/sync", check_only=check_only)

    if len(USED_SUBS) != len(SUBS):
        unused_subs = [SUBS[i] for i in range(len(SUBS)) if i not in USED_SUBS]

        print("These patterns were not used:")
        pprint(unused_subs)
        exit(1)


if __name__ == "__main__":
    main()
