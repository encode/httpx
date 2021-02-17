#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from pathlib import Path

from setuptools import setup


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    version = Path(package, "__version__.py").read_text()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", version).group(1)


def get_long_description():
    """
    Return the README.
    """
    long_description = ""
    with open("README.md", encoding="utf8") as f:
        long_description += f.read()
    long_description += "\n\n"
    with open("CHANGELOG.md", encoding="utf8") as f:
        long_description += f.read()
    return long_description


def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [str(path.parent) for path in Path(package).glob("**/__init__.py")]


setup(
    name="httpx",
    python_requires=">=3.6",
    version=get_version("httpx"),
    url="https://github.com/encode/httpx",
    project_urls={
        "Changelog": "https://github.com/encode/httpx/blob/master/CHANGELOG.md",
        "Documentation": "https://www.python-httpx.org",
        "Source": "https://github.com/encode/httpx",
    },
    license="BSD",
    description="The next generation HTTP client.",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Tom Christie",
    author_email="tom@tomchristie.com",
    package_data={"httpx": ["py.typed"]},
    packages=get_packages("httpx"),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "certifi",
        "sniffio",
        "rfc3986[idna2008]>=1.3,<2",
        "httpcore==0.12.*",
    ],
    extras_require={
        "http2": "h2==3.*",
        "brotli": "brotlipy==0.7.*",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP",
        "Framework :: AsyncIO",
        "Framework :: Trio",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
    ],
)
