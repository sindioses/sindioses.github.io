from datetime import UTC, datetime

import pytest

from fb_posts_lib.credentials import SERVICE, register_page_token
from fb_posts_lib.models import CollectionError
from fb_posts_lib.token_status import inspect_token, validate_metadata
from tests.fb_posts_doubles import MemorySecrets, ScriptedGraph


@pytest.mark.unit
def test_no_scheduled_expiration_with_separate_data_deadline() -> None:
    status = validate_metadata(
        {"is_valid": True, "type": "PAGE", "profile_id": "123", "app_id": "1603408681013331", "expires_at": 0, "data_access_expires_at": 1801766928},
        "123",
        datetime(2026, 11, 6, tzinfo=UTC),
    )
    assert status.data_access_expires_at == 1801766928
    assert status.summary().startswith("Token de página válido; caducidad del token: nunca. Acceso a datos: ") == True


@pytest.mark.unit
def test_user_token_is_rejected() -> None:
    with pytest.raises(CollectionError):
        validate_metadata(
            {"is_valid": True, "type": "USER", "profile_id": "123", "app_id": "1603408681013331", "expires_at": 0, "data_access_expires_at": 0},
            "123",
            datetime(2026, 11, 6, tzinfo=UTC),
        )


@pytest.mark.unit
def test_wrong_app_is_rejected() -> None:
    with pytest.raises(CollectionError):
        validate_metadata(
            {"is_valid": True, "type": "PAGE", "profile_id": "123", "app_id": "wrong", "expires_at": 0, "data_access_expires_at": 0},
            "123",
            datetime(2026, 11, 6, tzinfo=UTC),
        )


@pytest.mark.unit
def test_short_lived_page_token_is_rejected() -> None:
    with pytest.raises(CollectionError):
        validate_metadata(
            {
                "is_valid": True,
                "type": "PAGE",
                "profile_id": "123",
                "app_id": "1603408681013331",
                "expires_at": 1801766928,
                "data_access_expires_at": 1801766928,
            },
            "123",
            datetime(2026, 11, 6, tzinfo=UTC),
        )


@pytest.mark.unit
def test_missing_expiry_is_not_treated_as_never() -> None:
    with pytest.raises(CollectionError):
        validate_metadata(
            {"is_valid": True, "type": "PAGE", "profile_id": "123", "app_id": "1603408681013331", "data_access_expires_at": 0},
            "123",
            datetime(2026, 11, 6, tzinfo=UTC),
        )


@pytest.mark.unit
def test_missing_data_expiry_is_not_treated_as_unlimited() -> None:
    with pytest.raises(CollectionError):
        validate_metadata(
            {"is_valid": True, "type": "PAGE", "profile_id": "123", "app_id": "1603408681013331", "expires_at": 0}, "123", datetime(2026, 11, 6, tzinfo=UTC)
        )


@pytest.mark.unit
def test_expired_data_access_is_rejected_even_with_never_expiring_token() -> None:
    with pytest.raises(CollectionError):
        validate_metadata(
            {"is_valid": True, "type": "PAGE", "profile_id": "123", "app_id": "1603408681013331", "expires_at": 0, "data_access_expires_at": 1801766928},
            "123",
            datetime(2028, 1, 1, tzinfo=UTC),
        )


@pytest.mark.unit
def test_invalid_token_is_rejected() -> None:
    with pytest.raises(CollectionError):
        validate_metadata({"is_valid": False}, "123", datetime(2026, 11, 6, tzinfo=UTC))


@pytest.mark.unit
def test_unscheduled_data_access_deadline_is_distinct() -> None:
    status = validate_metadata(
        {"is_valid": True, "type": "PAGE", "profile_id": "123", "app_id": "1603408681013331", "expires_at": 0, "data_access_expires_at": 0},
        "123",
        datetime(2026, 11, 6, tzinfo=UTC),
    )
    assert status.summary() == "Token de página válido; caducidad del token: nunca. Acceso a datos: sin fecha declarada."


@pytest.mark.boundary
def test_wrong_identity_does_not_overwrite_keyring() -> None:
    store = MemorySecrets()
    store.set_password(SERVICE, "123", "existing")
    reader = ScriptedGraph([{"id": "user"}])
    with pytest.raises(CollectionError):
        register_page_token(store, reader, "123", "new", datetime(2026, 11, 6, tzinfo=UTC))
    assert store.get_password(SERVICE, "123") == "existing"


@pytest.mark.boundary
def test_validated_page_token_is_registered() -> None:
    store = MemorySecrets()
    reader = ScriptedGraph(
        [
            {"id": "123"},
            {
                "data": {
                    "is_valid": True,
                    "type": "PAGE",
                    "profile_id": "123",
                    "app_id": "1603408681013331",
                    "expires_at": 0,
                    "data_access_expires_at": 1801766928,
                }
            },
        ]
    )
    status = register_page_token(store, reader, "123", "new", datetime(2026, 11, 6, tzinfo=UTC))
    assert store.get_password(SERVICE, "123") == "new"
    assert status.data_access_expires_at == 1801766928
    assert reader.calls[-1] == ("debug_token", {"input_token": "new"})


@pytest.mark.boundary
def test_near_data_access_deadline_warns(messages: list[str]) -> None:
    reader = ScriptedGraph(
        [
            {"id": "123"},
            {
                "data": {
                    "is_valid": True,
                    "type": "PAGE",
                    "profile_id": "123",
                    "app_id": "1603408681013331",
                    "expires_at": 0,
                    "data_access_expires_at": 1794009600,
                }
            },
        ]
    )
    inspect_token(reader, "secret", "123", datetime(2026, 11, 6, tzinfo=UTC))
    assert len(messages) == 1


@pytest.mark.boundary
def test_malformed_debug_response_is_rejected() -> None:
    reader = ScriptedGraph([{"id": "123"}, {"data": []}])
    with pytest.raises(CollectionError):
        inspect_token(reader, "secret", "123", datetime(2026, 11, 6, tzinfo=UTC))
