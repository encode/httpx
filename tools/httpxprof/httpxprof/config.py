import pathlib

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8123
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

OUTPUT_DIR = pathlib.Path(__file__).parent / "out"
SCRIPTS_DIR = pathlib.Path(__file__).parent / "scripts"
assert SCRIPTS_DIR.exists(), SCRIPTS_DIR
