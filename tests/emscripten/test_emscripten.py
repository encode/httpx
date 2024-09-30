import pytest

# only run these tests if pytest_pyodide is installed
# so we don't break non-emscripten pytest running
pytest_pyodide = pytest.importorskip("pytest_pyodide")

from pytest_pyodide import copy_files_to_pyodide
from pytest_pyodide import config as pconfig

# make our ssl certificates work in chrome
pyodide_config = pconfig.get_global_config()
pyodide_config.set_flags(
    "chrome", ["ignore-certificate-errors"] + pyodide_config.get_flags("chrome")
)


@copy_files_to_pyodide(file_list=[("dist/*.whl", "/tmp")])
def test_get(server_url, selenium_coverage):
    selenium_coverage.run_async(
        f"""
    import httpx
    response = httpx.get('{server_url}')
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"
    """
    )


@copy_files_to_pyodide(file_list=[("dist/*.whl", "/tmp")])
def test_post_http(server_url, selenium_coverage):
    selenium_coverage.run_async(
        f"""
    import httpx
    response = httpx.post('{server_url}', content=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    """
    )


@copy_files_to_pyodide(file_list=[("dist/*.whl", "/tmp")])
def test_async_get(server_url, selenium_coverage):
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
def test_async_get_timeout(server_url, selenium_coverage):
    # test timeout on https and http
    # this is a blackhole ip address which should never respond
    timeout_url = str(server_url).split(":")[0]+"://192.0.2.1"
    selenium_coverage.run_async(
        f"""
        import httpx
        import pytest
        url = '{timeout_url}'
        with pytest.raises(httpx.ConnectTimeout):
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(url)
    """
    )

@copy_files_to_pyodide(file_list=[("dist/*.whl", "/tmp")])
def test_sync_get_timeout(server_url, selenium_coverage):
    # test timeout on https and http
    # this is a blackhole ip address which should never respond
    timeout_url = str(server_url).split(":")[0]+"://192.0.2.1"
    selenium_coverage.run_async(
        f"""
        import httpx
        import pytest
        url = '{timeout_url}'
        with pytest.raises(httpx.ConnectTimeout):
            response = httpx.get(url)
    """
    )



@copy_files_to_pyodide(file_list=[("dist/*.whl", "/tmp")])
def test_async_get_error(server_url, selenium_coverage):
    # test timeout on https and http
    # 255.255.255.255 should always return an error
    error_url = str(server_url).split(":")[0]+"://255.255.255.255/"
    selenium_coverage.run_async(
        f"""
        import httpx
        import pytest
        url = '{error_url}'
        with pytest.raises(httpx.ConnectError):
            response = httpx.get(url)        
    """
    )

@copy_files_to_pyodide(file_list=[("dist/*.whl", "/tmp")])
def test_sync_get_error(server_url, selenium_coverage):
    # test timeout on https and http
    # 255.255.255.255 should always return an error
    error_url = str(server_url).split(":")[0]+"://255.255.255.255/"
    selenium_coverage.run_async(
        f"""
        import httpx
        import pytest
        url = '{error_url}'
        with pytest.raises(httpx.ConnectError):
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(url)
    """
    )


@copy_files_to_pyodide(file_list=[("dist/*.whl", "/tmp")])
def test_async_post_json(server_url, selenium_coverage):
    selenium_coverage.run_async(
        f"""
        import httpx
        url     = '{server_url}'
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={{"text": "Hello, world!"}})
            assert response.status_code == 200
    """
    )

