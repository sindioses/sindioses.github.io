from datetime import UTC, date, datetime

import pytest

from fb_posts_lib.models import CollectionError, PostInfo, latest_date, post_info, resolve_period


@pytest.mark.unit
def test_explicit_end_day_is_inclusive() -> None:
    period = resolve_period(date(2026, 1, 1), date(2026, 1, 31), datetime(2026, 2, 2, tzinfo=UTC))
    assert period.start.isoformat() == "2026-01-01T00:00:00-03:00"
    assert period.end.isoformat() == "2026-02-01T00:00:00-03:00"


@pytest.mark.unit
def test_default_end_is_exact_supplied_instant() -> None:
    now = datetime(2026, 1, 5, 20, 1, 2, tzinfo=UTC)
    assert resolve_period(date(2026, 1, 1), None, now).end == now


@pytest.mark.unit
def test_reversed_dates_rejected() -> None:
    with pytest.raises(CollectionError):
        resolve_period(date(2026, 2, 1), date(2026, 1, 1), datetime(2026, 2, 2, tzinfo=UTC))


@pytest.mark.unit
def test_future_initial_default_end_rejected() -> None:
    with pytest.raises(CollectionError):
        resolve_period(date(2026, 2, 1), None, datetime(2026, 1, 1, tzinfo=UTC))


@pytest.mark.unit
def test_latest_converts_to_previous_local_day() -> None:
    assert latest_date(["2026-01-06T01:48:35+0000"]) == date(2026, 1, 5)


@pytest.mark.unit
def test_latest_compares_instants_not_strings() -> None:
    assert latest_date(["2026-01-06T01:00:00+0000", "2026-01-05T23:00:00-0300"]) == date(2026, 1, 5)


@pytest.mark.unit
def test_latest_empty_rejected() -> None:
    with pytest.raises(CollectionError):
        latest_date([])


@pytest.mark.unit
def test_latest_naive_rejected() -> None:
    with pytest.raises(CollectionError):
        latest_date(["2026-01-05T12:00:00"])


@pytest.mark.unit
def test_latest_malformed_rejected() -> None:
    with pytest.raises(CollectionError):
        latest_date(["invalid"])


@pytest.mark.parametrize("timestamp", ("2026-01-06T01:48:35+0000", "2026-01-06T01:48:35Z", "2026-01-05T22:48:35-03:00"))
@pytest.mark.unit
def test_parses_aware_date_without_changing_post(timestamp: str) -> None:
    post = {"id": "123_1", "created_time": timestamp}
    info = post_info(post)
    assert info.id == "123_1"
    assert info.created_time.isoformat() == "2026-01-05T22:48:35-03:00"
    assert post["created_time"] == timestamp


@pytest.mark.parametrize("post", [{"id": "123_1"}, {"id": "123_1", "created_time": None}])
@pytest.mark.unit
def test_missing_date_preserves_null(post: dict[str, str | None]) -> None:
    assert post_info(post) == PostInfo("123_1", None)


@pytest.mark.parametrize("identifier", (None, 123, "invalid"))
@pytest.mark.unit
def test_invalid_id_rejected(identifier: str | int | None) -> None:
    with pytest.raises(CollectionError):
        post_info({"id": identifier})


@pytest.mark.parametrize("timestamp", ("invalid", "2026-01-05T12:00:00", 123))
@pytest.mark.unit
def test_invalid_or_naive_date_rejected(timestamp: str | int | None) -> None:
    with pytest.raises(CollectionError):
        post_info({"id": "123_1", "created_time": timestamp})
