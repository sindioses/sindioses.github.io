"""Post discovery, readable field retrieval, and best-effort publisher attribution."""

import re
from collections.abc import Iterator
from typing import cast

from loguru import logger

from .fields import CORE_FIELDS, EXCLUDED_EDGES, POST_FIELDS_V26
from .models import CollectionError, GraphError, GraphReader, Period, Post, post_info
from .transport import sanitize_pagination


class FacebookPosts:
    def __init__(self, reader: GraphReader, page_id: str, version: str):
        if not page_id.isdecimal():
            raise CollectionError("El ID de página debe ser numérico.")
        self.reader = reader
        self.page_id = page_id
        self.version = version

    def verify_identity(self) -> None:
        identity = self.reader.get("me", {"fields": "id,name"})
        if identity.get("id") != self.page_id:
            raise CollectionError("El token no corresponde a la página configurada.")

    def pages(self, period: Period) -> Iterator[list[Post]]:
        parameters = {"fields": "id,created_time", "since": str(int(period.start.timestamp())), "until": str(int(period.end.timestamp())), "limit": "100"}
        seen: set[str] = set()
        while True:
            payload = self.reader.get(f"{self.page_id}/posts", parameters)
            data = payload.get("data")
            if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
                raise CollectionError("Facebook devolvió una lista de publicaciones inválida.")
            page = cast(list[Post], data)
            for post in page:
                post_info(post)
            yield page
            paging = payload.get("paging", {})
            if not isinstance(paging, dict):
                raise CollectionError("Facebook devolvió paginación inválida.")
            if not paging.get("next"):
                return
            cursors = paging.get("cursors")
            after = cursors.get("after") if isinstance(cursors, dict) else None
            if not isinstance(after, str) or not after or after in seen:
                raise CollectionError("Facebook devolvió un cursor inválido o repetido.")
            seen.add(after)
            parameters = {**parameters, "after": after}

    def readable_fields(self, identifier: str) -> tuple[str, ...]:
        try:
            payload = self.reader.get(identifier, {"fields": "id", "metadata": "1"})
        except GraphError as error:
            if not error.field_rejection:
                raise
            payload = {}
        metadata = payload.get("metadata")
        fields = metadata.get("fields") if isinstance(metadata, dict) else None
        if isinstance(fields, list) and fields:
            names: list[str] = []
            for field in fields:
                if not isinstance(field, dict) or not isinstance(field.get("name"), str):
                    raise CollectionError("Facebook devolvió metadatos de campos inválidos.")
                name = field["name"]
                if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
                    raise CollectionError("Facebook devolvió un nombre de campo inválido.")
                if name not in EXCLUDED_EDGES:
                    names.append(name)
            return tuple(dict.fromkeys((*CORE_FIELDS, "admin_creator", "from", "attachments", *names)))
        if self.version != "v26.0":
            raise CollectionError("Sin descubrimiento de campos, solo se admite el inventario de v26.0.")
        logger.debug("Publicación {}: sin metadatos de campos; se usa el inventario v26.0; no se garantiza cobertura exhaustiva.", identifier)
        return POST_FIELDS_V26

    def fetch_fields(self, identifier: str, fields: tuple[str, ...]) -> Post:
        try:
            payload = self.reader.get(identifier, {"fields": ",".join(fields)})
        except GraphError as error:
            if error.code in (10, 100, 200) and not error.field_rejection:
                # Some optional fields return generic object/permission errors. Verify
                # normal post access before isolating them; token/access failures stay fatal.
                probe = self.reader.get(identifier, {"fields": ",".join(CORE_FIELDS)})
                if post_info(probe).id != identifier:
                    raise CollectionError("La publicación solicitada ya no está disponible.") from None
            elif not error.field_rejection:
                raise
            if len(fields) > 1:
                middle = len(fields) // 2
                return {**self.fetch_fields(identifier, fields[:middle]), **self.fetch_fields(identifier, fields[middle:])}
            if fields[0] in CORE_FIELDS:
                raise
            logger.debug("Publicación {}: campo no disponible: {}.", identifier, fields[0])
            return {}
        if post_info(payload).id != identifier:
            raise CollectionError("La respuesta no corresponde a la publicación solicitada.")
        return payload

    def full_post(self, identifier: str) -> Post:
        post_info({"id": identifier})
        fields = self.readable_fields(identifier)
        result: Post = {}
        for offset in range(0, len(fields), 8):
            result.update(self.fetch_fields(identifier, fields[offset : offset + 8]))
        if "admin_creator" not in result:
            result.update(self.fetch_fields(identifier, ("admin_creator",)))
        post_info(result)
        return cast(Post, sanitize_pagination(result))
