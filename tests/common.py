import pathlib

TESTS_DIR = pathlib.Path(__file__).parent
TESTS_DIR = TESTS_DIR.relative_to(TESTS_DIR.parent)  # Ensure relative to project root.
FIXTURES_DIR = TESTS_DIR / "fixtures"
