"""
The _compat module is used for code which requires branching between different
Python environments. It is excluded from the code coverage checks.
"""

import re
from types import ModuleType
from typing import Optional

# Brotli support is optional
# The C bindings in `brotli` are recommended for CPython.
# The CFFI bindings in `brotlicffi` are recommended for PyPy and everything else.
try:
    import brotlicffi as brotli
except ImportError:  # pragma: no cover
    try:
        import brotli
    except ImportError:
        brotli = None

# Zstandard support is optional
zstd: Optional[ModuleType] = None
try:
    import zstandard as zstd
except (AttributeError, ImportError, ValueError):  # Defensive:
    zstd = None
else:
    # The package 'zstandard' added the 'eof' property starting
    # in v0.18.0 which we require to ensure a complete and
    # valid zstd stream was fed into the ZstdDecoder.
    # See: https://github.com/urllib3/urllib3/pull/2624
    _zstd_version = tuple(
        map(int, re.search(r"^([0-9]+)\.([0-9]+)", zstd.__version__).groups())  # type: ignore[union-attr]
    )
    if _zstd_version < (0, 18):  # Defensive:
        zstd = None

__all__ = ["brotli", "zstd"]
