from setuptools import setup

setup(
    name="httpxprof",
    version="0.1",
    packages=["httpxprof"],
    install_requires=["click", "snakeviz", "uvicorn"],
    entry_points="""
        [console_scripts]
        httpxprof=httpxprof.main:cli
    """,
)
