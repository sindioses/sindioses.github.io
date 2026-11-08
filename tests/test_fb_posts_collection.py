import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path

from fb_posts import app
from fb_posts_lib.collection import collect_posts
from fb_posts_lib.models import CollectionError, Counts, Post, resolve_period
from fb_posts_lib.storage import ROOT, open_database
from tests.fb_posts_doubles import FailingPageSource, PageSource


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()
        self.enterContext(redirect_stdout(self.output))

    def test_interrupt_preserves_stored_posts_in_current_page(self):
        class InterruptedSource(FailingPageSource):
            def full_post(self, identifier: str) -> Post:
                if identifier == "123_3":
                    raise KeyboardInterrupt
                return super().full_post(identifier)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            counts = Counts()
            period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
            with self.assertRaises(KeyboardInterrupt), open_database(path) as connection:
                collect_posts(InterruptedSource(), connection, period, False, counts)
            with open_database(path) as connection:
                self.assertEqual(connection.execute("SELECT id FROM posts ORDER BY id").fetchall(), [("123_1",), ("123_2",)])
            self.assertEqual(counts, Counts(read=3, inserted=2))
            self.assertEqual(self.output.getvalue().splitlines(), ["Guardado post 123_1 (fecha desconocida)", "Guardado post 123_2 (fecha desconocida)"])

    def test_failed_post_preserves_stored_posts_in_current_page(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            counts = Counts()
            period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
            with self.assertRaises(CollectionError), open_database(path) as connection:
                collect_posts(FailingPageSource(), connection, period, False, counts)
            with open_database(path) as connection:
                self.assertEqual(connection.execute("SELECT id FROM posts ORDER BY id").fetchall(), [("123_1",), ("123_2",)])
            self.assertEqual(counts, Counts(read=3, inserted=2))
            self.assertEqual(self.output.getvalue().splitlines(), ["Guardado post 123_1 (fecha desconocida)", "Guardado post 123_2 (fecha desconocida)"])

    def test_batch_boundary_and_final_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            with open_database(path) as connection, closing(sqlite3.connect(path)) as observer:
                snapshots: list[int] = []

                class ObservedSource(PageSource):
                    def full_post(self, identifier: str) -> Post:
                        snapshots.append(observer.execute("SELECT count(*) FROM posts").fetchone()[0])
                        return super().full_post(identifier)

                source = ObservedSource([{"id": f"123_{index}"} for index in range(12)])
                period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
                collect_posts(source, connection, period, False, Counts())
                self.assertEqual(snapshots, [0] * 10 + [10] * 2)
                self.assertEqual(observer.execute("SELECT count(*) FROM posts").fetchone()[0], 12)

    def test_progress_includes_aware_publication_date(self):
        with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
            source = PageSource([{"id": "123_1", "created_time": "2026-01-06T01:48:35+0000"}])
            period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
            collect_posts(source, connection, period, False, Counts())
            self.assertEqual(self.output.getvalue().strip(), "Guardado post 123_1 (2026-01-05T22:48:35-03:00)")

    def test_partial_failure_retains_committed_page(self):
        with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
            source = PageSource([{"id": "123_1", "message": "Sin firma"}], fail_after_page=True)
            counts = Counts()
            period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
            with self.assertRaises(CollectionError):
                collect_posts(source, connection, period, False, counts)
            self.assertEqual(connection.execute("SELECT id FROM posts").fetchall(), [("123_1",)])
            self.assertEqual(counts.inserted, 1)

    def test_repeat_skips_without_full_retrieval_and_continues(self):
        with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
            period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
            collect_posts(PageSource([{"id": "123_1"}]), connection, period, False, Counts())
            self.output.truncate(0)
            self.output.seek(0)
            source = PageSource([{"id": "123_1"}, {"id": "123_2"}])
            counts = Counts()
            collect_posts(source, connection, period, False, counts)
            self.assertEqual(source.fetched, ["123_2"])
            self.assertEqual(counts, Counts(read=2, inserted=1, skipped=1))
            self.assertEqual(self.output.getvalue().splitlines(), ["Guardado post 123_2 (fecha desconocida)"])

    def test_forced_refresh_counts(self):
        with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
            source = PageSource([{"id": "123_1"}])
            period = resolve_period(date(2026, 1, 1), None, datetime(2026, 1, 5, tzinfo=UTC))
            collect_posts(source, connection, period, False, Counts())
            self.output.truncate(0)
            self.output.seek(0)
            counts = Counts()
            collect_posts(source, connection, period, True, counts)
            self.assertEqual(counts, Counts(read=1, updated=1))
            self.assertEqual(self.output.getvalue().splitlines(), ["Guardado post 123_1 (fecha desconocida)"])


class CliTests(unittest.TestCase):
    def test_cyclopts_converts_dates_without_custom_parser(self):
        _, values, _ = app.parse_args(["collect", "2026-01-01", "2026-01-31"])
        self.assertEqual(values.args, (date(2026, 1, 1), date(2026, 1, 31)))

    def test_cyclopts_accepts_latest_literal(self):
        _, values, _ = app.parse_args(["collect", "latest"])
        self.assertEqual(values.args[0], "latest")

    def test_invalid_cli_date_has_no_database_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-created.db"
            result = subprocess.run(
                [sys.executable, str(ROOT / "fb_posts.py"), "collect", "not-a-date", "--database", str(path)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.exists(), False)

    def test_help_works_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "fb_posts.py"), "collect", "--help"], cwd=directory, check=False, capture_output=True, text=True, encoding="utf-8"
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual("--force" in result.stdout, True)
