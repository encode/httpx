# emscripten specific test fixtures


import pytest
import random
import textwrap

from typing import Any, Generator


_coverage_count = 0


def _get_coverage_filename(prefix: str) -> str:
    global _coverage_count
    _coverage_count += 1
    rand_part = "".join([random.choice("1234567890") for x in range(20)])
    return prefix + rand_part + f".{_coverage_count}"


@pytest.fixture()
def selenium_with_jspi_if_possible(
    request: pytest.FixtureRequest, runtime: str, has_jspi: bool
) -> Generator[Any, None, None]:
    if runtime == "firefox":
        fixture_name = "selenium"
    else:
        fixture_name = "selenium_jspi"
    selenium_obj = request.getfixturevalue(fixture_name)
    selenium_obj.with_jspi = has_jspi
    yield selenium_obj


@pytest.fixture()
def selenium_coverage(
    selenium_with_jspi_if_possible: Any, has_jspi: bool
) -> Generator[Any, None, None]:
    def _install_packages(self: Any) -> None:
        if self.browser == "node":
            # stop node.js checking our https certificates
            self.run_js('process.env["NODE_TLS_REJECT_UNAUTHORIZED"] = 0;')

        self.run_js(
            """
            await pyodide.loadPackage("coverage")
            await pyodide.loadPackage("ssl")            
            await pyodide.runPythonAsync(`import coverage
_coverage= coverage.Coverage(source_pkgs=['httpx'])
_coverage.start()
        `
        )"""
        )

    if not hasattr(selenium_with_jspi_if_possible, "old_run_async"):
        selenium_with_jspi_if_possible.old_run_async = (
            selenium_with_jspi_if_possible.run_async
        )

    selenium_with_jspi_if_possible._install_packages = _install_packages.__get__(
        selenium_with_jspi_if_possible, selenium_with_jspi_if_possible.__class__
    )

    def run_with_jspi(self: Any, code: str) -> Any:
        code = textwrap.dedent(code)
        code = (
                "import httpx\n"
            +f"httpx._transports.emscripten.DISABLE_JSPI={self.with_jspi ==False}\n"
            + code
        )
        self.old_run_async(code)

    selenium_with_jspi_if_possible.run_with_jspi = run_with_jspi.__get__(
        selenium_with_jspi_if_possible, selenium_with_jspi_if_possible.__class__
    )

    selenium_with_jspi_if_possible._install_packages()
    yield selenium_with_jspi_if_possible
    # on teardown, save _coverage output
    coverage_out_binary = bytes(
        selenium_with_jspi_if_possible.run_js(
            """
return await pyodide.runPythonAsync(`
_coverage.stop()
_coverage.save()
_coverage_datafile = open(".coverage","rb")
_coverage_outdata = _coverage_datafile.read()
# avoid polluting main namespace too much
import js as _coverage_js
# convert to js Array (as default conversion is TypedArray which does
# bad things in firefox)
_coverage_js.Array.from_(_coverage_outdata)
`)
    """
        )
    )
    with open(f"{_get_coverage_filename('.coverage.emscripten.')}", "wb") as outfile:
        outfile.write(coverage_out_binary)


@pytest.fixture(scope="session", params=["https", "http"])
def server_url(request, server, https_server):
    if request.param == "https":
        yield https_server.url.copy_with(path="/emscripten")
    else:
        yield server.url.copy_with(path="/emscripten")


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Generate Webassembly Javascript Promise Integration based tests
    only for platforms that support it.

    Currently:
    1) node.js only supports use of JSPI because it doesn't support
    synchronous XMLHttpRequest

    2) firefox doesn't support JSPI

    3) Chrome supports JSPI on or off.
    """
    if "has_jspi" in metafunc.fixturenames:
        if metafunc.config.getoption("--runtime").startswith("node"):
            metafunc.parametrize("has_jspi", [True])
        elif metafunc.config.getoption("--runtime").startswith("firefox"):
            metafunc.parametrize("has_jspi", [False])
        else:
            metafunc.parametrize("has_jspi", [True, False])
