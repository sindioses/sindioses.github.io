import json
import sqlite3
import tempfile
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest

from fb_posts_lib.models import CollectionError
from fb_posts_lib.storage import DEFAULT_DATABASE, SCHEMA, check_schema, open_database, save_post, stored_latest


@pytest.mark.integration
def test_schema_accepts_timestamp_column() -> None:
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.execute(SCHEMA)
        assert check_schema(connection) is True


@pytest.mark.parametrize("schema", (SCHEMA.replace("created_time TIMESTAMP", "created_time TEXT"), SCHEMA.replace("message TEXT", "message INTEGER")))
@pytest.mark.integration
def test_schema_rejects_other_column_types(schema: str | int | None) -> None:
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.execute(schema)
        with pytest.raises(CollectionError):
            check_schema(connection)


@pytest.mark.integration
def test_force_inserts_new_ids_with_null_metadata() -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        with connection:
            assert save_post(connection, {"id": "123_1"}, True) == "inserted"
        assert tuple(connection.execute("SELECT author, category, slug FROM posts").fetchone()) == (None, None, None)


@pytest.mark.integration
def test_table_triggers_are_incompatible() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.db"
        with open_database(path) as connection:
            connection.execute("CREATE TRIGGER posts_trigger AFTER INSERT ON posts BEGIN SELECT 1; END")
        before = path.read_bytes()
        with pytest.raises(CollectionError), open_database(path):
            pass
        assert path.read_bytes() == before


@pytest.mark.integration
def test_initial_null_metadata_and_complete_json() -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        post = {"id": "123_1", "message": "Español: acción", "admin_creator": {"name": "Persona"}, "unknown": [1, {"x": True}]}
        with connection:
            assert save_post(connection, post, False) == "inserted"
        row = connection.execute("SELECT message, created_time, permalink_url, raw_json, author, category, slug FROM posts").fetchone()
        assert row[:3] == ("Español: acción", None, None)
        assert json.loads(row[3]) == post
        assert row[4:] == (None, None, None)


@pytest.mark.integration
def test_existing_row_completely_unchanged_without_force() -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        with connection:
            save_post(connection, {"id": "123_1", "message": "Original"}, False)
            connection.execute("UPDATE posts SET author='Autora', category='Escepticismo', slug='original'")
        before = connection.execute("SELECT * FROM posts").fetchone()
        assert save_post(connection, {"id": "123_1", "message": "Changed"}, False) == "skipped"
        assert connection.execute("SELECT * FROM posts").fetchone() == before


@pytest.mark.integration
def test_forced_refresh_preserves_local_metadata() -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        with connection:
            save_post(connection, {"id": "123_1", "message": "Original"}, False)
            connection.execute("UPDATE posts SET author='Autora', category='Escepticismo', slug='original'")
            assert save_post(connection, {"id": "123_1", "message": "Changed"}, True, overwrite_message=True) == "updated"
        row = connection.execute("SELECT message, author, category, slug, raw_json FROM posts").fetchone()
        assert row[:4] == ("Changed", "Autora", "Escepticismo", "original")
        assert json.loads(row[4]) == {"id": "123_1", "message": "Changed"}


@pytest.mark.integration
def test_forced_refresh_preserves_editorial_message_and_updates_photo() -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        save_post(connection, {"id": "123_1", "message": "Texto editorial"}, False)
        refreshed = {
            "id": "123_1",
            "message": "Texto de Facebook",
            "created_time": "2026-01-16T12:26:30+0000",
            "permalink_url": "https://www.facebook.com/123_1",
            "attachments": {"data": [{"media": {"image": {"src": "https://example.com/fresh.jpg"}}}]},
        }
        assert save_post(connection, refreshed, True) == "updated"
        row = connection.execute("SELECT message, created_time, permalink_url, raw_json FROM posts").fetchone()
        assert row["message"] == "Texto editorial"
        assert row["created_time"].isoformat() == "2026-01-16T12:26:30+00:00"
        assert row["permalink_url"] == refreshed["permalink_url"]
        assert json.loads(row["raw_json"]) == refreshed


@pytest.mark.integration
def test_overwrite_message_without_force_does_not_update() -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        save_post(connection, {"id": "123_1", "message": "Texto editorial"}, False)
        before = tuple(connection.execute("SELECT * FROM posts").fetchone())
        assert save_post(connection, {"id": "123_1", "message": "Facebook"}, False, overwrite_message=True) == "skipped"
        assert tuple(connection.execute("SELECT * FROM posts").fetchone()) == before


@pytest.mark.integration
def test_missing_message_is_null() -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        with connection:
            save_post(connection, {"id": "123_1"}, False)
        assert tuple(connection.execute("SELECT message FROM posts").fetchone()) == (None,)


@pytest.mark.integration
def test_empty_message_preserved() -> None:
    with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
        with connection:
            save_post(connection, {"id": "123_1", "message": ""}, False)
        assert tuple(connection.execute("SELECT message FROM posts").fetchone()) == ("",)


@pytest.mark.integration
def test_legacy_objects_and_existing_backup_preserved() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.db"
        old_backup = path.with_suffix(".bak")
        old_backup.write_text("preserve")
        with closing(sqlite3.connect(path)) as connection:
            with connection:
                connection.executescript("CREATE TABLE legacy (id INTEGER); INSERT INTO legacy VALUES (7); CREATE VIEW legacy_view AS SELECT * FROM legacy;")
            before = connection.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall()
        with open_database(path) as connection:
            assert [tuple(row) for row in connection.execute("SELECT * FROM legacy_view").fetchall()] == [(7,)]
            assert [
                tuple(row)
                for row in connection.execute("SELECT name, sql FROM sqlite_master WHERE name <> 'posts' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
            ] == before
        backups = list(path.parent.glob("*.fb-posts-*.bak"))
        assert len(backups) == 1
        with closing(sqlite3.connect(backups[0])) as backup:
            assert [tuple(row) for row in backup.execute("SELECT * FROM legacy_view").fetchall()] == [(7,)]
        assert old_backup.read_text() == "preserve"


@pytest.mark.integration
def test_incompatible_schema_rejected_without_mutation() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.db"
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY)")
        original = path.read_bytes()
        with pytest.raises(CollectionError), open_database(path):
            pass
        assert path.read_bytes() == original


@pytest.mark.integration
def test_latest_ignores_other_page_and_null() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.db"
        with open_database(path) as connection, connection:
            save_post(connection, {"id": "123_1", "created_time": "2026-01-06T01:48:35+0000"}, False)
            save_post(connection, {"id": "123_2"}, False)
            save_post(connection, {"id": "999_1", "created_time": "2026-11-01T12:00:00+0000"}, False)
        assert stored_latest(path, "123") == date(2026, 1, 5)


@pytest.mark.integration
def test_latest_missing_table_does_not_create_it() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.db"
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("CREATE TABLE legacy(id INTEGER)")
        before = path.read_bytes()
        with pytest.raises(CollectionError):
            stored_latest(path, "123")
        assert path.read_bytes() == before


@pytest.mark.integration
def test_latest_missing_file_not_created() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "missing.db"
        with pytest.raises(CollectionError):
            stored_latest(path, "123")
        assert path.exists() == False


@pytest.mark.integration
def test_default_path_is_repository_sibling() -> None:
    assert DEFAULT_DATABASE == Path(__file__).resolve().parents[2] / "sindioses.db"
    assert DEFAULT_DATABASE.name == "sindioses.db"
