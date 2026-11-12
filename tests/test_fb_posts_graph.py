from datetime import UTC, date, datetime

import pytest

from fb_posts_lib.models import CollectionError, GraphError, resolve_period
from fb_posts_lib.posts import FacebookPosts
from tests.fb_posts_doubles import FieldGraph, ScriptedGraph


@pytest.mark.boundary
def test_generic_unsupported_field_skipped_only_after_node_probe(messages: list[str]) -> None:
    reader = ScriptedGraph([GraphError(100), {"id": "123_1"}])
    source = FacebookPosts(reader, "123", "v26.0")
    assert source.fetch_fields("123_1", ("allowed_advertising_objectives",)) == {}
    assert reader.calls[-1] == ("123_1", {"fields": "id,message,created_time,permalink_url"})
    assert messages == ["Publicación 123_1: campo no disponible: allowed_advertising_objectives."]


@pytest.mark.boundary
def test_missing_node_is_not_silently_skipped() -> None:
    reader = ScriptedGraph([GraphError(100), GraphError(100)])
    source = FacebookPosts(reader, "123", "v26.0")
    with pytest.raises(GraphError):
        source.fetch_fields("123_1", ("allowed_advertising_objectives",))


@pytest.mark.boundary
def test_optional_permission_error_requires_core_access_probe(messages: list[str]) -> None:
    reader = ScriptedGraph([GraphError(200), {"id": "123_1", "message": "Readable"}])
    source = FacebookPosts(reader, "123", "v26.0")
    assert source.fetch_fields("123_1", ("coordinates",)) == {}
    assert messages == ["Publicación 123_1: campo no disponible: coordinates."]


@pytest.mark.boundary
def test_general_permission_failure_is_not_skipped() -> None:
    reader = ScriptedGraph([GraphError(200), GraphError(200)])
    source = FacebookPosts(reader, "123", "v26.0")
    with pytest.raises(GraphError):
        source.fetch_fields("123_1", ("coordinates",))


@pytest.mark.boundary
def test_wrong_page_identity() -> None:
    source = FacebookPosts(ScriptedGraph([{"id": "9"}]), "123", "v26.0")
    with pytest.raises(CollectionError):
        source.verify_identity()


@pytest.mark.boundary
def test_full_post_beyond_columns_and_publisher() -> None:
    reader = FieldGraph()
    source = FacebookPosts(reader, "123", "v26.0")
    post = source.full_post("123_1")
    assert post["story"] == "Una historia"
    assert post["admin_creator"] == {"id": "7", "name": "Persona"}
    assert post["attachments"]["data"][0]["media"]["image"]["src"] == "https://media.invalid/img?x=%2F"
    assert {path for path, parameters in reader.calls} == {"123_1"}


@pytest.mark.boundary
def test_rejected_field_isolated(messages: list[str]) -> None:
    source = FacebookPosts(FieldGraph(denied="story"), "123", "v26.0")
    post = source.full_post("123_1")
    assert post.get("story") == None
    assert post["message"] == "Texto sin firma"
    assert messages == ["Publicación 123_1: campo no disponible: story."]


@pytest.mark.boundary
def test_missing_publisher_direct_lookup() -> None:
    reader = FieldGraph(publisher=False)
    source = FacebookPosts(reader, "123", "v26.0")
    post = source.full_post("123_1")
    assert post.get("admin_creator") == None
    assert reader.calls[-1] == ("123_1", {"fields": "admin_creator"})


@pytest.mark.boundary
def test_general_failure_is_not_optional() -> None:
    source = FacebookPosts(ScriptedGraph([GraphError(190)]), "123", "v26.0")
    with pytest.raises(GraphError):
        source.full_post("123_1")


@pytest.mark.boundary
def test_fallback_inventory_logs_diagnostic(messages: list[str]) -> None:
    reader = FieldGraph(metadata=False)
    source = FacebookPosts(reader, "123", "v26.0")
    post = source.full_post("123_1")
    assert post["story"] == "Una historia"
    assert messages == ["Publicación 123_1: sin metadatos de campos; se usa el inventario v26.0; no se garantiza cobertura exhaustiva."]
    requested = {name for _, parameters in reader.calls for name in parameters["fields"].split(",")}
    assert (
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
        is True
    )


@pytest.mark.boundary
def test_metadata_can_include_fields_omitted_from_fallback() -> None:
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
    assert set(names).issubset(source.readable_fields("123_1")) is True


@pytest.mark.boundary
def test_unknown_version_without_metadata_fails() -> None:
    source = FacebookPosts(FieldGraph(metadata=False), "123", "v99.0")
    with pytest.raises(CollectionError):
        source.full_post("123_1")


@pytest.mark.boundary
def test_pagination_retains_fixed_bounds() -> None:
    reader = ScriptedGraph([{"data": [{"id": "123_1"}], "paging": {"next": "IGNORED_SECRET_URL", "cursors": {"after": "abc"}}}, {"data": [{"id": "123_2"}]}])
    source = FacebookPosts(reader, "123", "v26.0")
    period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
    assert list(source.pages(period)) == [[{"id": "123_1"}], [{"id": "123_2"}]]
    assert reader.calls[1][1] == {**reader.calls[0][1], "after": "abc"}


@pytest.mark.boundary
def test_repeated_cursor_fails() -> None:
    payload = {"data": [], "paging": {"next": "not followed", "cursors": {"after": "abc"}}}
    source = FacebookPosts(ScriptedGraph([payload, payload]), "123", "v26.0")
    period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
    with pytest.raises(CollectionError):
        list(source.pages(period))


@pytest.mark.boundary
def test_invalid_post_id_fails() -> None:
    source = FacebookPosts(ScriptedGraph([{"data": [{"message": "Missing ID"}]}]), "123", "v26.0")
    period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
    with pytest.raises(CollectionError):
        list(source.pages(period))
