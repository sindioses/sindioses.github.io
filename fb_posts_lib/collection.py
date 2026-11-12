"""Coordinate bounded collection with batched commits and error preservation."""

import sqlite3
from collections.abc import Iterator
from typing import Protocol

from loguru import logger
from rich import print

from .models import Counts, Period, Post, post_info
from .storage import exists, save_post

BATCH_COMMIT_ITEMS = 10


class PostSource(Protocol):
    def pages(self, period: Period) -> Iterator[list[Post]]: ...
    def full_post(self, identifier: str) -> Post: ...


def collect_posts(
    source: PostSource, connection: sqlite3.Connection, period: Period, force: bool, counts: Counts, *, overwrite_message: bool = False
) -> None:
    pending = 0
    try:
        for page in source.pages(period):
            for listed in page:
                info = post_info(listed)
                identifier = info.id
                counts.read += 1
                if exists(connection, identifier) and not force:
                    counts.skipped += 1
                    logger.debug("Omitido post {} - {}", info.id, info.created_time)
                    continue
                post = source.full_post(identifier)
                outcome = save_post(connection, post, force, overwrite_message=overwrite_message)
                counts.add(outcome)
                if outcome != "skipped":
                    pending += 1
                    published = info.created_time.isoformat() if info.created_time is not None else "fecha desconocida"
                    print(f"Guardado post {info.id} ({published})")
                    if pending == BATCH_COMMIT_ITEMS:
                        connection.commit()
                        pending = 0
    finally:
        # Preserve completed writes on normal completion, errors and Ctrl-C.
        connection.commit()
