import unittest
from http.client import IncompleteRead
from io import BytesIO
from urllib.error import HTTPError, URLError

from fb_posts_lib.models import CollectionError, GraphError
from fb_posts_lib.transport import GraphTransport
from tests.fb_posts_doubles import MemoryHttp


class HttpTests(unittest.TestCase):
    def test_incomplete_response_is_safe(self):
        transport = GraphTransport("SECRET", "v26.0", MemoryHttp(b"", IncompleteRead(b"PRIVATE_DETAILS")))
        with self.assertRaises(CollectionError) as caught:
            transport.get("me", {})
        self.assertEqual(str(caught.exception), "No se pudo completar la conexión con Facebook.")

    def test_bearer_header_and_timeout(self):
        opener = MemoryHttp(b'{"id":"123"}')
        transport = GraphTransport("SECRET", "v26.0", opener)
        self.assertEqual(transport.get("me", {"fields": "id"}), {"id": "123"})
        self.assertEqual(opener.requests[0].get_header("Authorization"), "Bearer SECRET")
        self.assertEqual(opener.requests[0].full_url, "https://graph.facebook.com/v26.0/me?fields=id")
        self.assertEqual(opener.timeouts, [30])

    def test_network_exception_does_not_expose_secrets(self):
        transport = GraphTransport("SECRET", "v26.0", MemoryHttp(b"", URLError("SECRET")))
        with self.assertRaises(CollectionError) as caught:
            transport.get("me", {})
        self.assertEqual(str(caught.exception), "No se pudo completar la conexión con Facebook.")

    def test_http_graph_error(self):
        error = HTTPError("https://graph.facebook.com", 400, "SECRET", {}, BytesIO(b'{"error":{"code":190,"message":"SECRET"}}'))
        transport = GraphTransport("SECRET", "v26.0", MemoryHttp(b"", error))
        with self.assertRaises(GraphError) as caught:
            transport.get("me", {})
        self.assertEqual(caught.exception.code, 190)

    def test_rate_limit_remains_fatal(self):
        transport = GraphTransport("SECRET", "v26.0", MemoryHttp(b'{"error":{"code":4,"message":"limit"}}'))
        with self.assertRaises(GraphError) as caught:
            transport.get("me", {})
        self.assertEqual(caught.exception.field_rejection, False)

    def test_host_injection_rejected(self):
        opener = MemoryHttp(b"{}")
        transport = GraphTransport("SECRET", "v26.0", opener)
        with self.assertRaises(CollectionError):
            transport.get("https://evil.invalid", {})
        self.assertEqual(opener.requests, [])
