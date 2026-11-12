import re
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from fb_posts import app
from fb_posts_lib.collection import collect_posts
from fb_posts_lib.models import CollectionError, Counts, resolve_period
from fb_posts_lib.storage import open_database
from tests.fb_posts_doubles import FailingPageSource, InterruptedSource, ObservedSource, PageSource
from tests.process_support import ROOT


@pytest.mark.integration
def test_interrupt_preserves_stored_posts_in_current_page(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.db"
        counts = Counts()
        period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
        with pytest.raises(KeyboardInterrupt), open_database(path) as connection:
            collect_posts(InterruptedSource(), connection, period, False, counts)
        with open_database(path) as connection:
            assert [tuple(row) for row in connection.execute("SELECT id FROM posts ORDER BY id").fetchall()] == [("123_1",), ("123_2",)]
        assert counts == Counts(read=3, inserted=2)
        assert capsys.readouterr().out.splitlines() == ["Guardado post 123_1 (fecha desconocida)", "Guardado post 123_2 (fecha desconocida)"]


@pytest.mark.integration
def test_failed_post_preserves_stored_posts_in_current_page(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.db"
        counts = Counts()
        period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
        with pytest.raises(CollectionError), open_database(path) as connection:
            collect_posts(FailingPageSource(), connection, period, False, counts)
        with open_database(path) as connection:
            assert [tuple(row) for row in connection.execute("SELECT id FROM posts ORDER BY id").fetchall()] == [("123_1",), ("123_2",)]
        assert counts == Counts(read=3, inserted=2)
        assert capsys.readouterr().out.splitlines() == ["Guardado post 123_1 (fecha desconocida)", "Guardado post 123_2 (fecha desconocida)"]


@pytest.mark.integration
def test_batch_boundary_and_final_commit() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.db"
        with open_database(path) as connection, closing(sqlite3.connect(path)) as observer:
            snapshots: list[int] = []
            source = ObservedSource([{"id": f"123_{index}"} for index in range(12)], observer, snapshots)
            period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
            collect_posts(source, connection, period, False, Counts())
            assert snapshots == [0] * 10 + [10] * 2
            assert observer.execute("SELECT count(*) FROM posts").fetchone()[0] == 12


@pytest.mark.integration
def test_progress_includes_aware_publication_date(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        source = PageSource([{"id": "123_1", "created_time": "2026-01-06T01:48:35+0000"}])
        period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
        collect_posts(source, connection, period, False, Counts())
        assert capsys.readouterr().out.strip() == "Guardado post 123_1 (2026-01-05T22:48:35-03:00)"


@pytest.mark.integration
def test_partial_failure_retains_committed_page() -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        source = PageSource([{"id": "123_1", "message": "Sin firma"}], fail_after_page=True)
        counts = Counts()
        period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
        with pytest.raises(CollectionError):
            collect_posts(source, connection, period, False, counts)
        assert [tuple(row) for row in connection.execute("SELECT id FROM posts").fetchall()] == [("123_1",)]
        assert counts.inserted == 1


@pytest.mark.integration
def test_repeat_skips_without_full_retrieval_and_continues(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
        collect_posts(PageSource([{"id": "123_1"}]), connection, period, False, Counts())
        capsys.readouterr()
        source = PageSource([{"id": "123_1"}, {"id": "123_2"}])
        counts = Counts()
        collect_posts(source, connection, period, False, counts)
        assert source.fetched == ["123_2"]
        assert counts == Counts(read=2, inserted=1, skipped=1)
        assert capsys.readouterr().out.splitlines() == ["Guardado post 123_2 (fecha desconocida)"]


@pytest.mark.integration
def test_forced_refresh_counts(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        source = PageSource([{"id": "123_1"}])
        period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
        collect_posts(source, connection, period, False, Counts())
        capsys.readouterr()
        counts = Counts()
        collect_posts(source, connection, period, True, counts)
        assert counts == Counts(read=1, updated=1)
        assert capsys.readouterr().out.splitlines() == ["Guardado post 123_1 (fecha desconocida)"]


@pytest.mark.integration
def test_forced_collection_overwrites_message_when_requested() -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
        collect_posts(PageSource([{"id": "123_1", "message": "Texto editorial"}]), connection, period, False, Counts())
        collect_posts(PageSource([{"id": "123_1", "message": "Texto de Facebook"}]), connection, period, True, Counts(), overwrite_message=True)
        assert connection.execute("SELECT message FROM posts").fetchone()["message"] == "Texto de Facebook"


@pytest.mark.integration
def test_overwrite_message_defaults_to_false() -> None:
    _, values, _ = app.parse_args(["collect", "2026-01-16", "--force"])
    values.apply_defaults()
    assert values.arguments["overwrite_message"] == False


@pytest.mark.integration
def test_overwrite_message_long_option() -> None:
    _, values, _ = app.parse_args(["collect", "2026-01-16", "--force", "--overwrite-message"])
    assert values.kwargs["overwrite_message"] == True


@pytest.mark.integration
def test_overwrite_message_short_option() -> None:
    _, values, _ = app.parse_args(["collect", "2026-01-16", "--force", "-M"])
    assert values.kwargs["overwrite_message"] == True


@pytest.mark.integration
def test_invalid_cli_date_has_no_database_effect() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "not-created.db"
        result = subprocess.run(
            [sys.executable, str(ROOT / "fb_posts.py"), "collect", "not-a-date", "--database", str(path)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert result.returncode == 2
        assert path.exists() == False


@pytest.mark.integration
def test_help_works_outside_repository() -> None:
    with tempfile.TemporaryDirectory() as directory:
        result = subprocess.run(
            [sys.executable, str(ROOT / "fb_posts.py"), "collect", "--help"], cwd=directory, check=False, capture_output=True, text=True, encoding="utf-8"
        )
        assert result.returncode == 0
        assert bool(re.search(r"--force\b", result.stdout)) is True
