import hashlib
import typing
import time
import os
from base64 import b64encode
from urllib.parse import urlparse

from .models import AsyncRequest, AsyncResponse


class AuthBase:
    """
    Base class that all auth implementations derive from.
    """

    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ) -> None:
        self.username = username
        self.password = password


class HTTPBasicAuth(AuthBase):
    pass


class HTTPDigestAuth(AuthBase):
    pass
