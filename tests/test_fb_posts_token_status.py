import unittest
from datetime import UTC, datetime

from fb_posts_lib.credentials import SERVICE, register_page_token
from fb_posts_lib.models import CollectionError
from fb_posts_lib.token_status import inspect_token, validate_metadata
from tests.fb_posts_doubles import LoggedTestCase, MemorySecrets, ScriptedGraph


class TokenMetadataTests(unittest.TestCase):
    def test_no_scheduled_expiration_with_separate_data_deadline(self):
        status = validate_metadata(
            {"is_valid": True, "type": "PAGE", "profile_id": "123", "app_id": "1603408681013331", "expires_at": 0, "data_access_expires_at": 1801766928},
            "123",
            datetime(2026, 11, 6, tzinfo=UTC),
        )
        self.assertEqual(status.data_access_expires_at, 1801766928)
        self.assertEqual(status.summary().startswith("Token de página válido; caducidad del token: nunca. Acceso a datos: "), True)

    def test_user_token_is_rejected(self):
        with self.assertRaises(CollectionError):
            validate_metadata(
                {"is_valid": True, "type": "USER", "profile_id": "123", "app_id": "1603408681013331", "expires_at": 0, "data_access_expires_at": 0},
                "123",
                datetime(2026, 11, 6, tzinfo=UTC),
            )

    def test_wrong_app_is_rejected(self):
        with self.assertRaises(CollectionError):
            validate_metadata(
                {"is_valid": True, "type": "PAGE", "profile_id": "123", "app_id": "wrong", "expires_at": 0, "data_access_expires_at": 0},
                "123",
                datetime(2026, 11, 6, tzinfo=UTC),
            )

    def test_short_lived_page_token_is_rejected(self):
        with self.assertRaises(CollectionError):
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

    def test_missing_expiry_is_not_treated_as_never(self):
        with self.assertRaises(CollectionError):
            validate_metadata(
                {"is_valid": True, "type": "PAGE", "profile_id": "123", "app_id": "1603408681013331", "data_access_expires_at": 0},
                "123",
                datetime(2026, 11, 6, tzinfo=UTC),
            )

    def test_missing_data_expiry_is_not_treated_as_unlimited(self):
        with self.assertRaises(CollectionError):
            validate_metadata(
                {"is_valid": True, "type": "PAGE", "profile_id": "123", "app_id": "1603408681013331", "expires_at": 0},
                "123",
                datetime(2026, 11, 6, tzinfo=UTC),
            )

    def test_expired_data_access_is_rejected_even_with_never_expiring_token(self):
        with self.assertRaises(CollectionError):
            validate_metadata(
                {"is_valid": True, "type": "PAGE", "profile_id": "123", "app_id": "1603408681013331", "expires_at": 0, "data_access_expires_at": 1801766928},
                "123",
                datetime(2028, 1, 1, tzinfo=UTC),
            )

    def test_invalid_token_is_rejected(self):
        with self.assertRaises(CollectionError):
            validate_metadata({"is_valid": False}, "123", datetime(2026, 11, 6, tzinfo=UTC))

    def test_unscheduled_data_access_deadline_is_distinct(self):
        status = validate_metadata(
            {"is_valid": True, "type": "PAGE", "profile_id": "123", "app_id": "1603408681013331", "expires_at": 0, "data_access_expires_at": 0},
            "123",
            datetime(2026, 11, 6, tzinfo=UTC),
        )
        self.assertEqual(status.summary(), "Token de página válido; caducidad del token: nunca. Acceso a datos: sin fecha declarada.")


class TokenWorkflowTests(LoggedTestCase):
    def test_wrong_identity_does_not_overwrite_keyring(self):
        store = MemorySecrets()
        store.set_password(SERVICE, "123", "existing")
        reader = ScriptedGraph([{"id": "user"}])
        with self.assertRaises(CollectionError):
            register_page_token(store, reader, "123", "new", datetime(2026, 11, 6, tzinfo=UTC))
        self.assertEqual(store.get_password(SERVICE, "123"), "existing")

    def test_validated_page_token_is_registered(self):
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
        self.assertEqual(store.get_password(SERVICE, "123"), "new")
        self.assertEqual(status.data_access_expires_at, 1801766928)
        self.assertEqual(reader.calls[-1], ("debug_token", {"input_token": "new"}))

    def test_near_data_access_deadline_warns(self):
        messages = self.messages
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
        self.assertEqual(len(messages), 1)

    def test_malformed_debug_response_is_rejected(self):
        reader = ScriptedGraph([{"id": "123"}, {"data": []}])
        with self.assertRaises(CollectionError):
            inspect_token(reader, "secret", "123", datetime(2026, 11, 6, tzinfo=UTC))
