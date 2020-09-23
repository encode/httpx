import httpx
from httpx import __all__ as exported_members


def test_all_imports_are_exported() -> None:
    included_private_members = ["__description__", "__title__", "__version__"]
    assert exported_members == sorted(
        (
            member
            for member in vars(httpx).keys()
            if not member.startswith("_") or member in included_private_members
        ),
        key=str.casefold,
    )
