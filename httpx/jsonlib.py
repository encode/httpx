"""
JSON library wrapper

This module intention is to keep json loader/dumper functions in one place.
Mainly to allow an easy override.

E.g. to use `orjson` module instead of default `json`:
```py
import httpx.jsonlib
import orjson

httpx.jsonlib.loads = orjson.loads
httpx.jsonlib.dumps = orjson.dumps
```
"""
import json


loads = json.loads
dumps = json.dumps


__all__ = ['loads', 'dumps']
