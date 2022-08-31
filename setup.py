import sys

sys.stderr.write(
    """
===============================
Unsupported installation method
===============================
httpx no longer supports installation with `python setup.py install`.
Please use `python -m pip install .` instead.
"""
)
sys.exit(1)


# The below code will never execute, however GitHub is particularly
# picky about where it finds Python packaging metadata.
# See: https://github.com/github/feedback/discussions/6456
#
# To be removed once GitHub catches up.

setup(
    name="httpx",
    install_requires=[
        "certifi",
        "sniffio",
        "rfc3986[idna2008]>=1.3,<2",
        "httpcore>=0.15.0,<0.16.0",
    ],
)
