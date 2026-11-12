import sqlite3

"""In-memory substitutes; these never contact Facebook or a real keyring."""

from collections.abc import Iterator
from io import BytesIO
from urllib.request import Request

from keyring.errors import KeyringError

from fb_posts_lib.models import CollectionError, GraphError, Period, Post


class MemoryHttp:
    def __init__(self, body: bytes, error: Exception | None = None):
        self.body = body
        self.error = error
        self.requests: list[Request] = []
        self.timeouts: list[int] = []

    def open(self, request: Request, *, timeout: int) -> BytesIO:
        self.requests.append(request)
        self.timeouts.append(timeout)
        if self.error:
            raise self.error
        return BytesIO(self.body)


class MemorySecrets:
    def __init__(self):
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.values[service, username] = password


class UnavailableSecrets:
    def get_password(self, service: str, username: str) -> str | None:
        raise KeyringError("PRIVATE_DETAILS")

    def set_password(self, service: str, username: str, password: str) -> None:
        raise KeyringError("PRIVATE_DETAILS")


class ScriptedGraph:
    def __init__(self, replies: list[Post | Exception]):
        self.replies = iter(replies)
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, path: str, parameters: dict[str, str]) -> Post:
        self.calls.append((path, dict(parameters)))
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        return reply


class FieldGraph:
    def __init__(self, *, metadata: bool = True, denied: str = "", publisher: bool = True):
        self.metadata = metadata
        self.denied = denied
        self.publisher = publisher
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, path: str, parameters: dict[str, str]) -> Post:
        self.calls.append((path, dict(parameters)))
        if "metadata" in parameters:
            return {"id": path, "metadata": {"fields": [{"name": "story"}, {"name": "message_tags"}]}} if self.metadata else {"id": path}
        names = parameters["fields"].split(",")
        if self.denied in names:
            raise GraphError(100, field_rejection=True)
        result: Post = {"id": path}
        for name in names:
            if name == "message":
                result[name] = "Texto sin firma"
            if name == "story":
                result[name] = "Una historia"
            if name == "admin_creator" and self.publisher:
                result[name] = {"id": "7", "name": "Persona"}
            if name == "attachments":
                result[name] = {
                    "data": [{"media": {"image": {"src": "https://media.invalid/img?x=%2F"}}}],
                    "paging": {"next": "https://graph.facebook.com/a?access_token=SECRET&after=x"},
                }
        return result


class PageSource:
    def __init__(self, posts: list[Post], *, fail_after_page: bool = False):
        self.posts = posts
        self.fail_after_page = fail_after_page
        self.fetched: list[str] = []

    def pages(self, period: Period) -> Iterator[list[Post]]:
        for post in self.posts:
            yield [{key: post[key] for key in ("id", "created_time") if key in post}]
        if self.fail_after_page:
            raise CollectionError("Fallo simulado.")

    def full_post(self, identifier: str) -> Post:
        self.fetched.append(identifier)
        return next(post for post in self.posts if post["id"] == identifier)


class FailingPageSource:
    def pages(self, period: Period) -> Iterator[list[Post]]:
        yield [{"id": "123_1"}]
        yield [{"id": "123_2"}, {"id": "123_3"}]

    def full_post(self, identifier: str) -> Post:
        if identifier == "123_3":
            raise CollectionError("Fallo simulado.")
        return {"id": identifier}


class InterruptedSource(FailingPageSource):
    def full_post(self, identifier: str) -> Post:
        if identifier == "123_3":
            raise KeyboardInterrupt
        return super().full_post(identifier)


class ObservedSource(PageSource):
    def __init__(self, posts: list[Post], observer: sqlite3.Connection, snapshots: list[int]):
        super().__init__(posts)
        self.observer = observer
        self.snapshots = snapshots

    def full_post(self, identifier: str) -> Post:
        self.snapshots.append(self.observer.execute("SELECT count(*) FROM posts").fetchone()[0])
        return super().full_post(identifier)
