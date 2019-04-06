"""
Handlers for Content-Encoding.
"""


class IdentityDecoder:
    def decode(self, chunk: bytes) -> bytes:
        return chunk

    def flush(self) -> bytes:
        return b""


# class DeflateDecoder:
#     pass
#
#
# class GZipDecoder:
#     pass
#
#
# class BrotliDecoder:
#     pass
#
#
# class MultiDecoder:
#     def __init__(self, children):
#         self.children = children
#
#     def decode(self, chunk: bytes) -> bytes:
#         data = chunk
#         for child in children:
#             data = child.decode(data)
#         return data
#
#     def flush(self) -> bytes:
#         data = b''
#         for child in children:
#             data = child.decode(data)
#             data = child.flush()
#         return data
