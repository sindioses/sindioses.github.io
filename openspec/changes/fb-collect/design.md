# Design

## Context

Véase `proposal.md` para la motivación. Este repositorio genera un sitio Nikola y ya contiene scripts autónomos con metadatos PEP 723, como `checkoutput.py`. No tiene una aplicación de servidor ni una suite general de pruebas.

Las consultas aportadas por el usuario a Graph API v26.0 confirman que el token corresponde a la página `115097879246` y tiene permisos de lectura. Una respuesta incluye `admin_creator` para Marcelo Huerta y otras lo omiten, incluida una publicación que el usuario confirmó como publicada por Iván. No se conoce una regla fiable para recuperar esa atribución. El usuario aceptó sustituir ese objetivo por coincidencias textuales OR y aprobó las columnas propuestas.

## Goals / Non-Goals

**Goals:** mantener una herramienta local pequeña, separar el acceso externo del filtro y la persistencia para poder probarlos sin credenciales, y preservar íntegros los objetos recibidos.

**Non-Goals:** inferir autoría, automatizar inicio de sesión en el navegador, gestionar contraseñas o implementar un servidor OAuth. El usuario obtiene y renueva el token autorizado mediante las herramientas de Meta.

## Decisions

### Script y dependencias

Agregar `fb_collect.py` para Python >=3.13, ejecutable con `uv run --script fb_collect.py`. Declarar `keyring` en metadatos PEP 723; usar `argparse`, `urllib.request`, `json` y `sqlite3` de la biblioteca estándar. Esto sigue un precedente existente y evita agregar un SDK de Facebook o un ORM. No cambiar las dependencias de Nikola ni `uv.lock` si las dependencias permanecen aisladas al script.

Organizar funciones sencillas para CLI, keyring, transporte, selección y base; no crear una jerarquía de clientes o repositorios. Probar límites externos con sustitutos y una base SQLite temporal.

### Interfaz propuesta

- `credential set`: solicitar el token mediante `getpass`, guardarlo en el keyring con servicio `sindioses.fb-collect` y cuenta igual al ID de página. Permitir reemplazarlo explícitamente.
- `sample --post-id ID`: recuperar e imprimir un único objeto de publicación sin escribir SQLite.
- `collect`: recorrer las publicaciones, filtrar y persistir las coincidencias.
- Opciones comunes no secretas: `--page-id` y `--api-version`, con valores iniciales `115097879246` y `v26.0`, respectivamente. La versión inicial se basa en la consulta real del usuario, no en una afirmación de que sea la más reciente.
- Opciones de recopilación: `--contains TEXTO`, repetible, y `--database RUTA`. Si aparece `--contains`, sus expresiones reemplazan los dos valores predeterminados. Rechazar cadenas vacías o de espacios.
- Mostrar al terminar cantidades de publicaciones leídas y coincidentes; ante fallo indicar que el resultado es parcial. Documentación y ayuda en español.

Estas decisiones de interfaz son propuestas de implementación; las expresiones y columnas ya fueron confirmadas por el usuario.

### Keyring y autorización

Usar el almacén nativo seguro, Windows Credential Manager en el entorno actual. Verificar el backend efectivo y rechazar backends nulos, de fallo o de archivos en texto plano; no implementar fallback. El único secreto necesario para las consultas es el token de página. No solicitar contraseña de Facebook ni secreto de la aplicación.

Antes de leer publicaciones, consultar `/me?fields=id,name` y comparar el ID. Enviar el token mediante cabecera Bearer y usar HTTPS con timeout. Consultar `/{page-id}/posts` con los campos acordados y `from,admin_creator`; incluir esos datos en el JSON cuando Facebook los devuelva.

Para paginar, usar los cursores devueltos por Facebook y reconstruir solicitudes al mismo host, versión y endpoint, sin seguir literalmente las URL `paging.next`, que pueden contener tokens. Detectar cursores repetidos o paginación inválida y terminar con error. No enviar cabeceras de autorización en redirecciones a otros hosts. Los diagnósticos deben seleccionar código/tipo de error y una explicación segura, sin volcar solicitudes, cuerpos completos de error ni excepciones con URL secretas.

### Filtro literal

Comparar cada expresión con el mensaje mediante `casefold()` y OR. No usar regex, eliminar acentos ni buscar en comentarios, enlaces externos o metadatos. La firma conserva los corchetes como caracteres literales. No modificar el texto original almacenado ni añadir atributos de autoría. Un mensaje ausente no coincide.

### SQLite y JSON

Tabla `posts`: `id TEXT PRIMARY KEY NOT NULL`, `message TEXT NOT NULL`, `created_time TEXT NULL`, `permalink_url TEXT NULL`, `raw_json TEXT NOT NULL CHECK(json_valid(raw_json))`. Guardar el ID compuesto completo, las fechas tal como llegan y el objeto original serializado como JSON UTF-8, sin truncamiento. Se garantiza equivalencia de datos, no idéntico espaciado ni orden de claves en la respuesta HTTP.

Usar SQL parametrizado y UPSERT por ID, con transacción por página. Mantener columnas y JSON consistentes. No guardar la envoltura `data/paging` ni secretos de transporte. Una nueva ejecución puede recorrer de nuevo los resultados sin duplicados; no se necesita un sistema de checkpoints. Una publicación que deja de coincidir no elimina su versión almacenada: la base acumula coincidencias entre ejecuciones, y no constituye una réplica exacta de Facebook.

La ubicación predeterminada `cache/fb-collect.sqlite3` ya queda ignorada por Git y fuera de las entradas de Nikola. Crear el directorio padre si falta. «Temporal» significa almacenamiento de trabajo que el usuario puede eliminar cuando termine, no expiración ni borrado automático al salir. Documentar que limpiar `cache/` también elimina esta base y que una ruta alternativa debe quedar fuera de `files/`, `images/` y `output/`.

## Risks / Trade-offs

- Las firmas pueden aparecer en citas o faltar en textos de Iván: documentar que las coincidencias no verifican al publicador; no inventar una regla con `admin_creator` ausente.
- Facebook puede omitir publicaciones o campos: conservar lo recibido y limitar la promesa a resultados accesibles por API; una recopilación paginada no garantiza cobertura de todo lo visible en la interfaz.
- Un token puede caducar o perder permisos: terminar con diagnóstico seguro y permitir su reemplazo mediante `credential set`.
- El keyring depende del sistema y la sesión: comprobarlo antes de recopilar y fallar explícitamente si no ofrece almacenamiento seguro.
- Un fallo intermedio deja datos parciales: confirmar por página, informar el fallo y permitir repetir sin duplicar.
- El campo JSON duplica el mensaje: es una decisión expresa para facilitar consultas SQL y conservar metadatos para usos futuros.

## Migration Plan

No migrar contenido ni bases existentes. Introducir script, pruebas y documentación; validar primero con respuestas sintéticas y luego con una muestra autorizada y una recopilación real. La reversión consiste en retirar los nuevos archivos y, por decisión del usuario, eliminar la credencial y la base de trabajo. No ejecutar despliegue de Nikola.
