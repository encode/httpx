import enum


class Protocol(str, enum.Enum):
    HTTP_11 = "HTTP/1.1"
    HTTP_2 = "HTTP/2"
