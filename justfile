set windows-shell := ["pwsh", "-nologo", "-c"]

# List available recipes
[private]
default:
    @just --list --justfile "{{justfile()}}"

# Generar sitio
gen *params:
    uv run nikola build

# Publicar contenido
deploy:
    uv run nikola github_deploy
