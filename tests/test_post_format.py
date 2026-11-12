import pytest

from fb_posts_lib.post_format import post_format


@pytest.mark.unit
def test_editorial_markup_is_preserved_and_adapted() -> None:
    result = post_format("Título\n\nDescripción “citada”.\n\nTexto (Juan 3:16) y (!Juan 3:16, Génesis 1:1).\n\nNota [1]\n\n[1] Referencia.\n\n-Elemento", None)
    assert result.title == "Título"
    assert result.description == 'Descripción "citada".'
    assert result.body == (
        'Descripción "citada".\n\nTexto ({{% biblia "Juan 3:16" DHH %}}) y ({{% biblia_multi_coma "Juan 3:16, Génesis 1:1" DHH %}}).\n\nNota [1]_\n\n.. [1] Referencia.\n\n- Elemento'
    )


@pytest.mark.parametrize(
    "body,expected",
    [
        ("Descripción\n\n|img|\n\nFinal", "Descripción\n\n..  thumbnail:: foto.jpg\n    :class: align-right\n\n\nFinal"),
        ("Descripción\n\nFinal", "Descripción\n\n..  thumbnail:: foto.jpg\n    :class: align-right\n\n\nFinal"),
    ],
)
@pytest.mark.unit
def test_image_uses_placeholder_or_follows_description(body: str, expected: str) -> None:
    assert post_format("Título\n\n" + body, "foto.jpg").body == expected
