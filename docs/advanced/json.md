# JSON encoding/decoding

You can set a custom json encoder and decoder, e.g. if you want to use `msgspec` instead or python's `json` implementation.

Your custom function needs to return `bytes`. 


**Custom orjson implementation:**
```python
import httpx
import orjson
import typing


def custom_json_encoder(json_data: typing.Any) -> bytes:
    return orjson.dumps(json_data)

httpx.register_json_encoder(custom_json_encoder)


def custom_json_decoder(json_data: bytes, **kwargs: typing.Any) -> bytes:
    return orjson.loads(json_data)

httpx.register_json_decoder(custom_json_decoder)
```


**Custom msgspec implementation:**
```python
import httpx
import msgspec
import typing


encoder = msgspec.json.Encoder()
def custom_json_encoder(json_data: typing.Any) -> bytes:
    return encoder.encode(json_data)

httpx.register_json_encoder(custom_json_encoder)


decoder = msgspec.json.Decoder()
def custom_json_decoder(json_data: bytes, **kwargs: typing.Any) -> bytes:
    return decoder.decode(json_data)

httpx.register_json_decoder(custom_json_decoder)
```

