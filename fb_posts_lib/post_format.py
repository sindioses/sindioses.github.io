import re
from dataclasses import dataclass

from fb_posts_lib.const import THUMBNAIL_TEMPLATE


@dataclass
class PostInfo:
    title: str
    description: str
    body: str


def post_format(post: str, image_name: str | None) -> PostInfo:
    post = (
        _reemplazar_notas_pie(
            _reemplazar_citas_biblicas(post)
        )
        .replace("\N{LEFT DOUBLE QUOTATION MARK}", '"')
        .replace("\N{RIGHT DOUBLE QUOTATION MARK}", '"')
    )
    post = re.sub(r"^-", "- ", post, flags=re.MULTILINE)

    lines = post.splitlines()
    paragraphs = post.split("\n\n")
    if image_name:
        thumbtext = THUMBNAIL_TEMPLATE.format(image_name)
        if "|img|" in post:
            post = post.replace("|img|", thumbtext)
            paragraphs = post.split("\n\n")
        else:
            paragraphs.insert(2, thumbtext)

    return PostInfo(
        title=lines[0],
        description=paragraphs[1],
        body="\n\n".join(paragraphs[1:]),
    )


def _reemplazar_citas_biblicas(post: str) -> str:
    # Reemplazar posibles citas bíblicas con el enlace a Bible Gateway
    palabra = r"[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]*\.?"  # Juan, Cor., Reyes
    conector = r"(?:de|del|la|las|los|el|y)"  # for "Cantar de los Cantares"
    nombre = rf"{palabra}(?:\s+(?:{conector}\s+)*{palabra})*"
    prefijo = r"(?:[1-3]\s?|I{1,3}\s)?"  # 1, 2, 3, I, II, III
    num = r"\d{1,3}"
    rango = rf"{num}(?:[-–]{num})?"
    ncita = re.compile(  # noqa: E131
        rf"\(\s*"
        rf"({prefijo}{nombre}\s+{num}(?::{rango}(?:\s*,\s*{rango})*)?)"
        rf"\s*\)",
        re.MULTILINE | re.VERBOSE,
    )
    post = ncita.sub(r'({{% biblia "\1" DHH %}})', post)

    # Reemplazar múltiples posibles citas bíblicas en paréntesis marcados a tal efecto (!Cita1, Cita2)
    multicita = re.compile(r"\(!([^()]*)\)")
    post = multicita.sub(r'({{% biblia_multi_coma "\1" DHH %}})', post)

    return post


def _reemplazar_notas_pie(post: str) -> str:
    # Reemplazar notas intercaladas
    npie = re.compile(r"\[(\d+)]", re.MULTILINE)
    post = npie.sub(r"[\1]_", post)

    # Reemplazar notas definiciones de notas al pie
    npie = re.compile(r"^\[(\d+)]_", re.MULTILINE)
    post = npie.sub(r".. [\1]", post)
    return post
