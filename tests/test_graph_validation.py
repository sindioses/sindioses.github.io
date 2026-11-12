from datetime import UTC, date, datetime

import pytest

from fb_posts_lib.models import CollectionError, GraphError, Post, resolve_period
from fb_posts_lib.posts import FacebookPosts
from tests.fb_posts_doubles import ScriptedGraph


@pytest.mark.parametrize("payload", [{"data": {}}, {"data": [], "paging": []}, {"data": [], "paging": {"next": "unused", "cursors": {}}}])
@pytest.mark.boundary
def test_listing_rejects_invalid_structure(payload: Post) -> None:
    source = FacebookPosts(ScriptedGraph([payload]), "123", "v26.0")
    period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
    with pytest.raises(CollectionError):
        list(source.pages(period))


@pytest.mark.parametrize("payload", [{"metadata": {"fields": [42]}}, {"metadata": {"fields": [{"name": "Invalid field"}]}}])
@pytest.mark.boundary
def test_discovery_rejects_invalid_field_metadata(payload: Post) -> None:
    source = FacebookPosts(ScriptedGraph([payload]), "123", "v26.0")
    with pytest.raises(CollectionError):
        source.readable_fields("123_1")


@pytest.mark.boundary
def test_core_field_rejection_is_fatal() -> None:
    source = FacebookPosts(ScriptedGraph([GraphError(100, field_rejection=True)]), "123", "v26.0")
    with pytest.raises(GraphError):
        source.fetch_fields("123_1", ("message",))


@pytest.mark.boundary
def test_field_response_must_match_requested_post() -> None:
    source = FacebookPosts(ScriptedGraph([{"id": "123_2"}]), "123", "v26.0")
    with pytest.raises(CollectionError, match="no corresponde"):
        source.fetch_fields("123_1", ("message",))


@pytest.mark.boundary
def test_access_probe_must_match_requested_post() -> None:
    source = FacebookPosts(ScriptedGraph([GraphError(100), {"id": "123_2"}]), "123", "v26.0")
    with pytest.raises(CollectionError, match="ya no está disponible"):
        source.fetch_fields("123_1", ("message",))


@pytest.mark.unit
def test_invalid_page_is_rejected_before_any_request() -> None:
    reader = ScriptedGraph([])
    with pytest.raises(CollectionError, match="debe ser numérico"):
        FacebookPosts(reader, "invalid", "v26.0")
    assert reader.calls == []
