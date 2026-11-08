import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

from fb_posts_lib.models import CollectionError
from fb_posts_lib.storage import DEFAULT_DATABASE, SCHEMA, check_schema, database_path, open_database, save_post, stored_latest


class StorageTests(unittest.TestCase):
    def test_schema_accepts_timestamp_column(self):
        with closing(sqlite3.connect(":memory:")) as connection:
            connection.execute(SCHEMA)
            self.assertTrue(check_schema(connection))

    def test_schema_rejects_other_column_types(self):
        for schema in (SCHEMA.replace("created_time TIMESTAMP", "created_time TEXT"), SCHEMA.replace("message TEXT", "message INTEGER")):
            with self.subTest(schema=schema), closing(sqlite3.connect(":memory:")) as connection:
                connection.execute(schema)
                with self.assertRaises(CollectionError):
                    check_schema(connection)

    def test_force_inserts_new_ids_with_null_metadata(self):
        with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
            with connection:
                self.assertEqual(save_post(connection, {"id": "123_1"}, True), "inserted")
            self.assertEqual(connection.execute("SELECT author, category, slug FROM posts").fetchone(), (None, None, None))

    def test_table_triggers_are_incompatible(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            with open_database(path) as connection:
                connection.execute("CREATE TRIGGER posts_trigger AFTER INSERT ON posts BEGIN SELECT 1; END")
            before = path.read_bytes()
            with self.assertRaises(CollectionError), open_database(path):
                pass
            self.assertEqual(path.read_bytes(), before)

    def test_initial_null_metadata_and_complete_json(self):
        with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
            post = {"id": "123_1", "message": "Español: acción", "admin_creator": {"name": "Persona"}, "unknown": [1, {"x": True}]}
            with connection:
                self.assertEqual(save_post(connection, post, False), "inserted")
            row = connection.execute("SELECT message, created_time, permalink_url, raw_json, author, category, slug FROM posts").fetchone()
            self.assertEqual(row[:3], ("Español: acción", None, None))
            self.assertEqual(json.loads(row[3]), post)
            self.assertEqual(row[4:], (None, None, None))

    def test_existing_row_completely_unchanged_without_force(self):
        with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
            with connection:
                save_post(connection, {"id": "123_1", "message": "Original"}, False)
                connection.execute("UPDATE posts SET author='Autora', category='Escepticismo', slug='original'")
            before = connection.execute("SELECT * FROM posts").fetchone()
            self.assertEqual(save_post(connection, {"id": "123_1", "message": "Changed"}, False), "skipped")
            self.assertEqual(connection.execute("SELECT * FROM posts").fetchone(), before)

    def test_forced_refresh_preserves_local_metadata(self):
        with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
            with connection:
                save_post(connection, {"id": "123_1", "message": "Original"}, False)
                connection.execute("UPDATE posts SET author='Autora', category='Escepticismo', slug='original'")
                self.assertEqual(save_post(connection, {"id": "123_1", "message": "Changed"}, True), "updated")
            row = connection.execute("SELECT message, author, category, slug, raw_json FROM posts").fetchone()
            self.assertEqual(row[:4], ("Changed", "Autora", "Escepticismo", "original"))
            self.assertEqual(json.loads(row[4]), {"id": "123_1", "message": "Changed"})

    def test_missing_message_is_null(self):
        with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
            with connection:
                save_post(connection, {"id": "123_1"}, False)
            self.assertEqual(connection.execute("SELECT message FROM posts").fetchone(), (None,))

    def test_empty_message_preserved(self):
        with tempfile.TemporaryDirectory() as directory, open_database(Path(directory) / "test.db") as connection:
            with connection:
                save_post(connection, {"id": "123_1", "message": ""}, False)
            self.assertEqual(connection.execute("SELECT message FROM posts").fetchone(), ("",))

    def test_legacy_objects_and_existing_backup_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            old_backup = path.with_suffix(".bak")
            old_backup.write_text("preserve")
            with closing(sqlite3.connect(path)) as connection:
                with connection:
                    connection.executescript(
                        "CREATE TABLE legacy (id INTEGER); INSERT INTO legacy VALUES (7); CREATE VIEW legacy_view AS SELECT * FROM legacy;"
                    )
                before = connection.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall()
            with open_database(path) as connection:
                self.assertEqual(connection.execute("SELECT * FROM legacy_view").fetchall(), [(7,)])
                self.assertEqual(
                    connection.execute("SELECT name, sql FROM sqlite_master WHERE name <> 'posts' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall(),
                    before,
                )
            backups = list(path.parent.glob("*.fb-posts-*.bak"))
            self.assertEqual(len(backups), 1)
            with closing(sqlite3.connect(backups[0])) as backup:
                self.assertEqual(backup.execute("SELECT * FROM legacy_view").fetchall(), [(7,)])
            self.assertEqual(old_backup.read_text(), "preserve")

    def test_incompatible_schema_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            with closing(sqlite3.connect(path)) as connection:
                connection.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY)")
            original = path.read_bytes()
            with self.assertRaises(CollectionError), open_database(path):
                pass
            self.assertEqual(path.read_bytes(), original)

    def test_json_constraint_rejects_invalid_json(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            open_database(Path(directory) / "test.db") as connection,
            self.assertRaises(sqlite3.IntegrityError),
        ):
            connection.execute("INSERT INTO posts(id, raw_json) VALUES('123_1', 'invalid')")

    def test_latest_ignores_other_page_and_null(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            with open_database(path) as connection, connection:
                save_post(connection, {"id": "123_1", "created_time": "2026-01-06T01:48:35+0000"}, False)
                save_post(connection, {"id": "123_2"}, False)
                save_post(connection, {"id": "999_1", "created_time": "2026-11-01T12:00:00+0000"}, False)
            self.assertEqual(stored_latest(path, "123"), date(2026, 1, 5))

    def test_latest_missing_table_does_not_create_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            with closing(sqlite3.connect(path)) as connection:
                connection.execute("CREATE TABLE legacy(id INTEGER)")
            before = path.read_bytes()
            with self.assertRaises(CollectionError):
                stored_latest(path, "123")
            self.assertEqual(path.read_bytes(), before)

    def test_latest_missing_file_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.db"
            with self.assertRaises(CollectionError):
                stored_latest(path, "123")
            self.assertEqual(path.exists(), False)

    def test_default_path_is_repository_sibling(self):
        self.assertEqual(database_path(None), DEFAULT_DATABASE)
        self.assertEqual(DEFAULT_DATABASE.name, "sindioses.db")
