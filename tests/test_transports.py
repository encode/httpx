import datetime
import pytest
import httpx


def test_mock_transport_sets_elapsed():
    """Test that MockTransport sets the elapsed property on responses."""
    
    # 1. Create a simple handler that returns a response
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"Hello")
    
    # 2. Create a MockTransport with that handler
    transport = httpx.MockTransport(handler)
    
    # 3. Create a client with the transport
    client = httpx.Client(transport=transport)
    
    # 4. Make a request
    response = client.get("http://example.com/")
    
    # 5. Assert that elapsed is set and is a timedelta
    assert hasattr(response, "_elapsed")
    assert isinstance(response.elapsed, datetime.timedelta)
