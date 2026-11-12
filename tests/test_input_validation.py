from datetime import UTC, date, datetime

import pytest

from fb_posts import collect, credential_set
from fb_posts_lib.models import CollectionError, optional_text
from fb_posts_lib.token_status import inspect_token
from fb_posts_lib.transport import GraphTransport, decode_response
from tests.fb_posts_doubles import MemoryHttp, ScriptedGraph


@pytest.mark.parametrize("token,version", [("SECRET", "invalid"), ("white space", "v26.0")])
@pytest.mark.unit
def test_transport_rejects_invalid_configuration(token: str, version: str) -> None:
    with pytest.raises(CollectionError):
        GraphTransport(token, version, MemoryHttp(b"{}"))


@pytest.mark.unit
def test_optional_text_rejects_nontext_data() -> None:
    with pytest.raises(CollectionError, match="campo message inválido"):
        optional_text({"message": 42}, "message")


@pytest.mark.unit
def test_error_response_requires_numeric_code() -> None:
    with pytest.raises(CollectionError, match="error sin código válido"):
        decode_response(b'{"error": {"message": "private details"}}')


@pytest.mark.boundary
def test_token_inspection_rejects_invalid_page_before_network_access() -> None:
    reader = ScriptedGraph([])
    with pytest.raises(CollectionError, match="debe ser numérico"):
        inspect_token(reader, "secret", "invalid", datetime(2026, 1, 1, tzinfo=UTC))
    assert reader.calls == []


@pytest.mark.integration
def test_collect_rejects_invalid_page_before_database_access() -> None:
    with pytest.raises(CollectionError, match="debe ser numérico"):
        collect(date(2026, 1, 1), page_id="invalid")


@pytest.mark.unit
def test_credential_set_rejects_invalid_page_before_keyring_access() -> None:
    with pytest.raises(CollectionError, match="debe ser numérico"):
        credential_set(page_id="invalid")
