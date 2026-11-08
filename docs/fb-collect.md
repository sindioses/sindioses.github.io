# Recopilar publicaciones de Facebook

La herramienta consulta las publicaciones accesibles de la página Sin Dioses y
las guarda en SQLite. No filtra por texto o publicador, no descarga imágenes ni
archivos y no genera artículos reStructuredText ni publica el sitio.

## Instalación y credencial

Desde la raíz del repositorio:

```powershell
uv sync --locked
uv run fb_posts.py --help
```

Se utiliza el entorno del proyecto y las versiones de `uv.lock`. No hay un
entorno aislado para este script. En Windows se utiliza Credential Manager;
otros sistemas necesitan un backend nativo seguro compatible con `keyring`.
La herramienta rechaza los backends de archivos, nulos y compuestos.

Obtén un token de página sin caducidad programada de **Sin Dioses App**:

1. En [Graph API Explorer](https://developers.facebook.com/tools/explorer/),
   selecciona Sin Dioses App y genera un token de usuario con acceso a la página,
   `pages_show_list`, `pages_read_engagement` y `pages_read_user_content`.
2. Usa [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)
   para extender el token de usuario a larga duración. Los controles de Meta
   pueden variar; consulta su [guía de tokens de larga duración](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived/).
3. Coloca el token de usuario extendido en Explorer y consulta
   `/me/accounts?fields=id,name,access_token,tasks`.
4. Copia el `access_token` de la entrada Sin Dioses, ID `115097879246`.
   Ese es el token de **página**; no guardes el token de usuario del paso anterior.
5. Comprueba en Debugger que el tipo sea Page, la aplicación Sin Dioses App,
   el token sea válido y su caducidad sea Nunca.

Registra el token en una terminal interactiva:

```powershell
uv run fb_posts.py credential set
```

El valor se pide con entrada oculta y se guarda bajo el servicio
`sindioses.fb-collect`, cuenta `115097879246`. Repite el comando para reemplazarlo
cuando caduque o pierda permisos. No pongas el token en argumentos, archivos,
capturas ni historial de comandos. Para otra página, utiliza `--page-id ID`
tanto al registrar la credencial como al consultar publicaciones.

La herramienta verifica `/me` antes de consultar posts: el token debe representar
la página elegida, no tu cuenta personal. También consulta `/debug_token` y verifica
el tipo PAGE, la página, la aplicación `1603408681013331`, la validez y la ausencia
de caducidad programada. El registro valida el nuevo token **antes** de reemplazar
la credencial anterior. No solicita contraseña ni secreto de la aplicación.
La prueba de identidad y los errores no muestran el token.

Para verificar la credencial guardada sin cambiarla ni tocar SQLite:

```powershell
uv run fb_posts.py credential check
```

El resumen distingue la caducidad del token de la caducidad del acceso a datos.
Esta última puede tener una fecha aunque el token indique Nunca. La herramienta
avisa cuando faltan siete días o menos y detiene la consulta si el acceso ya
caducó. En ese caso debes volver a autorizar la aplicación. Un token sin caducidad
programada también puede ser revocado por Meta; el programa no puede impedirlo
ni garantizar acceso perpetuo. No se realizan renovaciones automáticas.

El código 190 indica que Facebook rechazó el token; el subcódigo 463 confirma que
caducó la sesión. Obtén otro **token de página** mediante las herramientas de Meta
y vuelve a ejecutar `uv run fb_posts.py credential set` para reemplazarlo. Guardar
el mismo token caducado otra vez no lo renueva. Después repite el intervalo original;
las filas ya guardadas se omiten sin cambios salvo que uses `--force`.

## Consultar una muestra

```powershell
uv run fb_posts.py sample --post-id 115097879246_1580719907436079
```

La muestra presenta el JSON del post y sus campos accesibles. No crea ni modifica
la base SQLite. Consulta los mismos campos y aplica las mismas protecciones que
la recopilación completa.

## Recopilar por fechas

```powershell
uv run fb_posts.py collect 2026-01-01
uv run fb_posts.py collect 2026-01-01 2026-01-31
uv run fb_posts.py collect latest
uv run fb_posts.py collect 2026-01-01 2026-01-31 --force
```

Cyclopts convierte las fechas mediante sus tipos nativos; `YYYY-MM-DD` es la
forma recomendada. La aplicación no implementa otro analizador de fechas.
La fecha inicial es obligatoria. Los días se interpretan en
`America/Argentina/Buenos_Aires`: el inicial empieza a medianoche y un día final
explícito se incluye entero. Por ejemplo, enero de 2026 termina en el límite
exclusivo del 1 de febrero a medianoche. Sin fecha final, el límite es el instante
actual capturado una sola vez al comenzar. Se rechazan intervalos invertidos.

`latest` busca la fecha de publicación más reciente ya guardada para esa página,
la convierte al calendario local y vuelve a consultar desde el comienzo de ese
día. Las fechas NULL no participan; las fechas guardadas inválidas producen un
error. Sin historial utilizable debes indicar una fecha explícita.

Por defecto, los IDs existentes se omiten **sin modificar ningún campo**. Con
`--force` se actualizan el mensaje, fecha, enlace y JSON de Facebook; se conservan
siempre `author`, `category` y `slug`. Las publicaciones nuevas se insertan en
ambos casos. El resumen informa leídas, nuevas, omitidas y actualizadas.

La recopilación confirma las escrituras cada `BATCH_COMMIT_ITEMS` publicaciones
insertadas o actualizadas, con un valor predeterminado de 10. También confirma
las escrituras pendientes al terminar, ante errores y con Ctrl-C, que termina
con código 130. Cada inserción o actualización imprime
`Guardado post ID (FECHA)` con la fecha de publicación y su zona horaria;
si falta la fecha, muestra `fecha desconocida`. Los posts omitidos no lo emiten
ni cuentan para el lote. Los mensajes pueden preceder a la confirmación del lote.
Repite el **intervalo explícito original** para completar una
ejecución interrumpida: `latest` no prueba que las fechas anteriores estén completas,
pues Facebook puede devolver primero las publicaciones más nuevas.

Opciones no secretas de `collect`:

| Opción | Valor predeterminado |
| --- | --- |
| `--page-id` | `115097879246` |
| `--api-version` | `v26.0`, versión usada en las consultas verificadas por el usuario |
| `--database` | `../sindioses.db`, respecto de la ubicación del repositorio |

La ruta predeterminada no depende del directorio de ejecución y debe existir.
Una ruta alternativa se resuelve respecto del directorio actual y puede crear
una nueva base. Mantén bases y respaldos fuera de `files/`, `images/` y `output/`.

## Alcance del JSON y publicador

La consulta de la lista identifica los posts del período; para los nuevos o
actualizados se consulta el nodo completo con grupos de campos. Se intenta
descubrir campos mediante metadatos del nodo. Sin ellos se usa un inventario de
campos v26.0 contrastado con el
[modelo Post de Meta](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/post.py),
con un aviso de que no garantiza exhaustividad. Para otras versiones se requiere
descubrimiento de campos. La validación real de esta función depende del token y
la API; las pruebas locales usan respuestas simuladas.

El inventario alternativo omite los campos rechazados en las consultas v26.0:
`allowed_advertising_objectives`, `caption`, `comments_mirroring_domain`,
`description`, `is_app_share`, `link`, `name`, `object_id`, `source` y `type`.
Si los metadatos del nodo los anuncian, se consultan igualmente.

Los campos opcionales rechazados explícitamente se aíslan y se informa su nombre;
los errores generales de permisos, token, conexión o límite de solicitudes detienen
la ejecución. Se conservan los campos desconocidos y objetos anidados recibidos.
Algunos campos no disponibles producen errores genéricos 100, 10 o 200: antes de
aislarlos se comprueba que el mismo post permita leer sus campos básicos. Si esa
comprobación falla, la operación se detiene. Los campos retirados con un error 12
de obsolescencia también se aíslan, sin ocultar errores de acceso al post.
Se preservan las URI de imágenes y archivos tal como aparecen: no se visitan ni
se descargan sus recursos. Tampoco se recorren recursos o páginas adicionales
de adjuntos. No se recopilan comentarios, mensajes privados ni artículos enlazados.
Las URL técnicas de paginación se guardan sin tokens ni pruebas secretas.

Se solicita `admin_creator` y, si falta, se intenta una consulta directa adicional.
Sus datos se conservan en `raw_json` cuando Facebook los entrega. `from` puede ser
solo la página y no prueba quién publicó. No se deduce una persona por firmas o
menciones. El publicador de Facebook y el autor editorial pueden ser distintos:
`author` empieza en NULL incluso si el publicador es conocido.

## Base compartida y consultas

La base existente contiene tablas y vistas de otros usos. La primera incorporación
de `posts` genera un respaldo SQLite consistente con nombre
`sindioses.db.fb-posts-<identificador>.bak`, sin sobrescribir respaldos anteriores.
Una tabla `posts` incompatible provoca un error; no se transforma automáticamente.
Solo se agrega la tabla nueva y no se migran las tablas heredadas.

| Columna | Contenido |
| --- | --- |
| `id` | Clave primaria textual: ID completo de Facebook |
| `message` | Texto completo; NULL si no está presente, cadena vacía si así llega |
| `created_time` | Fecha original de Facebook o NULL |
| `permalink_url` | Enlace permanente original o NULL |
| `raw_json` | JSON validado de toda la estructura recuperada del post |
| `author` | Autor editorial local; inicialmente NULL |
| `category` | Categoría de Nikola; inicialmente NULL |
| `slug` | Slug del futuro artículo y stem de su archivo `.rst`; inicialmente NULL |

Los metadatos locales no se agregan al JSON de Facebook. Una futura clasificación
debe usar los nombres de `CATEGORY_DESTPATH_NAMES[DEFAULT_LANG]` de `conf.py`, no
sus claves de destino ni los códigos de secciones de la base heredada. Para ver
los nombres y destinos vigentes sin mantener una lista duplicada:

```powershell
uv run python -c "import conf; print(conf.CATEGORY_DESTPATH_NAMES[conf.DEFAULT_LANG])"
```

Por ejemplo, `escepticismo` es la clave de destino y `Escepticismo` el nombre a
guardar. El flujo futuro que genere `el-ateismo-ante-la-muerte.rst` guardará
`el-ateismo-ante-la-muerte` en `slug`. Esta herramienta no asigna esos valores.

Consultas para ejecutar con un cliente SQLite:

```sql
SELECT id, message, author, category, slug FROM posts ORDER BY created_time DESC;
SELECT id, json_extract(raw_json, '$.admin_creator.name') AS poster FROM posts;
SELECT id, json_extract(raw_json, '$.story') AS story FROM posts;
SELECT id, message FROM posts WHERE category IS NULL;
```

Las filas se conservan hasta que decidas retirarlas. La base no es una réplica de
Facebook: no se borran filas que dejan de aparecer. **No elimines `sindioses.db`
para limpiar publicaciones**: conserva las tablas, vistas y datos ajenos a `posts`.

## Salida y diagnósticos

La salida de consola usa Rich. El JSON de muestras se imprime sin interpretar
etiquetas de formato ni partir las cadenas largas, para conservar JSON válido.
Los diagnósticos van a stderr mediante Loguru: advertencias con `logger.warning`,
errores previstos con `logger.error` y fallos internos con el decorador `logger.catch`
de `main()`, conservando la salida de error y un código de terminación distinto de cero.
El logger se configura una sola vez al cargar el módulo, usa el formato predeterminado
y obtiene el nivel de `LOGURU_LEVEL`, usando INFO si la variable no existe.
Por ejemplo, `$env:LOGURU_LEVEL = "DEBUG"` permite ver los detalles de recopilación.
Los diagnósticos de metadatos ausentes y campos
no disponibles usan `logger.debug` e incluyen el ID de publicación.
Loguru no ofrece un método `logger.warn`. Las trazas de fallos internos conservan
las ubicaciones del código pero omiten variables, errores encadenados y mensajes
originales que podrían contener credenciales. No se crean archivos de registro.

## Verificación local

```powershell
uv run -m unittest discover -s tests -p 'test_fb_posts*.py'
```

Las pruebas no acceden a Facebook ni al keyring del usuario. Usan credenciales y
respuestas simuladas y bases SQLite temporales. Las pruebas reales requieren
registrar el token interactivamente y ejecutar una muestra y un intervalo pequeño.
