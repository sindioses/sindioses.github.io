"""SQLite persistence restricted to the collector's posts table."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from .models import CollectionError, Post, latest_date, optional_text, post_info

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT.parent / "sindioses.db"
COLUMNS = ("id", "message", "created_time", "permalink_url", "raw_json", "author", "category", "slug")
SCHEMA = """CREATE TABLE posts (
    id TEXT PRIMARY KEY NOT NULL, message TEXT, created_time TIMESTAMP, permalink_url TEXT,
    raw_json TEXT NOT NULL CHECK(json_valid(raw_json)),
    author TEXT DEFAULT NULL, category TEXT DEFAULT NULL, slug TEXT DEFAULT NULL
)"""


def adapt_datetime_iso(dt):
    return dt.isoformat()


def convert_datetime_iso(val):
    # val is passed as a bytes object from the database
    return datetime.fromisoformat(val.decode())


sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter("timestamp", convert_datetime_iso)


def database_path(override: Path | None) -> Path:
    path = override.resolve() if override else DEFAULT_DATABASE
    if not path.is_file():
        raise CollectionError(f"No existe la base compartida {path}")
    return path


def check_schema(connection: sqlite3.Connection) -> bool:
    record = connection.execute("SELECT type, sql FROM sqlite_master WHERE name = 'posts' COLLATE NOCASE").fetchone()
    if record is None:
        return False
    columns = connection.execute("PRAGMA table_info(posts)").fetchall()
    valid = record[0] == "table" and tuple(row[1] for row in columns) == COLUMNS
    valid = valid and tuple(row[2].upper() for row in columns) == ("TEXT", "TEXT", "TIMESTAMP", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT")
    valid = valid and columns[0][3] == 1 and columns[0][5] == 1 and columns[4][3] == 1
    valid = valid and all(row[5] == 0 for row in columns[1:])
    valid = valid and all(columns[index][3] == 0 for index in (1, 2, 3, 5, 6, 7))
    valid = valid and "check(json_valid(raw_json))" in "".join(record[1].lower().split())
    valid = valid and connection.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' AND tbl_name='posts' COLLATE NOCASE").fetchone() is None
    if not valid:
        raise CollectionError("La tabla posts existente tiene un esquema incompatible; no se modificó.")
    return True


@contextmanager
def open_database(path: Path) -> Iterator[sqlite3.Connection]:
    existed = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)) as connection:
        if not check_schema(connection):
            if existed:
                backup_path = path.with_name(f"{path.name}.fb-posts-{uuid4().hex}.bak")
                with backup_path.open("xb"):
                    pass
                with closing(sqlite3.connect(backup_path)) as backup:
                    connection.backup(backup)
            with connection:
                connection.execute(SCHEMA)
        connection.row_factory = sqlite3.Row
        yield connection


def stored_latest(path: Path, page_id: str) -> date:
    # Read-only lookup must precede schema initialization for an invalid latest request.
    if not path.is_file():
        return latest_date([])
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        if not check_schema(connection):
            return latest_date([])
        rows = connection.execute(
            "SELECT created_time FROM posts WHERE substr(id, 1, ?) = ? AND created_time IS NOT NULL",
            (len(page_id) + 1, page_id + "_"),
        )
        return latest_date(row[0] for row in rows)


def exists(connection: sqlite3.Connection, identifier: str) -> bool:
    return connection.execute("SELECT 1 FROM posts WHERE id = ?", (identifier,)).fetchone() is not None


def save_post(
    connection: sqlite3.Connection, post: Post, force: bool, *, overwrite_message: bool = False
) -> Literal["inserted", "skipped", "updated"]:
    identifier = post_info(post).id
    present = exists(connection, identifier)
    if present and not force:
        return "skipped"
    values = (identifier, *(optional_text(post, name) for name in COLUMNS[1:4]), json.dumps(post, ensure_ascii=False, allow_nan=False))
    statement = (
        "INSERT INTO posts (id, message, created_time, permalink_url, raw_json, author, category, slug) "
        "VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL)"
    )
    statement += (
        " ON CONFLICT(id) DO UPDATE SET "
        + ("message=excluded.message, " if overwrite_message else "")
        + "created_time=excluded.created_time, "
        "permalink_url=excluded.permalink_url, raw_json=excluded.raw_json"
        if force
        else " ON CONFLICT(id) DO NOTHING"
    )
    cursor = connection.execute(statement, values)
    return "skipped" if cursor.rowcount == 0 else "updated" if present else "inserted"


def get_section_mappings(db: sqlite3.Connection) -> dict:
    query = (
        "SELECT idseccion, prefijo, nombreseccion FROM secciones WHERE prefijo is not null and trim(prefijo) <> ''"
    )
    cur = db.execute(query)
    return {row[0]: {"dir": row["prefijo"], "name": row["nombreseccion"]} for row in cur}
