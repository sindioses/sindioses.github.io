"""Shared data contracts and date calculations."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

type Json = None | bool | int | float | str | list[Json] | dict[str, Json]
type Post = dict[str, Json]
SITE_ZONE = ZoneInfo("America/Argentina/Buenos_Aires")


class CollectionError(Exception):
    """A safe diagnostic that can be displayed without exposing credentials."""


class GraphError(CollectionError):
    def __init__(self, code: int, *, field_rejection: bool = False, subcode: int | None = None):
        message = f"Facebook rechazó la consulta (código {code})."
        if code == 190:
            reason = "El token de Facebook caducó" if subcode == 463 else "Facebook rechazó el token"
            detail = f"código {code}, subcódigo {subcode}" if subcode is not None else f"código {code}"
            message = f"{reason} ({detail}). Obtenga un token de página nuevo y guárdelo con: uv run fb_posts.py credential set"
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.field_rejection = field_rejection


class GraphReader(Protocol):
    def get(self, path: str, parameters: dict[str, str]) -> Post: ...


class SecretStore(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...
    def set_password(self, service: str, username: str, password: str) -> None: ...


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime


def resolve_period(initial: date, final: date | None, now: datetime) -> Period:
    start = datetime.combine(initial, time.min, SITE_ZONE)
    end = datetime.combine(final + timedelta(days=1), time.min, SITE_ZONE) if final else now
    if start >= end:
        raise CollectionError("La fecha inicial debe preceder al límite final.")
    return Period(start, end)


def latest_date(timestamps: Iterable[str]) -> date:
    latest: datetime | None = None
    try:
        for value in timestamps:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                raise ValueError("Missing timezone")
            if latest is None or parsed > latest:
                latest = parsed
    except (TypeError, ValueError):
        raise CollectionError("Hay fechas almacenadas inválidas o sin zona horaria.") from None
    if latest is None:
        raise CollectionError("No hay fechas guardadas; indique una fecha inicial explícita.")
    return latest.astimezone(SITE_ZONE).date()


@dataclass(frozen=True)
class PostInfo:
    id: str
    created_time: datetime | None


def post_info(post: Post) -> PostInfo:
    identifier = post.get("id")
    if not isinstance(identifier, str) or not re.fullmatch(r"[0-9]+(?:_[0-9]+)?", identifier):
        raise CollectionError("Facebook devolvió un ID de publicación inválido.")
    value = optional_text(post, "created_time")
    created_time = None
    if value is not None:
        try:
            created_time = datetime.fromisoformat(value)
            if created_time.tzinfo is None or created_time.utcoffset() is None:
                raise ValueError("Missing timezone")
        except ValueError:
            raise CollectionError("Facebook devolvió una fecha de publicación inválida o sin zona horaria.") from None
        created_time = created_time.astimezone(SITE_ZONE)
    return PostInfo(identifier, created_time)


def optional_text(post: Post, name: str) -> str | None:
    value = post.get(name)
    if value is not None and not isinstance(value, str):
        raise CollectionError(f"Facebook devolvió un campo {name} inválido.")
    return value


@dataclass
class Counts:
    read: int = 0
    inserted: int = 0
    skipped: int = 0
    updated: int = 0

    def add(self, outcome: Literal["inserted", "skipped", "updated"]) -> None:
        setattr(self, outcome, getattr(self, outcome) + 1)

    def summary(self) -> str:
        return f"Leídas: {self.read}; nuevas: {self.inserted}; omitidas: {self.skipped}; actualizadas: {self.updated}."
