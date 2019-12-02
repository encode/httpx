from enum import IntEnum


class StatusCode(IntEnum):
    """HTTP status codes and reason phrases
    Status codes from the following RFCs are all observed:
        * RFC 7231: Hypertext Transfer Protocol (HTTP/1.1), obsoletes 2616
        * RFC 6585: Additional HTTP Status Codes
        * RFC 3229: Delta encoding in HTTP
        * RFC 4918: HTTP Extensions for WebDAV, obsoletes 2518
        * RFC 5842: Binding Extensions to WebDAV
        * RFC 7238: Permanent Redirect
        * RFC 2295: Transparent Content Negotiation in HTTP
        * RFC 2774: An HTTP Extension Framework
        * RFC 7540: Hypertext Transfer Protocol Version 2 (HTTP/2)
        * RFC 2324: Hyper Text Coffee Pot Control Protocol (HTCPCP/1.0)
        * RFC 7725: An HTTP Status Code to Report Legal Obstacles
    """

    def __new__(cls, value: int, phrase: str = "") -> "StatusCode":
        obj = int.__new__(cls, value)  # type: ignore
        obj._value_ = value

        obj.phrase = phrase
        return obj

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def get_reason_phrase(cls, value: int) -> str:
        try:
            return StatusCode(value).phrase  # type: ignore
        except ValueError:
            return ""

    @classmethod
    def is_redirect(cls, value: int) -> bool:
        return value in (
            # 301 (Cacheable redirect. Method may change to GET.)
            StatusCode.MOVED_PERMANENTLY,
            # 302 (Uncacheable redirect. Method may change to GET.)
            StatusCode.FOUND,
            # 303 (Client should make a GET or HEAD request.)
            StatusCode.SEE_OTHER,
            # 307 (Equiv. 302, but retain method)
            StatusCode.TEMPORARY_REDIRECT,
            # 308 (Equiv. 301, but retain method)
            StatusCode.PERMANENT_REDIRECT,
        )

    @classmethod
    def is_error(cls, value: int) -> bool:
        return 400 <= value <= 599

    @classmethod
    def is_client_error(cls, value: int) -> bool:
        return 400 <= value <= 499

    @classmethod
    def is_server_error(cls, value: int) -> bool:
        return 500 <= value <= 599

    # informational
    CONTINUE = 100, "Continue"
    SWITCHING_PROTOCOLS = 101, "Switching Protocols"
    PROCESSING = 102, "Processing"

    # success
    OK = 200, "OK"
    CREATED = 201, "Created"
    ACCEPTED = 202, "Accepted"
    NON_AUTHORITATIVE_INFORMATION = 203, "Non-Authoritative Information"
    NO_CONTENT = 204, "No Content"
    RESET_CONTENT = 205, "Reset Content"
    PARTIAL_CONTENT = 206, "Partial Content"
    MULTI_STATUS = 207, "Multi-Status"
    ALREADY_REPORTED = 208, "Already Reported"
    IM_USED = 226, "IM Used"

    # redirection
    MULTIPLE_CHOICES = 300, "Multiple Choices"
    MOVED_PERMANENTLY = 301, "Moved Permanently"
    FOUND = 302, "Found"
    SEE_OTHER = 303, "See Other"
    NOT_MODIFIED = 304, "Not Modified"
    USE_PROXY = 305, "Use Proxy"
    TEMPORARY_REDIRECT = 307, "Temporary Redirect"
    PERMANENT_REDIRECT = 308, "Permanent Redirect"

    # client error
    BAD_REQUEST = 400, "Bad Request"
    UNAUTHORIZED = 401, "Unauthorized"
    PAYMENT_REQUIRED = 402, "Payment Required"
    FORBIDDEN = 403, "Forbidden"
    NOT_FOUND = 404, "Not Found"
    METHOD_NOT_ALLOWED = 405, "Method Not Allowed"
    NOT_ACCEPTABLE = 406, "Not Acceptable"
    PROXY_AUTHENTICATION_REQUIRED = 407, "Proxy Authentication Required"
    REQUEST_TIMEOUT = 408, "Request Timeout"
    CONFLICT = 409, "Conflict"
    GONE = 410, "Gone"
    LENGTH_REQUIRED = 411, "Length Required"
    PRECONDITION_FAILED = 412, "Precondition Failed"
    REQUEST_ENTITY_TOO_LARGE = 413, "Request Entity Too Large"
    REQUEST_URI_TOO_LONG = 414, "Request-URI Too Long"
    UNSUPPORTED_MEDIA_TYPE = 415, "Unsupported Media Type"
    REQUESTED_RANGE_NOT_SATISFIABLE = 416, "Requested Range Not Satisfiable"
    EXPECTATION_FAILED = 417, "Expectation Failed"
    IM_A_TEAPOT = 418, "I'm a teapot"
    MISDIRECTED_REQUEST = 421, "Misdirected Request"
    UNPROCESSABLE_ENTITY = 422, "Unprocessable Entity"
    LOCKED = 423, "Locked"
    FAILED_DEPENDENCY = 424, "Failed Dependency"
    UPGRADE_REQUIRED = 426, "Upgrade Required"
    PRECONDITION_REQUIRED = 428, "Precondition Required"
    TOO_MANY_REQUESTS = 429, "Too Many Requests"
    REQUEST_HEADER_FIELDS_TOO_LARGE = 431, "Request Header Fields Too Large"
    UNAVAILABLE_FOR_LEGAL_REASONS = 451, "Unavailable For Legal Reasons"

    # server errors
    INTERNAL_SERVER_ERROR = 500, "Internal Server Error"
    NOT_IMPLEMENTED = 501, "Not Implemented"
    BAD_GATEWAY = 502, "Bad Gateway"
    SERVICE_UNAVAILABLE = 503, "Service Unavailable"
    GATEWAY_TIMEOUT = 504, "Gateway Timeout"
    HTTP_VERSION_NOT_SUPPORTED = 505, "HTTP Version Not Supported"
    VARIANT_ALSO_NEGOTIATES = 506, "Variant Also Negotiates"
    INSUFFICIENT_STORAGE = 507, "Insufficient Storage"
    LOOP_DETECTED = 508, "Loop Detected"
    NOT_EXTENDED = 510, "Not Extended"
    NETWORK_AUTHENTICATION_REQUIRED = 511, "Network Authentication Required"


codes = StatusCode

#  Include lower-case styles for `requests` compatibility.
for code in codes:
    setattr(codes, code._name_.lower(), int(code))
