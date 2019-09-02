import typing

from mypy_extensions import TypedDict

from .config import CertTypes, TimeoutTypes, VerifyTypes
from .models import (
    AuthTypes,
    CookieTypes,
    HeaderTypes,
    QueryParamTypes,
    RequestData,
    RequestFiles,
)


class RequestType(TypedDict):
    data: RequestData
    files: RequestFiles
    json: typing.Any
    params: QueryParamTypes
    headers: HeaderTypes
    cookies: CookieTypes
    stream: bool
    auth: AuthTypes
    allow_redirects: bool
    cert: CertTypes
    verify: VerifyTypes
    timeout: TimeoutTypes
    trust_env: bool
