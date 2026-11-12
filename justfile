set windows-shell := ["pwsh", "-nologo", "-c"]

# List available recipes
[private]
default:
    @just --list --justfile "{{justfile()}}"

# Generar sitio
gen *params:
    uv run nikola build {{params}}

# Ejecutar la suite de pruebas
test:
    uv run pytest

# Publicar contenido
deploy *comments:
    uv run nikola github_deploy -m "{{comments}}"

# Obtener posts de Facebook
[group("FB")]
download-posts inicio *params:
    uv run fb_posts.py collect {{inicio}} {{params}}

alias dl := download-posts

# Escribir posts Nikola clasificados y con autor
[group("FB")]
posts *params:
    uv run fb_posts.py gen {{params}}

# Escribir posts y regenerar sitio
[group("FB")]
gen-post *params:
    just posts {{params}}
    just gen

# Verificar credenciales
cred:
    uv run fb_posts.py credential check
