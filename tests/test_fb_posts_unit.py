import unittest
from datetime import UTC, date, datetime

from keyring.backends.null import Keyring

from fb_posts_lib.credentials import SERVICE, read_token, require_native, save_token
from fb_posts_lib.models import SITE_ZONE, CollectionError, GraphError, PostInfo, latest_date, post_info, resolve_period
from fb_posts_lib.transport import RejectRedirects, decode_response, sanitize_pagination
from tests.fb_posts_doubles import MemorySecrets, UnavailableSecrets


class DateTests(unittest.TestCase):
    def test_explicit_end_day_is_inclusive(self):
        period = resolve_period(date(2026, 1, 1), date(2026, 1, 31), datetime(2026, 2, 2, tzinfo=UTC))
        self.assertEqual(period.start.isoformat(), "2026-01-01T00:00:00-03:00")
        self.assertEqual(period.end.isoformat(), "2026-02-01T00:00:00-03:00")

    def test_default_end_is_exact_supplied_instant(self):
        now = datetime(2026, 1, 5, 20, 1, 2, tzinfo=UTC)
        self.assertEqual(resolve_period(date(2026, 1, 1), None, now).end, now)

    def test_reversed_dates_rejected(self):
        with self.assertRaises(CollectionError):
            resolve_period(date(2026, 2, 1), date(2026, 1, 1), datetime(2026, 2, 2, tzinfo=UTC))

    def test_future_initial_default_end_rejected(self):
        with self.assertRaises(CollectionError):
            resolve_period(date(2026, 2, 1), None, datetime(2026, 1, 1, tzinfo=UTC))

    def test_latest_converts_to_previous_local_day(self):
        self.assertEqual(latest_date(["2026-01-06T01:48:35+0000"]), date(2026, 1, 5))

    def test_latest_compares_instants_not_strings(self):
        self.assertEqual(latest_date(["2026-01-06T01:00:00+0000", "2026-01-05T23:00:00-0300"]), date(2026, 1, 5))

    def test_latest_empty_rejected(self):
        with self.assertRaises(CollectionError):
            latest_date([])

    def test_latest_naive_rejected(self):
        with self.assertRaises(CollectionError):
            latest_date(["2026-01-05T12:00:00"])

    def test_latest_malformed_rejected(self):
        with self.assertRaises(CollectionError):
            latest_date(["invalid"])

    def test_canonical_timezone(self):
        self.assertEqual(SITE_ZONE.key, "America/Argentina/Buenos_Aires")


class PostInfoTests(unittest.TestCase):
    def test_parses_aware_date_without_changing_post(self):
        for timestamp in ("2026-01-06T01:48:35+0000", "2026-01-06T01:48:35Z", "2026-01-05T22:48:35-03:00"):
            with self.subTest(timestamp=timestamp):
                post = {"id": "123_1", "created_time": timestamp}
                info = post_info(post)
                self.assertEqual(info.id, "123_1")
                self.assertEqual(info.created_time.isoformat(), "2026-01-05T22:48:35-03:00")
                self.assertEqual(post["created_time"], timestamp)

    def test_missing_date_preserves_null(self):
        self.assertEqual(post_info({"id": "123_1"}), PostInfo("123_1", None))
        self.assertEqual(post_info({"id": "123_1", "created_time": None}), PostInfo("123_1", None))

    def test_invalid_id_rejected(self):
        for identifier in (None, 123, "invalid"):
            with self.subTest(identifier=identifier), self.assertRaises(CollectionError):
                post_info({"id": identifier})

    def test_invalid_or_naive_date_rejected(self):
        for timestamp in ("invalid", "2026-01-05T12:00:00", 123):
            with self.subTest(timestamp=timestamp), self.assertRaises(CollectionError):
                post_info({"id": "123_1", "created_time": timestamp})


class CredentialTests(unittest.TestCase):
    def test_read_failure_is_safe(self):
        with self.assertRaises(CollectionError) as caught:
            read_token(UnavailableSecrets(), "123")
        self.assertEqual(str(caught.exception), "No se pudo leer la credencial del keyring.")

    def test_save_failure_is_safe(self):
        with self.assertRaises(CollectionError) as caught:
            save_token(UnavailableSecrets(), "123", "SECRET")
        self.assertEqual(str(caught.exception), "No se pudo guardar la credencial en el keyring.")

    def test_insecure_backend_rejected(self):
        with self.assertRaises(CollectionError):
            require_native(Keyring())

    def test_registration_and_replacement(self):
        store = MemorySecrets()
        save_token(store, "123", "first")
        save_token(store, "123", "second")
        self.assertEqual(read_token(store, "123"), "second")
        self.assertEqual(store.values, {(SERVICE, "123"): "second"})

    def test_missing_credential(self):
        with self.assertRaises(CollectionError):
            read_token(MemorySecrets(), "123")

    def test_empty_token_not_saved(self):
        store = MemorySecrets()
        with self.assertRaises(CollectionError):
            save_token(store, "123", " ")
        self.assertEqual(store.values, {})


class TransportTests(unittest.TestCase):
    def test_deprecated_field_identified(self):
        with self.assertRaises(GraphError) as caught:
            decode_response(
                b'{"error":{"code":12,"message":"(#12) deprecate_post_aggregated_fields_for_attachement is deprecated for versions v3.3 and higher"}}'
            )
        self.assertEqual(caught.exception.field_rejection, True)

    def test_invalid_json(self):
        with self.assertRaises(CollectionError):
            decode_response(b"not json")

    def test_non_object_json(self):
        with self.assertRaises(CollectionError):
            decode_response(b"[]")

    def test_nonfinite_json(self):
        with self.assertRaises(CollectionError):
            decode_response(b'{"value": NaN}')

    def test_expired_token_error_safe(self):
        with self.assertRaises(GraphError) as caught:
            decode_response(b'{"error":{"code":190,"message":"TOKEN_SECRET"}}')
        self.assertEqual(
            str(caught.exception),
            "Facebook rechazó el token (código 190). Obtenga un token de página nuevo y guárdelo con: uv run fb_posts.py credential set",
        )
        self.assertEqual(caught.exception.field_rejection, False)

    def test_expired_session_subcode_has_safe_actionable_diagnostic(self):
        with self.assertRaises(GraphError) as caught:
            decode_response(b'{"error":{"code":190,"error_subcode":463,"message":"TOKEN_SECRET"}}')
        self.assertEqual(
            str(caught.exception),
            "El token de Facebook caducó (código 190, subcódigo 463). Obtenga un token de página nuevo y guárdelo con: uv run fb_posts.py credential set",
        )
        self.assertEqual(caught.exception.subcode, 463)
        self.assertEqual(caught.exception.field_rejection, False)

    def test_optional_field_identified(self):
        with self.assertRaises(GraphError) as caught:
            decode_response(b'{"error":{"code":100,"message":"Tried accessing nonexisting field (old)"}}')
        self.assertEqual(caught.exception.field_rejection, True)

    def test_general_permission_error_is_fatal(self):
        with self.assertRaises(GraphError) as caught:
            decode_response(b'{"error":{"code":10,"message":"Requires pages_read_engagement permission"}}')
        self.assertEqual(caught.exception.field_rejection, False)

    def test_pagination_secrets_removed_media_unchanged(self):
        value = {
            "attachments": {"media": {"src": "https://img.invalid/x?x=%2F"}, "paging": {"next": "https://graph.facebook.com/a?access_token=SECRET&after=x"}}
        }
        self.assertEqual(
            sanitize_pagination(value),
            {"attachments": {"media": {"src": "https://img.invalid/x?x=%2F"}, "paging": {"next": "https://graph.facebook.com/a?after=x"}}},
        )

    def test_redirect_does_not_forward_authorization(self):
        with self.assertRaises(CollectionError):
            RejectRedirects().redirect_request(None, None, 302, "", {}, "https://evil.invalid")
