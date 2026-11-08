"""HTTPS transport with safe Graph API diagnostics."""

import json
import re
from contextlib import AbstractContextManager
from http.client import HTTPException
from typing import BinaryIO, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .models import CollectionError, GraphError, Json, Post


class HttpOpener(Protocol):
    def open(self, request: Request, *, timeout: int) -> AbstractContextManager[BinaryIO]: ...


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CollectionError("Facebook devolvió una redirección; no se reenvió la autorización.")


def invalid_constant(value: str) -> None:
    raise CollectionError("Facebook devolvió JSON con un número inválido.")


def decode_response(body: bytes) -> Post:
    try:
        payload = json.loads(body, parse_constant=invalid_constant)
    except (ValueError, UnicodeError):
        raise CollectionError("Facebook devolvió JSON inválido.") from None
    if not isinstance(payload, dict):
        raise CollectionError("Facebook devolvió una estructura inválida.")
    error = payload.get("error")
    if error is not None:
        if not isinstance(error, dict) or not isinstance(error.get("code"), int):
            raise CollectionError("Facebook devolvió un error sin código válido.")
        message = error.get("message", "")
        code = error["code"]
        # Only explicit field errors may be skipped; token/rate/transport failures are fatal.
        field_rejection = isinstance(message, str) and (
            code == 100
            and bool(re.search(r"nonexisting field|non-existing field|field .+ does not exist", message, re.IGNORECASE))
            or code == 12
            and bool(re.search(r"deprecated", message, re.IGNORECASE))
            or code in (10, 200)
            and bool(re.search(r"(?:field|admin_creator).*(?:permission|access)|permission.*field", message, re.IGNORECASE))
        )
        subcode = error.get("error_subcode")
        raise GraphError(code, field_rejection=field_rejection, subcode=subcode if isinstance(subcode, int) else None)
    return payload


class GraphTransport:
    def __init__(self, token: str, version: str, opener: HttpOpener | None = None):
        if not re.fullmatch(r"v\d+\.\d+", version):
            raise CollectionError("La versión de API debe tener la forma v26.0.")
        if not token or any(character.isspace() for character in token):
            raise CollectionError("El token guardado no es válido; vuelva a registrarlo.")
        self._token = token
        self.version = version
        self._opener = opener if opener is not None else build_opener(RejectRedirects())

    def get(self, path: str, parameters: dict[str, str]) -> Post:
        if not re.fullmatch(r"debug_token|(?:me|\d+(?:_\d+)?)(?:/posts)?", path):
            raise CollectionError("Ruta Graph API no permitida.")
        url = f"https://graph.facebook.com/{self.version}/{path}?{urlencode(parameters)}"
        request = Request(url, headers={"Authorization": f"Bearer {self._token}"})
        try:
            with self._opener.open(request, timeout=30) as response:
                return decode_response(response.read())
        except HTTPError as error:
            with error:
                decode_response(error.read())
            raise CollectionError(f"Facebook devolvió HTTP {error.code}.") from None
        except (URLError, TimeoutError, OSError, HTTPException):
            raise CollectionError("No se pudo completar la conexión con Facebook.") from None


def sanitize_pagination(value: Json) -> Json:
    """Remove transport credentials only; media URIs remain byte-for-byte unchanged."""
    from urllib.parse import parse_qsl, urlsplit, urlunsplit

    if isinstance(value, list):
        return [sanitize_pagination(item) for item in value]
    if not isinstance(value, dict):
        return value
    result: Post = {}
    for key, item in value.items():
        if key == "paging" and isinstance(item, dict):
            paging = dict(item)
            for direction in ("next", "previous"):
                url = paging.get(direction)
                if isinstance(url, str):
                    parts = urlsplit(url)
                    query = [
                        (name, text) for name, text in parse_qsl(parts.query, keep_blank_values=True) if name.lower() not in {"access_token", "appsecret_proof"}
                    ]
                    paging[direction] = urlunsplit(parts._replace(query=urlencode(query)))
            result[key] = sanitize_pagination(paging)
        else:
            result[key] = sanitize_pagination(item)
    return result
