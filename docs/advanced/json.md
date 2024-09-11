# JSON encoding/decoding

You can set a custom json encoder and decoder, e.g. if you want to use `msgspec` instead or python's `json` implementation.

Your custom function needs to return `bytes`. 


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
def custom_json_decoder(json_data: bytes, **kwargs) -> bytes:
    return decoder.decode(json_data)

httpx.register_json_decoder(custom_json_decoder)
```
