from http.client import IncompleteRead
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from fb_posts_lib.models import CollectionError, GraphError
from fb_posts_lib.transport import GraphTransport
from tests.fb_posts_doubles import MemoryHttp


@pytest.mark.boundary
def test_incomplete_response_is_safe() -> None:
    transport = GraphTransport("SECRET", "v26.0", MemoryHttp(b"", IncompleteRead(b"PRIVATE_DETAILS")))
    with pytest.raises(CollectionError) as caught:
        transport.get("me", {})
    assert str(caught.value) == "No se pudo completar la conexión con Facebook."


@pytest.mark.boundary
def test_bearer_header_and_timeout() -> None:
    opener = MemoryHttp(b'{"id":"123"}')
    transport = GraphTransport("SECRET", "v26.0", opener)
    assert transport.get("me", {"fields": "id"}) == {"id": "123"}
    assert opener.requests[0].get_header("Authorization") == "Bearer SECRET"
    assert opener.requests[0].full_url == "https://graph.facebook.com/v26.0/me?fields=id"
    assert opener.timeouts == [30]


@pytest.mark.boundary
def test_network_exception_does_not_expose_secrets() -> None:
    transport = GraphTransport("SECRET", "v26.0", MemoryHttp(b"", URLError("SECRET")))
    with pytest.raises(CollectionError) as caught:
        transport.get("me", {})
    assert str(caught.value) == "No se pudo completar la conexión con Facebook."


@pytest.mark.boundary
def test_http_graph_error() -> None:
    error = HTTPError("https://graph.facebook.com", 400, "SECRET", {}, BytesIO(b'{"error":{"code":190,"message":"SECRET"}}'))
    transport = GraphTransport("SECRET", "v26.0", MemoryHttp(b"", error))
    with pytest.raises(GraphError) as caught:
        transport.get("me", {})
    assert caught.value.code == 190


@pytest.mark.boundary
def test_rate_limit_remains_fatal() -> None:
    transport = GraphTransport("SECRET", "v26.0", MemoryHttp(b'{"error":{"code":4,"message":"limit"}}'))
    with pytest.raises(GraphError) as caught:
        transport.get("me", {})
    assert caught.value.field_rejection == False


@pytest.mark.boundary
def test_host_injection_rejected() -> None:
    opener = MemoryHttp(b"{}")
    transport = GraphTransport("SECRET", "v26.0", opener)
    with pytest.raises(CollectionError):
        transport.get("https://evil.invalid", {})
    assert opener.requests == []
