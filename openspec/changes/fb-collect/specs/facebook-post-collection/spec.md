# Spec Delta

## Purpose

Recopilar automáticamente publicaciones de Facebook que coincidan con expresiones textuales configurables y conservar sus datos completos en SQLite para consultas locales posteriores.

## ADDED Requirements

### Requirement: Credenciales en el keyring del sistema
El script MUST permitir registrar o reemplazar un token de página mediante entrada oculta y recuperarlo del keyring seguro del sistema operativo para recopilar publicaciones. MUST detenerse si el token o un backend seguro no están disponibles, sin recurrir a almacenamiento en texto plano.

#### Scenario: Registro y recuperación
- **WHEN** el usuario registra un token para la página y luego ejecuta una recopilación
- **THEN** el token se guarda en el keyring del sistema y se recupera sin pedirlo nuevamente ni mostrarlo

#### Scenario: Credencial o backend ausentes
- **WHEN** no existe un token guardado o no hay un backend seguro disponible
- **THEN** el script termina con código distinto de cero y explica cómo configurar la credencial sin crear un archivo de secretos

### Requirement: Lectura autorizada de la página
El script MUST leer publicaciones mediante solicitudes GET a una versión explícita de Graph API y un token de la página configurada. La página predeterminada MUST ser `115097879246`, correspondiente a SinDioses.org. MUST verificar que la identidad del token coincide con la página antes de recopilar.

#### Scenario: Página correcta
- **WHEN** el token corresponde a la página configurada
- **THEN** el script consulta sus publicaciones solicitando `id`, `message`, `created_time`, `permalink_url`, `from` y `admin_creator`

#### Scenario: Token de otra identidad
- **WHEN** la identidad del token no corresponde a la página configurada
- **THEN** el script rechaza la recopilación con un diagnóstico sin secretos

### Requirement: Paginación completa
El script MUST procesar todas las páginas de resultados hasta agotar la paginación y MUST mantener la autenticación limitada al servidor Graph API autorizado. Una página sin coincidencias MUST NOT detener la recopilación si existe una página siguiente.

#### Scenario: Coincidencia posterior
- **WHEN** la primera página no contiene coincidencias pero la siguiente sí
- **THEN** el script continúa y almacena las coincidencias de la página siguiente

#### Scenario: Fin de resultados
- **WHEN** Facebook devuelve una colección vacía sin página siguiente
- **THEN** la recopilación termina correctamente sin insertar publicaciones

### Requirement: Filtro parcial configurable
El script MUST seleccionar un post cuando su `message` contenga al menos una expresión configurada, sin distinguir mayúsculas y minúsculas. Los valores predeterminados MUST ser `Iván Gonzáles Mairena` y `[Godless Freeman]`. Las expresiones MUST ser literales; una configuración personalizada MUST reemplazar los valores predeterminados y rechazar expresiones vacías.

#### Scenario: Firma coincidente
- **WHEN** un mensaje contiene `[GODLESS FREEMAN]` entre otros párrafos
- **THEN** la publicación coincide sin necesitar el nombre de Iván

#### Scenario: Expresiones personalizadas
- **WHEN** el usuario configura únicamente `otra firma`
- **THEN** se seleccionan solo mensajes que contengan esa expresión sin distinguir mayúsculas

#### Scenario: Texto ausente o sin coincidencias
- **WHEN** una publicación no tiene `message`, tiene un mensaje vacío o no contiene ninguna expresión
- **THEN** no se almacena y la recopilación continúa

### Requirement: La coincidencia textual no atribuye al publicador
El script MUST filtrar independientemente de la presencia de `admin_creator` y MUST NOT deducir el publicador a partir de una firma, mención o campo ausente. La documentación MUST explicar que el filtro identifica contenido textual y puede incluir menciones o excluir textos sin firma.

#### Scenario: Firma sin atribución
- **WHEN** un mensaje contiene `[Godless Freeman]` y Facebook omite `admin_creator`
- **THEN** se almacena por su contenido sin añadir una identidad de publicador al JSON

### Requirement: Persistencia del post completo
SQLite MUST guardar únicamente las coincidencias con `id` como clave primaria textual y columnas `message`, `created_time`, `permalink_url` y `raw_json`. `raw_json` MUST ser texto con validación JSON y conservar sin pérdida semántica todo el objeto de publicación recibido, con campos anidados o desconocidos. Los campos opcionales ausentes MUST conservarse como NULL en sus columnas.

#### Scenario: Conservación de campos adicionales
- **WHEN** Facebook devuelve un post coincidente con metadatos adicionales y estructuras anidadas
- **THEN** `raw_json` contiene el objeto completo, incluido su mensaje íntegro, y sus columnas extraídas corresponden al mismo post

#### Scenario: Fechas y enlaces ausentes
- **WHEN** un post coincidente tiene ID y mensaje pero carece de fecha o enlace
- **THEN** esas columnas son NULL y el JSON preserva la ausencia original

#### Scenario: Identificador ausente
- **WHEN** un objeto de publicación no tiene un ID válido
- **THEN** el script informa un error de respuesta y no inventa una clave

### Requirement: Repetición y retención local
La recopilación MUST actualizar por ID las coincidencias ya existentes sin duplicarlas. La base MUST permanecer disponible entre ejecuciones hasta que el usuario la elimine y MUST estar por defecto en `cache/fb-collect.sqlite3`, fuera del sitio publicado. El usuario MUST poder elegir otra ruta local de base.

#### Scenario: Segunda recopilación
- **WHEN** se recibe nuevamente una publicación coincidente con el mismo ID y texto actualizado
- **THEN** se actualizan sus columnas y JSON en una sola fila

#### Scenario: Cambio de filtro
- **WHEN** se ejecuta otra recopilación con expresiones diferentes
- **THEN** se agregan o actualizan las nuevas coincidencias sin eliminar filas almacenadas anteriormente

### Requirement: Errores y confidencialidad
El script MUST terminar con código distinto de cero ante fallos de autenticación, permisos, transporte o respuesta inválida. MUST conservar las páginas previamente confirmadas en SQLite e indicar que la ejecución quedó incompleta. Tokens, cabeceras de autorización y URL de paginación con secretos MUST NOT aparecer en logs, base de datos ni mensajes de error.

#### Scenario: Fallo después de una página almacenada
- **WHEN** Facebook rechaza una página posterior
- **THEN** las filas ya confirmadas siguen disponibles y se informa una recopilación incompleta sin exponer el token

### Requirement: Consulta inicial de muestra
El script MUST ofrecer una consulta de un solo post para inspeccionar el objeto JSON antes de una recopilación completa, sin modificar la base. Esta consulta MUST usar el keyring y las mismas reglas de autenticación y confidencialidad.

#### Scenario: Inspección de un post
- **WHEN** el usuario solicita una muestra mediante un ID de post
- **THEN** se presenta su objeto JSON sin envoltura de paginación y no se insertan filas
