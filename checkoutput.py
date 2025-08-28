#!/usr/bin/env uv run -s
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "beautifulsoup4",
#     "lxml",
#     "rich",
# ]
#
# ///

from pathlib import Path
import logging
from rich import print  # noqa: F401
from rich.progress import track
from rich.logging import RichHandler
from bs4 import BeautifulSoup
from urllib.parse import unquote
from rich.table import Table


FORMAT = "%(message)s"
logging.basicConfig(level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])

logger = logging.getLogger("rich")


imglocales = set()


def local_image(tag):
    src = tag.get("src")
    result = tag.name == "img" and src and src not in imglocales and not src.startswith("http")
    imglocales.add(src)
    return result


def main():
    raiz_output = Path() / "output"
    paginas = raiz_output.glob("**/*.html")
    filas = []
    for pagina in track(list(paginas)):
        sopa = BeautifulSoup(pagina.read_text(encoding="utf-8"), "lxml")
        imgs = sopa.find_all(local_image)
        if imgs:
            for img in imgs:
                cleansrc = unquote(img["src"]).partition("?")[0]
                pathimage = (pagina.parent / cleansrc).resolve()
                if not pathimage.is_file():
                    logger.warning(
                        "%r: imagen %r no hallada (src=%r)",
                        str(pagina),
                        str(pathimage),
                        cleansrc,
                    )
                    filas.append((str(pagina.relative_to(raiz_output)), cleansrc))

    tbl = Table("Página", "Imagen faltante")
    for fila in sorted(filas):
        tbl.add_row(*fila)
    print(tbl)


if __name__ == "__main__":
    main()
