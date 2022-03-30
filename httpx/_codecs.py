"""
The `httpx` package includes two optionally installable codecs,
which provide support for character-set autodetection.

This can be useful for cases where you need the textual content of responses,
rather than the raw bytewise content, if the Content-Type does not include
a `charset` value, and the character set of the responses is unknown.

There are two commonly used packages for this in the Python ecosystem.

* chardet: https://chardet.readthedocs.io/
* charset_normalizer: https://charset-normalizer.readthedocs.io/

---

## Using the default encoding.

To understand this better let's start by looking at the default behaviour
without character-set auto-detection...

```python
import httpx

# Instantiate a client with the default configuration.
client = httpx.Client()

# Using the client...
response = client.get(...)
print(response.encoding)  # This will either print the charset given in
                          # the Content-Type charset, or else "utf-8".
print(response.text)  # The text will either be decoded with the Content-Type
                      # charset, or using "utf-8".
```

This is normally absolutely fine. Most servers will respond with a properly
formatted Content-Type header, including a charset encoding. And in most cases
where no charset encoding is included, UTF-8 is very likely to be used,
since it is now so widely adopted.

## Using an explicit encoding.

In some cases we might be making requests to a site, where no character
set information is being set explicitly by the server, but we know what
the encoding is. In this case it's best to set the default encoding
explicitly on the client.

```python
import httpx

# Instantiate a client with a Japanese character set as the default encoding.
client = httpx.Client(default_encoding="shift-jis")

# Using the client...
response = client.get(...)
print(response.encoding)  # This will either print the charset given in
                          # the Content-Type charset, or else "shift-jis".
print(response.text)  # The text will either be decoded with the Content-Type
                      # charset, or using "shift-jis".
```

## Using character set auto-detection.

In cases where the server is not reliably including character set information,
and where we don't know what encoding is being used, we can enable auto-detection
to make a best-guess attempt when decoding from bytes to text.

```python
import codecs
import httpx


# Register the custom charset autodetect codecs.
# These codecs are then available as "chardet" and "charset_normalizer".
codecs.register(httpx.charset_autodetect)

# Instantiate a client using "chardet" character set autodetection.
# When no explicit charset information is present on the response,
# the chardet package will be used to make a best-guess attempt.
client = httpx.Client(default_encoding="chardet")

# Using the client with character-set autodetection enabled.
response = client.get(...)
print(response.encoding)  # This will either print the charset given in
                          # the Content-Type charset, or else "chardet".
print(response.text)  # The text will either be decoded with the Content-Type
                      # charset, or using "chardet" autodetection.
```
"""
import codecs
import typing


class ChardetCodec(codecs.Codec):
    def encode(input, errors="strict"):  # type: ignore
        raise RuntimeError("The 'chardet' codec does not support encoding.")

    def decode(input, errors="strict"):  # type: ignore
        import chardet

        content: bytes = bytes(input)
        info: dict = chardet.detect(content)
        encoding: str = info.get("encoding") or "utf-8"
        return content.decode(encoding, errors=errors), len(content)


class CharsetNormalizerCodec(codecs.Codec):
    def encode(input, errors="strict"):  # type: ignore
        raise RuntimeError("The 'charset_normalizer' codec does not support encoding.")

    def decode(input, errors="strict"):  # type: ignore
        import charset_normalizer

        content: bytes = bytes(input)
        info: dict = charset_normalizer.detect(content)
        encoding: str = info.get("encoding") or "utf-8"
        return content.decode(encoding, errors=errors), len(content)


class NullIncrementalEncoder(codecs.IncrementalEncoder):
    def encode(input, final=False):  # type: ignore
        raise RuntimeError("This codec does not support encoding.")


def charset_autodetect(encoding_name: str) -> typing.Optional[codecs.CodecInfo]:
    if encoding_name == "chardet":
        return codecs.CodecInfo(
            name="chardet",
            encode=ChardetCodec().encode,  # type: ignore
            decode=ChardetCodec().decode,  # type: ignore
            incrementalencoder=NullIncrementalEncoder,
            # Note that for iter_text/aiter_text we *always* just fallback
            # to using utf-8. Attempting character set autodetection in the
            # incremental case can cause large amounts of buffering.
            incrementaldecoder=codecs.getincrementaldecoder("utf-8"),
        )

    elif encoding_name == "charset_normalizer":
        return codecs.CodecInfo(
            name="charset_normalizer",
            encode=CharsetNormalizerCodec().encode,  # type: ignore
            decode=CharsetNormalizerCodec().decode,  # type: ignore
            incrementalencoder=NullIncrementalEncoder,
            # Note that for iter_text/aiter_text we *always* just fallback
            # to using utf-8. Attempting character set autodetection in the
            # incremental case can cause large amounts of buffering.
            incrementaldecoder=codecs.getincrementaldecoder("utf-8"),
        )

    return None
