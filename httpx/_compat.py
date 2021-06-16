"""
The _compat module is used for code which requires branching between different
Python environments. It is excluded from the code coverage checks.
"""
import ssl
import sys

# `contextlib.asynccontextmanager` exists from Python 3.7 onwards.
# For 3.6 we require the `async_generator` package for a backported version.
try:
    from contextlib import asynccontextmanager  # type: ignore
except ImportError:
    from async_generator import asynccontextmanager  # type: ignore # noqa


def set_minimum_tls_version_1_2(context: ssl.SSLContext) -> None:
    if sys.version_info >= (3, 10):
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    else:
        # These become deprecated in favor of 'context.minimum_version'
        # from Python 3.10 onwards.
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
