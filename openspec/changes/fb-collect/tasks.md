# Tasks

## 1. CLI y credenciales

- [ ] 1.1 Crear `fb_collect.py` con metadatos PEP 723, dependencia `keyring`, subcomandos `credential set`, `sample` y `collect`, y opciones no secretas del diseño; verificar que `uv run --script fb_collect.py --help` muestra la interfaz en español sin requerir credenciales.
- [ ] 1.2 Implementar entrada oculta, registro, reemplazo y recuperación del token por página en un backend nativo seguro; verificar mediante pruebas con backend sustituido el uso correcto de servicio/cuenta, credencial ausente, backend inseguro y errores sin secretos.
- [ ] 1.3 Documentar en `docs/fb-collect.md` cómo obtener un token mediante Sin Dioses App, registrarlo y renovarlo; comprobar que los ejemplos no incluyen secretos en argumentos, archivos ni historial y describen Windows Credential Manager.

## 2. Lectura de Facebook y consulta de muestra

- [ ] 2.1 Implementar GET con versión explícita, cabecera Bearer, timeout y comprobación de identidad de página; verificar con transporte sustituido la página correcta, token de otra identidad, permisos insuficientes, caducidad y errores HTTP/JSON sin exponer secretos.
- [ ] 2.2 Implementar lectura de `/{page-id}/posts` y paginación mediante cursores sobre el mismo endpoint; probar varias páginas, primera página sin coincidencias, fin vacío, cursores repetidos y rechazo de redirecciones que puedan exponer autorización.
- [ ] 2.3 Implementar `sample --post-id` sin escribir SQLite; verificar que conserva campos anidados y ausentes, no imprime la envoltura de paginación y no modifica ninguna base.
- [ ] 2.4 Añadir a la documentación los comandos de muestra y recopilación, el alcance de `/posts` y los campos solicitados; verificar que coinciden con `--help` y que explican las limitaciones de visibilidad de Facebook.

## 3. Filtro y persistencia SQLite

- [ ] 3.1 Implementar filtro literal OR con `casefold()` y reemplazo de expresiones mediante `--contains`; probar ambos valores predeterminados, diferencias de mayúsculas, corchetes literales, expresiones vacías, mensajes ausentes y selección sin `admin_creator`.
- [ ] 3.2 Implementar tabla `posts`, validación JSON, SQL parametrizado, UPSERT y transacción por página en la ruta configurable; verificar con SQLite temporal la integridad de mensaje/JSON, Unicode, campos adicionales, NULL, ID inválido y actualización sin duplicados.
- [ ] 3.3 Integrar lectura, filtro, almacenamiento y resumen de cantidades; probar que un fallo posterior conserva las páginas confirmadas, devuelve código no cero y que una nueva ejecución completa los resultados sin duplicarlos ni borrar coincidencias anteriores.
- [ ] 3.4 Documentar esquema, consultas SQL a `raw_json`, configuración OR, acumulación entre ejecuciones y retención manual; comprobar que los ejemplos SQL funcionan con una base de prueba y que se advierte sobre la eliminación de `cache/` y las rutas publicadas por Nikola.

## 4. Verificación integrada

- [ ] 4.1 Ejecutar las pruebas focalizadas con `unittest` en el entorno configurado, pasando por el entorno aislado del script cuando sea necesario para disponer de `keyring`; verificar que no usan la red, credenciales reales ni modifican el almacén del usuario. Ejecutar Ruff sobre Python cambiado si está disponible.
- [ ] 4.2 Registrar interactivamente el token autorizado y ejecutar una muestra real; verificar que `/me` corresponde a la página configurada, que el JSON no expone el token y que el comando no altera la base. Si no hay acceso disponible, registrar el bloqueo sin dar por realizada esta comprobación.
- [ ] 4.3 Ejecutar una recopilación real y repetirla, comprobar coincidencias y equivalencia semántica del JSON mediante consultas SQLite y confirmar ausencia de duplicados; revisar Git para garantizar que no se agregan credenciales ni bases, y que no cambian fuentes publicadas de Nikola. Si la API impide completar la recopilación, registrar el fallo real sin marcar esta tarea como terminada.
