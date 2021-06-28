"""
The _compat module is used for code which requires branching between different
Python environments. It is excluded from the code coverage checks.
"""

__all__ = ["asynccontextmanager", "aclosing", "set_minimum_tls_version_1_2"]

import ssl
import sys


if sys.version_info >= (3, 7):
    # `contextlib.asynccontextmanager` exists from Python 3.7 onwards.
    from contextlib import asynccontextmanager
else:
    # For 3.6 we require the `contextlib2` package for a backported version.
    from contextlib2 import asynccontextmanager

if sys.version_info >= (3, 10):
    # `contextlib.aclosing` exists from Python 3.10 onwards
    from contextlib import aclosing
else:
    # For 3.9 we require the `contextlib2` package for a backported version.
    from contextlib2 import aclosing

if sys.version_info >= (3, 10) or (
    sys.version_info >= (3, 7) and ssl.OPENSSL_VERSION_INFO >= (1, 1, 0, 7)
):

    def set_minimum_tls_version_1_2(context: ssl.SSLContext) -> None:
        # The OP_NO_SSL* and OP_NO_TLS* become deprecated in favor of
        # 'SSLContext.minimum_version' from Python 3.7 onwards, however
        # this attribute is not available unless the ssl module is compiled
        # with OpenSSL 1.1.0g or newer.
        # https://docs.python.org/3.10/library/ssl.html#ssl.SSLContext.minimum_version
        # https://docs.python.org/3.7/library/ssl.html#ssl.SSLContext.minimum_version
        context.minimum_version = ssl.TLSVersion.TLSv1_2


else:

    def set_minimum_tls_version_1_2(context: ssl.SSLContext) -> None:
        # If 'minimum_version' isn't available, we configure these options with
        # the older deprecated variants.
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
