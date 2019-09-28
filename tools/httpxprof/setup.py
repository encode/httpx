import typing
from pathlib import Path

from setuptools import setup


def get_packages(package: str) -> typing.List[str]:
    return [str(path.parent) for path in Path(package).glob("**/__init__.py")]


setup(
    name="httpxprof",
    version="0.1",
    packages=get_packages("httpxprof"),
    install_requires=["click", "snakeviz", "uvicorn", "tqdm"],
    entry_points="""
        [console_scripts]
        httpxprof=httpxprof.main:cli
    """,
)
