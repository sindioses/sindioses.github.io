import pytest

from fb_posts_lib.models import CollectionError, GraphError
from fb_posts_lib.transport import RejectRedirects, decode_response, sanitize_pagination


@pytest.mark.unit
def test_deprecated_field_identified() -> None:
    with pytest.raises(GraphError) as caught:
        decode_response(b'{"error":{"code":12,"message":"(#12) deprecate_post_aggregated_fields_for_attachement is deprecated for versions v3.3 and higher"}}')
    assert caught.value.field_rejection == True


@pytest.mark.unit
def test_invalid_json() -> None:
    with pytest.raises(CollectionError):
        decode_response(b"not json")


@pytest.mark.unit
def test_non_object_json() -> None:
    with pytest.raises(CollectionError):
        decode_response(b"[]")


@pytest.mark.unit
def test_nonfinite_json() -> None:
    with pytest.raises(CollectionError):
        decode_response(b'{"value": NaN}')


@pytest.mark.unit
def test_expired_token_error_safe() -> None:
    with pytest.raises(GraphError) as caught:
        decode_response(b'{"error":{"code":190,"message":"TOKEN_SECRET"}}')
    assert str(caught.value) == "Facebook rechazó el token (código 190). Obtenga un token de página nuevo y guárdelo con: uv run fb_posts.py credential set"
    assert caught.value.field_rejection == False


@pytest.mark.unit
def test_expired_session_subcode_has_safe_actionable_diagnostic() -> None:
    with pytest.raises(GraphError) as caught:
        decode_response(b'{"error":{"code":190,"error_subcode":463,"message":"TOKEN_SECRET"}}')
    assert (
        str(caught.value)
        == "El token de Facebook caducó (código 190, subcódigo 463). Obtenga un token de página nuevo y guárdelo con: uv run fb_posts.py credential set"
    )
    assert caught.value.subcode == 463
    assert caught.value.field_rejection == False


@pytest.mark.unit
def test_optional_field_identified() -> None:
    with pytest.raises(GraphError) as caught:
        decode_response(b'{"error":{"code":100,"message":"Tried accessing nonexisting field (old)"}}')
    assert caught.value.field_rejection == True


@pytest.mark.unit
def test_general_permission_error_is_fatal() -> None:
    with pytest.raises(GraphError) as caught:
        decode_response(b'{"error":{"code":10,"message":"Requires pages_read_engagement permission"}}')
    assert caught.value.field_rejection == False


@pytest.mark.unit
def test_pagination_secrets_removed_media_unchanged() -> None:
    value = {"attachments": {"media": {"src": "https://img.invalid/x?x=%2F"}, "paging": {"next": "https://graph.facebook.com/a?access_token=SECRET&after=x"}}}
    assert sanitize_pagination(value) == {
        "attachments": {"media": {"src": "https://img.invalid/x?x=%2F"}, "paging": {"next": "https://graph.facebook.com/a?after=x"}}
    }


@pytest.mark.unit
def test_redirect_does_not_forward_authorization() -> None:
    with pytest.raises(CollectionError):
        RejectRedirects().redirect_request(None, None, 302, "", {}, "https://evil.invalid")
