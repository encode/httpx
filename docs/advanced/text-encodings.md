When accessing `response.text`, we need to decode the response bytes into a unicode text representation.

By default `httpx` will use `"charset"` information included in the response `Content-Type` header to determine how the response bytes should be decoded into text.

In cases where no charset information is included on the response, the default behaviour is to assume "utf-8" encoding, which is by far the most widely used text encoding on the internet.

## Using the default encoding

To understand this better let's start by looking at the default behaviour for text decoding...

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

This is normally absolutely fine. Most servers will respond with a properly formatted Content-Type header, including a charset encoding. And in most cases where no charset encoding is included, UTF-8 is very likely to be used, since it is so widely adopted.

## Using an explicit encoding

In some cases we might be making requests to a site where no character set information is being set explicitly by the server, but we know what the encoding is. In this case it's best to set the default encoding explicitly on the client.

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

## Using auto-detection

In cases where the server is not reliably including character set information, and where we don't know what encoding is being used, we can enable auto-detection to make a best-guess attempt when decoding from bytes to text.

To use auto-detection you need to set the `default_encoding` argument to a callable instead of a string. This callable should be a function which takes the input bytes as an argument and returns the character set to use for decoding those bytes to text.

There are two widely used Python packages which both handle this functionality:

* [`chardet`](https://chardet.readthedocs.io/) - This is a well established package, and is a port of [the auto-detection code in Mozilla](https://www-archive.mozilla.org/projects/intl/chardet.html).
* [`charset-normalizer`](https://charset-normalizer.readthedocs.io/) - A newer package, motivated by `chardet`, with a different approach.

Let's take a look at installing autodetection using one of these packages...

```shell
$ pip install httpx
$ pip install chardet
```

Once `chardet` is installed, we can configure a client to use character-set autodetection.

```python
import httpx
import chardet

def autodetect(content):
    return chardet.detect(content).get("encoding")

# Using a client with character-set autodetection enabled.
client = httpx.Client(default_encoding=autodetect)
response = client.get(...)
print(response.encoding)  # This will either print the charset given in
                          # the Content-Type charset, or else the auto-detected
                          # character set.
print(response.text)
```
