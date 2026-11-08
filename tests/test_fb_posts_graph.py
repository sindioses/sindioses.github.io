from datetime import UTC, date, datetime

from fb_posts_lib.models import CollectionError, GraphError, resolve_period
from fb_posts_lib.posts import FacebookPosts
from tests.fb_posts_doubles import FieldGraph, LoggedTestCase, ScriptedGraph


class GraphTests(LoggedTestCase):
    def test_generic_unsupported_field_skipped_only_after_node_probe(self):
        reader = ScriptedGraph([GraphError(100), {"id": "123_1"}])
        messages = self.messages
        source = FacebookPosts(reader, "123", "v26.0")
        self.assertEqual(source.fetch_fields("123_1", ("allowed_advertising_objectives",)), {})
        self.assertEqual(reader.calls[-1], ("123_1", {"fields": "id,message,created_time,permalink_url"}))
        self.assertEqual(messages, ["Publicación 123_1: campo no disponible: allowed_advertising_objectives."])

    def test_missing_node_is_not_silently_skipped(self):
        reader = ScriptedGraph([GraphError(100), GraphError(100)])
        source = FacebookPosts(reader, "123", "v26.0")
        with self.assertRaises(GraphError):
            source.fetch_fields("123_1", ("allowed_advertising_objectives",))

    def test_optional_permission_error_requires_core_access_probe(self):
        reader = ScriptedGraph([GraphError(200), {"id": "123_1", "message": "Readable"}])
        messages = self.messages
        source = FacebookPosts(reader, "123", "v26.0")
        self.assertEqual(source.fetch_fields("123_1", ("coordinates",)), {})
        self.assertEqual(messages, ["Publicación 123_1: campo no disponible: coordinates."])

    def test_general_permission_failure_is_not_skipped(self):
        reader = ScriptedGraph([GraphError(200), GraphError(200)])
        source = FacebookPosts(reader, "123", "v26.0")
        with self.assertRaises(GraphError):
            source.fetch_fields("123_1", ("coordinates",))

    def test_wrong_page_identity(self):
        source = FacebookPosts(ScriptedGraph([{"id": "9"}]), "123", "v26.0")
        with self.assertRaises(CollectionError):
            source.verify_identity()

    def test_full_post_beyond_columns_and_publisher(self):
        reader = FieldGraph()
        source = FacebookPosts(reader, "123", "v26.0")
        post = source.full_post("123_1")
        self.assertEqual(post["story"], "Una historia")
        self.assertEqual(post["admin_creator"], {"id": "7", "name": "Persona"})
        self.assertEqual(post["attachments"]["data"][0]["media"]["image"]["src"], "https://media.invalid/img?x=%2F")
        self.assertEqual({path for path, parameters in reader.calls}, {"123_1"})

    def test_rejected_field_isolated(self):
        messages = self.messages
        source = FacebookPosts(FieldGraph(denied="story"), "123", "v26.0")
        post = source.full_post("123_1")
        self.assertEqual(post.get("story"), None)
        self.assertEqual(post["message"], "Texto sin firma")
        self.assertEqual(messages, ["Publicación 123_1: campo no disponible: story."])

    def test_missing_publisher_direct_lookup(self):
        reader = FieldGraph(publisher=False)
        source = FacebookPosts(reader, "123", "v26.0")
        post = source.full_post("123_1")
        self.assertEqual(post.get("admin_creator"), None)
        self.assertEqual(reader.calls[-1], ("123_1", {"fields": "admin_creator"}))

    def test_general_failure_is_not_optional(self):
        source = FacebookPosts(ScriptedGraph([GraphError(190)]), "123", "v26.0")
        with self.assertRaises(GraphError):
            source.full_post("123_1")

    def test_fallback_inventory_logs_diagnostic(self):
        messages = self.messages
        reader = FieldGraph(metadata=False)
        source = FacebookPosts(reader, "123", "v26.0")
        post = source.full_post("123_1")
        self.assertEqual(post["story"], "Una historia")
        self.assertEqual(
            messages,
            ["Publicación 123_1: sin metadatos de campos; se usa el inventario v26.0; no se garantiza cobertura exhaustiva."],
        )
        requested = {name for _, parameters in reader.calls for name in parameters["fields"].split(",")}
        self.assertTrue(
            requested.isdisjoint(
                {
                    "allowed_advertising_objectives",
                    "caption",
                    "comments_mirroring_domain",
                    "description",
                    "is_app_share",
                    "link",
                    "name",
                    "object_id",
                    "source",
                    "type",
                }
            )
        )

    def test_metadata_can_include_fields_omitted_from_fallback(self):
        names = (
            "allowed_advertising_objectives",
            "caption",
            "comments_mirroring_domain",
            "description",
            "is_app_share",
            "link",
            "name",
            "object_id",
            "source",
            "type",
        )
        reader = ScriptedGraph([{"id": "123_1", "metadata": {"fields": [{"name": name} for name in names]}}])
        source = FacebookPosts(reader, "123", "v26.0")
        self.assertTrue(set(names).issubset(source.readable_fields("123_1")))

    def test_unknown_version_without_metadata_fails(self):
        source = FacebookPosts(FieldGraph(metadata=False), "123", "v99.0")
        with self.assertRaises(CollectionError):
            source.full_post("123_1")

    def test_pagination_retains_fixed_bounds(self):
        reader = ScriptedGraph(
            [{"data": [{"id": "123_1"}], "paging": {"next": "IGNORED_SECRET_URL", "cursors": {"after": "abc"}}}, {"data": [{"id": "123_2"}]}]
        )
        source = FacebookPosts(reader, "123", "v26.0")
        period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
        self.assertEqual(list(source.pages(period)), [[{"id": "123_1"}], [{"id": "123_2"}]])
        self.assertEqual(reader.calls[1][1], {**reader.calls[0][1], "after": "abc"})

    def test_repeated_cursor_fails(self):
        payload = {"data": [], "paging": {"next": "not followed", "cursors": {"after": "abc"}}}
        source = FacebookPosts(ScriptedGraph([payload, payload]), "123", "v26.0")
        period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
        with self.assertRaises(CollectionError):
            list(source.pages(period))

    def test_invalid_post_id_fails(self):
        source = FacebookPosts(ScriptedGraph([{"data": [{"message": "Missing ID"}]}]), "123", "v26.0")
        period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
        with self.assertRaises(CollectionError):
            list(source.pages(period))
