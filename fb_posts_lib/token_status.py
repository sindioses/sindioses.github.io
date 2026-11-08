"""Validate Page-token metadata without exposing tokens or API error bodies."""

from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from .models import SITE_ZONE, CollectionError, GraphReader, Post

APP_ID = "1603408681013331"


@dataclass(frozen=True)
class TokenStatus:
    data_access_expires_at: int

    def summary(self) -> str:
        expiration = datetime.fromtimestamp(self.data_access_expires_at, SITE_ZONE).isoformat() if self.data_access_expires_at else "sin fecha declarada"
        return f"Token de página válido; caducidad del token: nunca. Acceso a datos: {expiration}."


def validate_metadata(data: Post, page_id: str, now: datetime) -> TokenStatus:
    if data.get("is_valid") is not True:
        raise CollectionError("Facebook indica que el token no es válido; vuelva a autorizar la aplicación.")
    if data.get("type") != "PAGE" or data.get("profile_id") != page_id:
        raise CollectionError("Se necesita el token de la página elegida, obtenido en /me/accounts, no un token de usuario.")
    if data.get("app_id") != APP_ID:
        raise CollectionError("El token no pertenece a Sin Dioses App.")
    expires_at = data.get("expires_at")
    if type(expires_at) is not int or expires_at < 0:
        raise CollectionError("Facebook no devolvió una caducidad de token verificable.")
    if expires_at != 0:
        raise CollectionError("El token tiene caducidad programada. Obtenga un token de página derivado de un token de usuario de larga duración.")
    data_expiration = data.get("data_access_expires_at")
    if type(data_expiration) is not int or data_expiration < 0:
        raise CollectionError("Facebook no devolvió una caducidad de acceso a datos verificable.")
    if data_expiration and data_expiration <= now.timestamp():
        raise CollectionError("El acceso a datos caducó aunque el token no caduque. Vuelva a autorizar Sin Dioses App.")
    return TokenStatus(data_expiration)


def inspect_token(reader: GraphReader, token: str, page_id: str, now: datetime) -> TokenStatus:
    if not page_id.isdecimal():
        raise CollectionError("El ID de página debe ser numérico.")
    identity = reader.get("me", {"fields": "id,name"})
    if identity.get("id") != page_id:
        raise CollectionError("El token no corresponde a la página elegida. Copie su access_token de /me/accounts, no el token de usuario.")
    payload = reader.get("debug_token", {"input_token": token})
    data = payload.get("data")
    if not isinstance(data, dict):
        raise CollectionError("Facebook devolvió metadatos de token inválidos.")
    status = validate_metadata(data, page_id, now)
    if status.data_access_expires_at and status.data_access_expires_at - now.timestamp() <= 7 * 24 * 3600:
        logger.warning("El acceso a datos vence en menos de siete días; puede ser necesario volver a autorizar la aplicación.")
    return status
