from httpx import Client, QueryParams


def test_client_query_params():
    client = Client(params={"a": "b"})
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"


def test_client_query_params_string():
    client = Client(params="a=b")
    assert isinstance(client.params, QueryParams)
    assert client.params["a"] == "b"
