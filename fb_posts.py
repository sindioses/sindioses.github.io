"""Recopilar publicaciones de Facebook en la base local de Sin Dioses."""

import json
import sqlite3
import sys
from datetime import date, datetime
from itertools import takewhile
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

import httpx
from cyclopts import App, Parameter
from loguru import logger
from rich import get_console, print

from fb_posts_lib.collection import collect_posts
from fb_posts_lib.const import IMAGE_ROOT, LogLevelName, POST_ROOT, POST_TEMPLATE, SQL_POST_QUERY
from fb_posts_lib.credentials import native_store, prompt_token, read_token, register_page_token
from fb_posts_lib.models import SITE_ZONE, CollectionError, Counts, Post, resolve_period
from fb_posts_lib.post_format import post_format
from fb_posts_lib.posts import FacebookPosts
from fb_posts_lib.storage import database_path, get_section_mappings, open_database, stored_latest
from fb_posts_lib.token_status import inspect_token
from fb_posts_lib.transport import GraphTransport


app = App(
    help="Recopilar publicaciones de Facebook sin descargar imágenes ni archivos.",
    default_parameter=Parameter(negative=()),
)
credential = App(name="credential", help="Gestionar el token en el keyring del sistema.")
app.command(credential)


def facebook(page_id: str, api_version: str) -> FacebookPosts:
    token = read_token(native_store(), page_id)
    reader = GraphTransport(token, api_version)
    inspect_token(reader, token, page_id, datetime.now(SITE_ZONE))
    return FacebookPosts(reader, page_id, api_version)


@credential.command(name="set")
def credential_set(*, page_id: str = "115097879246", api_version: str = "v26.0") -> None:
    """Registrar o reemplazar el token mediante entrada oculta.

    Parameters
    ----------
    page_id
        ID numérico de la página autorizada.
    api_version
        Versión explícita de Graph API para validar la credencial.
    """
    if not page_id.isdecimal():
        raise CollectionError("El ID de página debe ser numérico.")
    store = native_store()
    token = prompt_token()
    status = register_page_token(store, GraphTransport(token, api_version), page_id, token, datetime.now(SITE_ZONE))
    print("Token guardado en el keyring del sistema.")
    print(status.summary())


@credential.command(name="check")
def credential_check(*, page_id: str = "115097879246", api_version: str = "v26.0") -> None:
    """Verificar página, aplicación y caducidades sin cambiar la credencial.

    Parameters
    ----------
    page_id
        ID de la página autorizada.
    api_version
        Versión explícita de Graph API.
    """
    token = read_token(native_store(), page_id)
    status = inspect_token(GraphTransport(token, api_version), token, page_id, datetime.now(SITE_ZONE))
    print(status.summary())


@app.command
def sample(*, post_id: str, page_id: str = "115097879246", api_version: str = "v26.0") -> None:
    """Consultar una publicación completa sin escribir en SQLite.

    Parameters
    ----------
    post_id
        ID numérico o compuesto de la publicación.
    page_id
        ID de la página autorizada.
    api_version
        Versión explícita de Graph API.
    """
    post = facebook(page_id, api_version).full_post(post_id)
    display_post(post)


def display_post(post: Post) -> None:
    """Print JSON literally, preserving markup-like text and long message lines."""
    get_console().print(json.dumps(post, ensure_ascii=False, indent=2, allow_nan=False), soft_wrap=True, markup=False, highlight=False)


@app.command
def collect(
    initial_date: date | Literal["latest"],
    final_date: date | None = None,
    /,
    *,
    force: bool = False,
    page_id: str = "115097879246",
    api_version: str = "v26.0",
    database: Path | None = None,
    log_level: Annotated[LogLevelName, Parameter(alias="-L")] = LogLevelName.INFO,
) -> None:
    """Recopilar todas las publicaciones accesibles de un período.

    Parameters
    ----------
    initial_date
        Fecha inicial YYYY-MM-DD o latest (día del último post guardado).
    final_date
        Último día incluido YYYY-MM-DD. Omitir para usar el instante actual.
    force
        Actualizar campos de Facebook de IDs existentes; preservar metadatos locales.
    page_id
        ID de la página autorizada.
    api_version
        Versión explícita de Graph API.
    database
        Ruta SQLite alternativa; por defecto ../sindioses.db respecto del repositorio.
    log_level
        Nivel de logging
    """

    log_level.reset_logger()
    now = datetime.now(SITE_ZONE)
    if not page_id.isdecimal():
        raise CollectionError("El ID de página debe ser numérico.")
    path = database_path(database)
    initial = stored_latest(path, page_id) if initial_date == "latest" else initial_date
    period = resolve_period(initial, final_date, now)
    source = facebook(page_id, api_version)
    print(f"Desde {period.start.isoformat()} hasta {period.end.isoformat()} (límite final exclusivo).")
    counts = Counts()
    try:
        with open_database(path) as connection:
            collect_posts(source, connection, period, force, counts)
    except (CollectionError, sqlite3.Error, OSError):
        logger.error("Recopilación incompleta. {} Repita el intervalo explícito.", counts.summary())
        raise
    print(counts.summary())


@app.command
def gen(
    *,
    article_force: Annotated[bool, Parameter(alias="-F")] = False,
    image_force: Annotated[bool, Parameter(alias="-f")] = False,
    cut_date: Annotated[datetime | None, Parameter(alias="-C")] = None,
    partial_slug: Annotated[str | None, Parameter(alias="-S")] = None,
    log_level: Annotated[LogLevelName, Parameter(alias="-L")] = LogLevelName.INFO,
):
    """Generar artículos a partir de los posts que están clasificados.

    Parameters
    ----------
    article_force
        Sobreescribir un archivo existente
    image_force
        Sobreescribir una imagen existente
    cut_date
        Fecha a partir de la cual se deben generar artículos
    partial_slug
        Slug total y parcial que debe coincidir
    log_level
        Nivel de logging

    """

    log_level.reset_logger()
    try:
        with open_database(database_path(None)) as db:
            cats = get_section_mappings(db)
            logger.debug("cats: {}", cats)
            cur = db.execute(SQL_POST_QUERY, {"cut_date": cut_date, "slug": partial_slug})
            for post in cur:
                categ = post["category"]
                outfile = (POST_ROOT / cats[categ]["dir"] / post["slug"]).with_suffix(".rst")
                if outfile.exists() and not article_force:
                    stat = outfile.stat()
                    logger.debug("{} ya existe ({} bytes), omitiendo", outfile, stat.st_size)
                    continue
                image_name = None
                if post["image"]:
                    logger.debug("Imagen hallada: {}", post["image"])
                    image_ext = Path(urlsplit(post["image"]).path).suffix
                    image_fn = (IMAGE_ROOT / cats[categ]["dir"] / post["slug"]).with_suffix(image_ext)
                    image_name = image_fn.name
                    if not image_fn.exists() or image_force:
                        r = httpx.get(post["image"])
                        r.raise_for_status()
                        image_fn.parent.mkdir(parents=True, exist_ok=True)
                        image_fn.write_bytes(r.content)
                        logger.debug("Grabada imagen {}", image_fn)

                post_info = post_format(post["message"], image_name)
                outfile.write_text(
                    POST_TEMPLATE.format(
                        author=post["author"],
                        title=post_info.title,
                        date=post["created_time"],
                        type=post["category"].lower(),
                        category=cats[categ]["name"],
                        description=post_info.description,
                        body=post_info.body,
                        link=post["permalink_url"],
                    ),
                    encoding="utf-8",
                )
                logger.info("Grabado {}", outfile)

    except (sqlite3.Error, OSError) as err:
        logger.error("{}", err)
        raise


@logger.catch(onerror=lambda _: sys.exit(1))
def main() -> None:
    try:
        app()
    except CollectionError as error:
        logger.error("{}", error)
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        logger.warning("Operación interrumpida; repita el intervalo explícito para completar la recopilación.")
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
