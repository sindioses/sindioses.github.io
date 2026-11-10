# Publicaciones de Facebook: recopilación y generación de artículos

`fb_posts.py` permite guardar publicaciones de Sin Dioses en SQLite y generar
artículos reStructuredText a partir de las publicaciones preparadas editorialmente.
`collect` recopila sin filtrar por texto o publicador y sin descargar imágenes;
`gen` escribe artículos y puede descargar imágenes. Ningún comando publica el sitio.

| Comando | Uso y efectos |
| --- | --- |
| `credential set` | Validar y guardar un token de página en el keyring |
| `credential check` | Verificar el token guardado sin escribir en SQLite |
| `sample` | Consultar y mostrar el JSON de un post sin guardarlo |
| `collect` | Guardar los posts accesibles del período en SQLite |
| `gen` | Crear archivos `.rst` e imágenes a partir de los posts preparados |

## Instalación

Desde la raíz del repositorio:

```powershell
uv sync --locked
uv run fb_posts.py --help
uv run fb_posts.py collect --help
uv run fb_posts.py gen --help
```

Se utiliza el entorno del proyecto y las versiones de `uv.lock`. No hay un
entorno aislado para este script. En Windows se utiliza Credential Manager;
otros sistemas necesitan un backend nativo seguro compatible con `keyring`.
La herramienta rechaza los backends de archivos, nulos y compuestos.

## Registrar o renovar un token vencido

La renovación consiste en obtener una autorización nueva y reemplazar el token
guardado. No se renueva automáticamente y volver a guardar un token vencido no
lo vuelve válido. El mismo procedimiento sirve para el primer registro.

Necesitas acceso a la página **Sin Dioses**, ID `115097879246`, y a
**Sin Dioses App**, ID `1603408681013331`, en las herramientas de Meta.
Trabaja en una sesión privada de tu navegador y una terminal interactiva local.
No pegues tokens o secretos en esta documentación, argumentos de terminal,
archivos, capturas, tickets, registros ni historial de comandos. Las únicas
herramientas web a las que se pegan tokens en este procedimiento son las de Meta.

### 1. Identificar la causa

Si el comando informa código **190**, Facebook rechazó la credencial; el
subcódigo **463** indica una sesión caducada. Si informa que caducó el acceso a
datos, también debes volver a autorizar la aplicación aunque el token diga Nunca.
Un token revocado o que perdió permisos requiere comprobar la autorización.

Puedes consultar el estado guardado con:

```powershell
uv run fb_posts.py credential check
```

Resultado esperado si está vencido: un diagnóstico y salida distinta de cero.
No borres el keyring ni SQLite para corregirlo. La comprobación no reemplaza la
credencial ni cambia posts. Si el problema es solo de conexión, comprueba la
conectividad antes de reemplazar un token que podría seguir siendo válido.

### 2. Abrir Explorer y elegir la aplicación correcta

Entra en [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
con la cuenta de Facebook que tiene acceso a Sin Dioses. En el selector de
aplicación, selecciona **Sin Dioses App** y confirma el ID `1603408681013331`.
Utiliza la versión `v26.0`, que es la predeterminada del script.

Resultado esperado: Explorer muestra esa aplicación y permite solicitar un
token de usuario. Si la app no está disponible, comprueba que la cuenta conectada
tenga acceso a ella; no continúes con otra aplicación de nombre parecido.

### 3. Obtener una autorización de usuario nueva

Usa el selector o control de generación de tokens de Explorer para obtener un
token de **usuario**. Inicia sesión de nuevo o confirma la autorización cuando
Meta lo solicite. Selecciona Sin Dioses entre las páginas autorizadas y concede:

- `pages_show_list`
- `pages_read_engagement`
- `pages_read_user_content`

Resultado esperado: un token de usuario nuevo y válido, asociado a la app
correcta y a la página seleccionada. Todavía no lo guardes con `credential set`:
el script necesita el token de página que se obtiene en el paso 5.

Los rótulos y posiciones de los controles de Meta pueden cambiar. Si no aparece
la opción para obtener autorización de usuario, revisa el selector de token, la
sesión conectada y la [guía de inicio de Pages API](https://developers.facebook.com/docs/pages-api/getting-started/).
No sustituyas este paso por copiar otra vez el token antiguo.

### 4. Extender el token de usuario mientras es válido

Abre [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/),
pega el token **nuevo de usuario** y solicita su inspección. Comprueba aplicación,
tipo User, validez y permisos. Si ofrece el control para extenderlo, úsalo y copia
el token extendido que devuelva. Vuelve a inspeccionarlo para confirmar su nueva
vigencia antes de continuar. Sigue la
[guía oficial de tokens de larga duración](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived/)
para el procedimiento de extensión que esté disponible para tu aplicación.

Resultado esperado: un token de usuario válido de larga duración. Extender un
token de usuario no lo convierte en token de página. Un token que ya caducó no
sirve para este paso: vuelve al paso 3 y obtén uno nuevo.

Si no aparece el control de extensión, comprueba primero que el token inspeccionado
sea User, válido y de la app correcta. Consulta la guía oficial antes de seguir;
no se documenta aquí un botón alternativo cuya disponibilidad no está verificada.
No pongas el secreto de la app en un comando de shell ni en un script del repositorio.
El programa no necesita guardar ese secreto para consultar publicaciones.

### 5. Obtener el token de Sin Dioses

Vuelve a Explorer y coloca el token de usuario **extendido** como token de la
consulta. Ejecuta una petición GET en `v26.0` con esta ruta:

```text
/me/accounts?fields=id,name,access_token,tasks
```

Busca en `data` la entrada cuyo `id` es `115097879246` y cuyo nombre es Sin Dioses.
Copia únicamente su campo `access_token`. Ese es el token de **página** que
debes usar en los pasos siguientes. La respuesta contiene credenciales: no la
guardes en archivos ni la compartas; conserva solo los datos no secretos necesarios.

Resultado esperado: la entrada de Sin Dioses con un `access_token` no vacío.
Si `data` está vacío o la página no figura, comprueba cuenta, página seleccionada
y permisos del paso 3. Si hay paginación, comprueba las demás páginas de resultados
en la herramienta de Meta. No elijas el token de otra página.

### 6. Verificar el token de página y sus dos caducidades

Inspecciona el token del paso 5 en Debugger. Comprueba:

| Dato | Valor esperado |
| --- | --- |
| Tipo | Page / PAGE |
| Página | `115097879246`, Sin Dioses |
| Aplicación | `1603408681013331`, Sin Dioses App |
| Válido | Verdadero |
| Permisos | Los tres permisos solicitados en el paso 3 |
| Caducidad del token | Nunca, sin caducidad programada; `expires_at` igual a `0` |
| Caducidad de acceso a datos | Una fecha futura, o `0` si Meta no declara plazo |

Resultado esperado: identidad, app y validez correctas, sin caducidad programada
del token. No confundas Nunca con acceso perpetuo: Meta puede revocarlo y el
acceso a datos puede tener una fecha de vencimiento independiente. El programa
avisa cuando faltan siete días o menos para ese plazo y rechaza el acceso vencido.

Si el tipo sigue siendo User, vuelve al paso 5. Si el token de página tiene una
caducidad programada, comprueba que se obtuvo usando el token de usuario extendido.
Si el acceso a datos ya venció, repite la autorización del paso 3; no ignores el
plazo ni reutilices el valor caducado. La falta de metadatos verificables también
impide registrar la credencial en el script.

### 7. Reemplazar la credencial del keyring

Desde la raíz del repositorio, en una terminal interactiva:

```powershell
uv run fb_posts.py credential set
```

En `Token de la página (entrada oculta):`, pega el token de página del paso 5 y
presiona Intro. No se debe mostrar el valor. El programa valida `/me` y
`/debug_token` antes de reemplazar la credencial guardada.

Resultado esperado: `Token guardado en el keyring del sistema.` y el resumen de
caducidades. Se usa el servicio `sindioses.fb-collect`, cuenta `115097879246`,
en el keyring nativo. Si la validación falla, el token previo no se reemplaza.
El registro no solicita contraseña de Facebook ni secreto de la app.

Para otra página se admite `--page-id ID`, y para otra versión `--api-version VERSION`;
usa los mismos valores en registro, comprobación, muestra y recopilación. La app
que valida el script sigue siendo Sin Dioses App.

### 8. Comprobar y retomar la recopilación

Comprueba lo que efectivamente quedó guardado:

```powershell
uv run fb_posts.py credential check
```

Resultado esperado: salida correcta y un resumen como
`Token de página válido; caducidad del token: nunca. Acceso a datos: FECHA_CON_ZONA.`
Si Meta declara `0` para acceso a datos, el resumen indica `sin fecha declarada`.
La comprobación no cambia SQLite ni vuelve a registrar el token.

Después repite el **intervalo explícito original** que quedó incompleto. Por
ejemplo, si estabas recopilando enero de 2026:

```powershell
uv run fb_posts.py collect 2026-01-01 2026-01-31
```

Resultado esperado: los IDs guardados se omiten y los faltantes se incorporan.
No agregues `--force` salvo que quieras actualizar campos de Facebook ya guardados.
No uses `latest` como prueba de recuperación completa: pueden faltar posts más
antiguos que la fecha más reciente almacenada. No se requiere borrar filas.

### Problemas durante el registro o la renovación

| Diagnóstico o situación | Qué comprobar |
| --- | --- |
| Código 190, subcódigo 463 | Obtener autorización nueva; no re-guardar el token vencido |
| Token User o página incorrecta | Copiar el token de la entrada exacta de `/me/accounts` |
| App incorrecta | Seleccionar Sin Dioses App antes de generar el token |
| Página ausente o permisos denegados, códigos 10/200 | Acceso de la cuenta y selección de página/permisos en la autorización |
| Caducidad programada | Derivar de nuevo la página desde un token de usuario extendido |
| Acceso a datos vencido o autorización revocada | Volver a autorizar la app y repetir la obtención de la página |
| Sin keyring seguro o sin entrada oculta | Usar un backend nativo y una terminal interactiva; no recurrir a archivos de texto |
| Metadatos de caducidad ausentes | Revisar el token en Meta; el script no supone que un dato ausente significa acceso ilimitado |

Referencias: [tokens de larga duración](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived/),
[depuración y errores de tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/debugging-and-error-handling/)
y [Pages API](https://developers.facebook.com/docs/pages-api/getting-started/).
Al revisar esta guía el 9 de noviembre de 2026, estas páginas devolvieron HTTP 429
o no fueron accesibles desde el entorno de revisión. El recorrido se contrastó
con el código y el procedimiento usado en el proyecto; no se verificaron los
rótulos actuales de la interfaz ni se realizó una renovación real. Si un control
no aparece, consulta la referencia oficial en tu sesión antes de continuar.

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
| `--force` | Desactivado; actualizar campos de Facebook de IDs existentes |
| `--log-level`, `-L` | `info`; selección de nivel, salvo que exista `LOGURU_LEVEL` |

La ruta predeterminada no depende del directorio de ejecución y debe existir.
Una ruta alternativa se resuelve respecto del directorio actual y también debe
existir: `--database` no crea un archivo de base nuevo. Mantén bases y respaldos
fuera de `files/`, `images/` y `output/`.

Para ver detalles de campos omitidos o posts existentes:

```powershell
uv run fb_posts.py collect 2026-01-01 2026-01-31 -L debug
```

Las fechas son argumentos posicionales; las opciones usan los nombres de la tabla.
La página predeterminada es `115097879246` y la versión `v26.0` corresponde a las
consultas verificadas del proyecto; no significa que sea la última versión de Meta.

## Generar artículos con `gen`

Este comando usa la base predeterminada `../sindioses.db`; no ofrece `--database`,
`--page-id` ni `--api-version`. No consulta posts de Facebook ni requiere un token
para leer la base. Si el post tiene una imagen elegida, puede realizar una descarga HTTP.

Antes de ejecutarlo:

1. Recopila los posts y revisa su contenido en SQLite.
2. Asigna `author`, `category` y `slug` editorialmente con un cliente SQLite.
   `collect` no los completa. Usa un slug revisado, sin extensión ni directorios,
   que será el nombre base del archivo `.rst`.
3. Comprueba que `category` corresponda a una clave `idseccion` de `secciones`,
   con `prefijo` no vacío. El generador utiliza ese prefijo como directorio y
   `nombreseccion` como categoría de Nikola. Los valores deben coincidir con las
   claves que devuelve la base; no se convierten automáticamente.
4. Asegúrate de que exista `posts/<prefijo>/`. El generador crea los directorios
   de imágenes cuando descarga, pero no crea el directorio del artículo.
5. Revisa que el mensaje tenga título en la primera línea y al menos un párrafo
   posterior separado por una línea vacía. La descripción se toma del segundo
   párrafo. El formateador adapta citas bíblicas, notas y referencias a imágenes;
   revisa editorialmente el resultado antes de publicarlo.

La selección exige `message`, `category`, `slug` y `author` no NULL y
`length(message) > 2000`; un texto de exactamente 2.000 caracteres queda excluido.
La condición SQL solo comprueba NULL para los metadatos, no que estén completos
o sean válidos. Los posts se procesan por `created_time` ascendente.

```powershell
uv run fb_posts.py gen
uv run fb_posts.py gen --partial-slug ateismo
uv run fb_posts.py gen -S ateismo -C 2026-11-01T00:00:00-03:00
uv run fb_posts.py gen -S ateismo -F -f -L debug
```

| Opción | Efecto |
| --- | --- |
| `--article-force`, `-F` | Sobrescribir artículos existentes; desactivado por defecto |
| `--image-force`, `-f` | Volver a descargar imágenes existentes; desactivado por defecto |
| `--cut-date`, `-C` | Seleccionar `created_time > fecha`, límite exclusivo; sin filtro por defecto |
| `--partial-slug`, `-S` | Buscar coincidencias parciales, sin filtro por defecto |
| `--log-level`, `-L` | Nivel de Loguru, `info` por defecto, sujeto a `LOGURU_LEVEL` |

`-F` y `-f` distinguen mayúsculas y minúsculas. La búsqueda de slug usa
`LIKE '%valor%'`: no exige coincidencia exacta y conserva los comodines SQL `%` y `_`.
Revisa los slugs seleccionados antes de usar las opciones de sobrescritura.
El filtro de fecha se aplica en SQLite; mantén representaciones de fechas
coherentes en la base, sin asumir que SQL normaliza zonas horarias diferentes.

Los artículos se escriben en UTF-8 en `posts/<prefijo>/<slug>.rst`. Se incorporan
autor, título, fecha, categoría, tipo, enlace original, descripción y cuerpo.
El nombre del archivo usa el slug existente; el comando no asigna slugs ni
actualiza `author`, `category` o `slug` en SQLite.

La única imagen seleccionada procede de
`raw_json.attachments.data[0].media.image.src`, si existe. Se conserva su extensión
y se guarda bajo `images/<prefijo>/<slug><extensión>`. Otras imágenes o adjuntos
no se descargan. Si la imagen ya existe, se reutiliza salvo que se indique `-f`.
Si el artículo ya existe y no se indica `-F`, se omite todo el post, incluida la
descarga: para regenerar un artículo y su imagen, usa ambos `-F -f`.

No hay modo de previsualización ni transacción conjunta para los archivos generados.
Un error puede dejar artículos o imágenes ya escritos. Comprueba las rutas,
revisa los `.rst` y las imágenes, y valida el sitio antes de una publicación
solicitada por separado. `gen` no compila ni despliega el sitio.

## Alcance del JSON y publicador durante la recopilación

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
| `created_time` | TIMESTAMP; fecha original de Facebook o NULL, convertida a `datetime` al leer con `open_database` |
| `permalink_url` | Enlace permanente original o NULL |
| `raw_json` | JSON validado de toda la estructura recuperada del post |
| `author` | Autor editorial local; inicialmente NULL |
| `category` | Clasificación editorial local; inicialmente NULL; para `gen` debe resolver a una sección |
| `slug` | Slug del artículo y stem de su archivo `.rst`; inicialmente NULL |

Los metadatos locales no se agregan al JSON de Facebook. La recopilación conserva
los valores originales de las fechas; el adaptador/conversor SQLite permite
leer TIMESTAMP como `datetime`. Cambiar el tipo de una tabla existente requiere
una migración aparte; el script no la realiza.

La especificación histórica de recopilación reservaba `category` para nombres
de `CATEGORY_DESTPATH_NAMES[DEFAULT_LANG]` y describía la generación como futura.
El `gen` actual requiere claves de `secciones.idseccion` y usa `nombreseccion`
para los metadatos de Nikola. No son representaciones intercambiables: para
generar, comprueba el mapeo que usa la implementación actual y revisa la categoría
resultante. Esta guía no cambia la especificación ni migra valores existentes.

Consultas de inspección, sin modificar clasificaciones:

```sql
SELECT idseccion, prefijo, nombreseccion FROM secciones
WHERE prefijo IS NOT NULL AND trim(prefijo) <> '';
SELECT category, slug, author, length(message) AS caracteres FROM posts
WHERE message IS NOT NULL AND category || slug || author IS NOT NULL
  AND length(message) > 2000;
```

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
`collect` y `gen` configuran el logger al comenzar, con el formato predeterminado.
`--log-level`/`-L` acepta `trace`, `debug`, `info`, `success`, `warning`, `error` y
`critical`; el valor predeterminado es `info`. Si existe `LOGURU_LEVEL`, esa
variable prevalece sobre la opción. Para los demás comandos no hay una opción
`-L`; usan la configuración inicial de Loguru.

```powershell
$env:LOGURU_LEVEL = "DEBUG"
uv run fb_posts.py collect 2026-01-01 -L info
Remove-Item Env:LOGURU_LEVEL
```

En ese ejemplo el nivel efectivo es DEBUG; al retirar la variable, vuelve a
aplicarse el nivel elegido por CLI. `Guardado post ID (FECHA)` es salida de
consola y no se oculta al cambiar el nivel de Loguru.
Los diagnósticos de metadatos ausentes y campos
no disponibles usan `logger.debug` e incluyen el ID de publicación.
Las validaciones previstas usan diagnósticos controlados. La configuración actual
de Loguru no desactiva globalmente la información de variables en las trazas de
errores inesperados: no compartas una traza sin revisar y ocultar posibles secretos
o datos privados. No se crean archivos de registro automáticamente.

## Verificación local

```powershell
uv run -m unittest discover -s tests -p 'test_fb_posts*.py'
```

Las pruebas no acceden a Facebook ni al keyring del usuario. Usan credenciales y
respuestas simuladas y bases SQLite temporales. Las pruebas reales requieren
registrar el token interactivamente y ejecutar una muestra y un intervalo pequeño.
