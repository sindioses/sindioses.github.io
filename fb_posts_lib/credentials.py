"""Native OS keyring access; never use file or plaintext backends."""

import warnings
from datetime import datetime
from getpass import GetPassWarning, getpass

import keyring
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError

from .models import CollectionError, GraphReader, SecretStore
from .token_status import TokenStatus, inspect_token

SERVICE = "sindioses.fb-collect"
NATIVE_MODULES = {"keyring.backends.Windows", "keyring.backends.macOS", "keyring.backends.SecretService", "keyring.backends.kwallet"}


def native_store() -> SecretStore:
    try:
        return require_native(keyring.get_keyring())
    except (KeyringError, RuntimeError):
        raise CollectionError("El keyring del sistema no está disponible.") from None


def require_native(backend: KeyringBackend) -> SecretStore:
    if type(backend).__module__ not in NATIVE_MODULES or backend.priority <= 0:
        raise CollectionError("Configure un keyring nativo seguro; no se admiten almacenes de archivos ni backends compuestos.")
    return backend


def read_token(store: SecretStore, page_id: str) -> str:
    try:
        token = store.get_password(SERVICE, page_id)
    except KeyringError:
        raise CollectionError("No se pudo leer la credencial del keyring.") from None
    if not token:
        raise CollectionError("Falta el token. Ejecute: uv run fb_posts.py credential set")
    return token


def save_token(store: SecretStore, page_id: str, token: str) -> None:
    if not token.strip() or any(character.isspace() for character in token):
        raise CollectionError("El token no puede estar vacío ni contener espacios.")
    try:
        store.set_password(SERVICE, page_id, token)
    except KeyringError:
        raise CollectionError("No se pudo guardar la credencial en el keyring.") from None


def register_page_token(store: SecretStore, reader: GraphReader, page_id: str, token: str, now: datetime) -> TokenStatus:
    status = inspect_token(reader, token, page_id, now)
    save_token(store, page_id, token)
    return status


def prompt_token() -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            return getpass("Token de la página (entrada oculta): ")
    except (GetPassWarning, EOFError):
        raise CollectionError("Se necesita una terminal con entrada oculta para registrar el token.") from None
