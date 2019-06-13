import http3


def hello_world(environ, start_response):
    status = "200 OK"
    output = b"Hello, World!"

    response_headers = [
        ("Content-type", "text/plain"),
        ("Content-Length", str(len(output))),
    ]

    start_response(status, response_headers)

    return [output]


def test_wsgi():
    client = http3.Client(app=hello_world)
    response = client.get("http://www.example.org/")
    assert response.status_code == 200
    assert response.text == "Hello, World!"
