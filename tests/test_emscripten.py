import pytest

try:
    from pytest_pyodide import copy_files_to_pyodide,runner
    import pytest_pyodide

    # make our ssl certificates work in chrome
    pyodide_config=pytest_pyodide.config.get_global_config()
    pyodide_config.set_flags( "chrome", ["ignore-certificate-errors"]+pyodide_config.get_flags("chrome"))

except ImportError:
    pytest.skip()

import random
from typing import Any, Generator

_coverage_count = 0



def _get_coverage_filename(prefix: str) -> str:
    global _coverage_count
    _coverage_count += 1
    rand_part = "".join([random.choice("1234567890") for x in range(20)])
    return prefix + rand_part + f".{_coverage_count}"


@pytest.fixture()
def selenium_coverage(selenium_jspi: Any) -> Generator[Any, None, None]:
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

    selenium_jspi._install_packages = _install_packages.__get__(
        selenium_jspi, selenium_jspi.__class__
    )

    selenium_jspi._install_packages()
    yield selenium_jspi
    # on teardown, save _coverage output
    coverage_out_binary = bytes(
        selenium_jspi.run_js(
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


@pytest.fixture(scope="session",params=["https","http"])
def server_url(request,server,https_server):
    if request.param=='https':
        yield https_server.url
    else:
        yield server.url

@copy_files_to_pyodide(file_list=[("dist/*.whl", "/tmp")])
def test_get(server_url,selenium_coverage):
    selenium_coverage.run_async(
        f"""
    import httpx
    response = httpx.get('{server_url}')
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    #assert response.text == "Hello, world!"
    #assert response.http_version == "HTTP/1.1"
    """
    )


@copy_files_to_pyodide(file_list=[("dist/*.whl", "/tmp")])
def test_post_http(server_url,selenium_coverage):
    selenium_coverage.run_async(
        f"""
    import httpx
    response = httpx.post('{server_url}', content=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    """
    )

@copy_files_to_pyodide(file_list=[("dist/*.whl", "/tmp")])
def test_async_get(server_url,selenium_coverage):
    selenium_coverage.run_async(
        f"""
        import httpx
        url = '{server_url}'
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            assert response.status_code == 200
            assert response.text == "Hello, world!"
            assert response.http_version == "HTTP/1.1"
            assert response.headers
            assert repr(response) == "<Response [200 OK]>"
    """
    )

@copy_files_to_pyodide(file_list=[("dist/*.whl", "/tmp")])
def test_async_post_json(server_url,selenium_coverage):
    selenium_coverage.run_async(
        f"""
        import httpx
        url = '{server_url}'
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={{"text": "Hello, world!"}})
            assert response.status_code == 200
    """
    )

