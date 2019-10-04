import pathlib
import re

PACKAGE = "httpx"


def get_version(package=PACKAGE):
    version = pathlib.Path(package, "__version__.py").read_text()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", version).group(1)
