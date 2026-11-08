# Spec Delta

## Purpose

Ingest all API-accessible Facebook Page posts within a requested date range and preserve their complete data and local category metadata in an existing SQLite database.

## ADDED Requirements

### Requirement: Structured diagnostics and literal console output
Loguru MUST be configured outside commands with its default format. Warnings MUST use `logger.warning()`, expected failures MUST use `logger.error()`, and `main()` MUST use `logger.catch` for unexpected failures with nonzero exit status. Logs MUST omit sensitive locals, original exception messages, and chained errors. Console output MUST use Rich while preserving literal, valid sample JSON including long strings. Dependencies MUST be declared in the project.

#### Scenario: Stored post progress
- **WHEN** a post is inserted or updated
- **THEN** the collector prints `Guardado post {id} ({date})` after writing the row, including its aware publication timestamp or `fecha desconocida` when missing
- **AND** skipped posts produce no progress message

#### Scenario: Batch persistence
- **WHEN** `BATCH_COMMIT_ITEMS` posts have been inserted or updated, default 10
- **THEN** the collector commits pending writes, counting across listing pages and excluding skips
- **AND** normal completion or any error also commits the remaining completed writes

#### Scenario: Operator interrupts collection
- **WHEN** Ctrl-C interrupts processing of the current result page
- **THEN** all previously stored posts, including those from the current page, remain committed and included in the counts before interruption propagates
- **AND** the CLI exits with status 130

#### Scenario: Field diagnostics do not clutter operator output
- **WHEN** field metadata is missing or an optional field is unavailable
- **THEN** the collector logs the diagnostic through `logger.debug()` with the post ID
- **AND** the stderr sink uses `LOGURU_LEVEL` when set, otherwise INFO, hiding those diagnostics by default

#### Scenario: Expected operational error
- **WHEN** an API or credential failure produces a safe diagnostic
- **THEN** it is logged at ERROR level without a traceback and the CLI exits nonzero

#### Scenario: Unexpected failure with sensitive context
- **WHEN** an internal exception contains sensitive locals, a raw message, or a chained exception
- **THEN** the CLI logs an exception stack without those values and exits nonzero

#### Scenario: Sample contains markup-like text
- **WHEN** a sample contains literal Rich-like markup or a long message string
- **THEN** console output remains valid JSON with the original string content

### Requirement: Validate long-lived Page credentials
Registration MUST validate credentials before replacing a stored token. Registration and API use MUST verify the selected Page identity, PAGE token type/profile, Sin Dioses App ID, validity, and explicit zero scheduled expiry. User tokens, missing expiry metadata, and tokens with scheduled expiration MUST be rejected without exposing secrets. A read-only `credential check` command MUST report token and data-access expiration independently.

#### Scenario: Wrong credential supplied
- **WHEN** the supplied credential represents a User or has scheduled expiration
- **THEN** registration rejects it and leaves the previous keyring entry unchanged

#### Scenario: Valid Page credential
- **WHEN** the stored token represents the selected Page, is valid for Sin Dioses App, and has zero scheduled expiry
- **THEN** checking it reports the separate data-access deadline without changing the keyring or SQLite

### Requirement: Respect data-access expiration
The collector MUST distinguish token expiration from `data_access_expires_at`, warn within seven days of a positive data-access deadline, and reject expired data access. Zero MUST mean no deadline was declared; missing metadata MUST NOT be treated as unlimited access. Documentation MUST explain that Meta may still revoke access or require reauthorization; the CLI MUST NOT claim perpetual validity or automatic renewal.

#### Scenario: Token never expires but data access does
- **WHEN** token expiry is zero and data access has a future deadline
- **THEN** the check displays both facts and warns only when the deadline is within seven days

#### Scenario: Data-access deadline passed
- **WHEN** data access has expired despite zero token expiry
- **THEN** the operation stops before post retrieval and asks the user to reauthorize the app

### Requirement: Cyclopts command interface
The CLI MUST use Cyclopts and expose `collect INITIAL_DATE [FINAL_DATE] [--force]`. The mandatory initial argument MUST use built-in date conversion or `Literal["latest"]`; the optional final argument MUST use built-in date conversion. Documentation MUST show `YYYY-MM-DD`. Custom CLI date/datetime parsing or redundant format validation MUST NOT be implemented. Invalid CLI dates MUST fail before API calls or database mutation.

#### Scenario: Missing or malformed initial date
- **WHEN** ingestion is invoked without an initial date or with a value rejected by Cyclopts date conversion, such as `not-a-date` or an impossible date
- **THEN** Cyclopts reports an argument error and ingestion does not start

#### Scenario: Valid invocation
- **WHEN** ingestion is invoked with `2026-01-01 2026-01-31 --force`
- **THEN** the CLI resolves the requested interval and enables explicit replacement

#### Scenario: Library-supported date formats
- **WHEN** Cyclopts successfully converts a supplied date using its built-in conversion
- **THEN** application code receives the typed date and does not reparse it or reject it through a separate format policy

### Requirement: Project environment invocation
The collector MUST run directly as `uv run fb_posts.py` using the repository's project environment. Its dependencies MUST be declared in `pyproject.toml` and resolved in `uv.lock` together. It MUST NOT require PEP 723 script dependencies or a separate script environment.

#### Scenario: Documented invocation
- **WHEN** the user installs dependencies with `uv sync --locked` and runs `uv run fb_posts.py --help`
- **THEN** the CLI displays help using project dependencies without script-specific setup

### Requirement: Date interval semantics
Calendar dates MUST use `America/Argentina/Buenos_Aires`. The initial day MUST be inclusive from midnight. An explicit final day MUST be inclusive through that day, represented by an exclusive next-midnight bound. If final date is omitted, ingestion MUST use the current timestamp captured once at command start as its exclusive upper bound. Reversed or empty intervals MUST fail before ingestion.

#### Scenario: Explicit final day
- **WHEN** ingestion is requested from `2026-01-01` to `2026-01-31`
- **THEN** the interval starts at January 1 local midnight and ends exclusively at February 1 local midnight

#### Scenario: Default final instant
- **WHEN** ingestion starts without a final date
- **THEN** every request uses the same upper bound captured at command start rather than a moving current time

#### Scenario: Reversed interval
- **WHEN** the initial day is later than the explicit final day
- **THEN** the command reports a validation error without ingesting data

### Requirement: Resolve latest from stored posts
`latest` MUST resolve to the local calendar date of the most recent stored `created_time` for the selected Page, comparing parsed aware timestamps. It MUST re-read that entire day. NULL timestamps MUST be ignored; malformed non-NULL timestamps MUST cause a diagnostic error. If no usable stored date exists, the command MUST request an explicit initial date without ingesting data.

#### Scenario: Existing history
- **WHEN** the most recent stored post was created at `2026-01-06T01:48:35+0000`
- **THEN** `latest` begins January 5 at midnight in Buenos Aires, including that entire local day

#### Scenario: No usable history
- **WHEN** `latest` is requested with no `posts` table, no rows for the selected Page, or only NULL timestamps
- **THEN** ingestion fails clearly and asks for an explicit initial date

#### Scenario: Other Page history
- **WHEN** the database contains a newer post belonging to another Page
- **THEN** that post does not affect the selected Page's `latest` date

### Requirement: Credentials in the system keyring
The script MUST support hidden registration or replacement of a Page token and retrieve it from the operating system's secure keyring for API access. It MUST stop if a token or secure backend is unavailable, without falling back to plaintext storage.

#### Scenario: Registration and retrieval
- **WHEN** the user registers a token and then runs ingestion
- **THEN** the token is retrieved from the secure keyring without displaying it or requesting it again

#### Scenario: Missing credential or secure backend
- **WHEN** a token or secure backend is unavailable
- **THEN** the script exits nonzero with setup instructions and does not create a secrets file

### Requirement: Authorized unfiltered Page ingestion
The script MUST read posts through GET requests to an explicit Graph API version using a token verified against the selected Page. The default Page MUST be `115097879246`. It MUST ingest every returned post within the resolved bounds regardless of text or publisher attribution and retrieve the full accessible structure for new or forcibly refreshed posts. No content filter MUST be exposed.

#### Scenario: Text without signatures
- **WHEN** the API returns a post in the requested interval whose message contains neither a person's name nor a signature
- **THEN** the post is ingested subject only to ID conflict rules

#### Scenario: Missing text or publisher
- **WHEN** a returned post has no `message` or `admin_creator`
- **THEN** it remains eligible for ingestion without inventing text or a publisher identity

#### Scenario: Token for another identity
- **WHEN** `/me` does not match the configured Page
- **THEN** ingestion is rejected with a diagnostic containing no secrets

### Requirement: Complete bounded pagination
The script MUST traverse all result pages using the same resolved date bounds until pagination ends. It MUST keep authentication limited to the authorized Graph API server and MUST continue when a page contains only previously stored IDs. Invalid or repeated cursors MUST produce an error rather than an endless traversal.

#### Scenario: Later new IDs
- **WHEN** the first page contains only existing IDs but a later page contains new IDs
- **THEN** ingestion continues and inserts the new posts

#### Scenario: Empty result
- **WHEN** Facebook returns no posts and no next page
- **THEN** ingestion completes successfully without inserting rows

### Requirement: Complete post persistence
SQLite MUST store posts in `posts` with textual primary key `id` and columns `message`, `created_time`, `permalink_url`, `raw_json`, `author`, `category`, and `slug`. Missing optional API fields MUST be NULL. `raw_json` MUST be validated JSON text preserving the complete retrieved post structure without semantic loss, except credential sanitization in transport URLs. Invalid post IDs MUST cause a response error rather than an invented key.

#### Scenario: Additional fields
- **WHEN** a new post includes extra metadata and nested objects
- **THEN** all fields remain in `raw_json` and extracted API columns correspond to the same object

#### Scenario: Missing or empty message
- **WHEN** a new post lacks `message` or explicitly contains an empty string
- **THEN** the column is NULL or an empty string respectively and JSON preserves the original representation

### Requirement: Preserve existing IDs unless forced
Ingestion MUST leave every field of an existing row unchanged by default. With `--force`, it MUST update only Facebook-derived fields and `raw_json` for existing IDs while preserving `author`, `category`, and `slug`. New IDs MUST be inserted with or without `--force`. Neither mode MUST delete rows absent from results.

#### Scenario: Default skip
- **WHEN** the API returns changed content for an already stored ID without `--force`
- **THEN** the row remains entirely unchanged and is counted as skipped

#### Scenario: Forced refresh
- **WHEN** the same ID is ingested with `--force`
- **THEN** Facebook fields and JSON are refreshed in the existing row, its author, category, and slug are preserved, and it is counted as updated

#### Scenario: New ID during forced ingestion
- **WHEN** a previously unseen ID arrives with `--force`
- **THEN** it is inserted once with NULL author, category, and slug

### Requirement: Nikola category metadata
The nullable `category` field MUST start as NULL for new rows. Assigned categories MUST correspond to display names from `CATEGORY_DESTPATH_NAMES[DEFAULT_LANG]` in `conf.py`. Ingestion MUST NOT assign, clear, or infer categories or add local classification to `raw_json`. Classification, reStructuredText conversion, and publication remain future operations.

#### Scenario: Classified post refreshed
- **WHEN** a post with category `Escepticismo` is ingested again, including with `--force`
- **THEN** the category remains `Escepticismo` and local classification is not added to the Facebook JSON

### Requirement: Nikola article slug metadata
The `slug` field MUST be nullable text and initially NULL. It MUST hold the Nikola article slug, matching the generated `.rst` filename stem, when a future article-generation workflow stores it. Ingestion MUST NOT generate, assign, or clear slugs, including with `--force`, or add local slug metadata to `raw_json`. Article generation remains outside this change's scope.

#### Scenario: Newly ingested post
- **WHEN** a post is inserted for the first time
- **THEN** its slug is NULL regardless of whether Facebook returns any similarly named field

#### Scenario: Generated article ingested again
- **WHEN** a stored row has slug `el-ateismo-ante-la-muerte` for the article file `el-ateismo-ante-la-muerte.rst` and the post is ingested again with or without `--force`
- **THEN** its slug remains unchanged and ingestion does not inject local slug metadata into the original JSON

### Requirement: Shared database preservation and retention
The default database MUST be the existing `../sindioses.db`, resolved from the repository root independently of working directory. The script MUST allow another path, preserve unrelated objects and data, and back up an existing database before adding `posts` without overwriting a backup. Missing default files or incompatible tables MUST fail safely. Stored rows MUST persist until deliberately removed; cleanup MUST NOT delete the shared database.

#### Scenario: Existing legacy database
- **WHEN** ingestion first initializes a database with legacy objects and no `posts` table
- **THEN** it creates a consistent backup and adds `posts` without altering legacy objects or data

#### Scenario: Different working directory
- **WHEN** the script runs from another directory without an override
- **THEN** it uses the same repository sibling database

#### Scenario: Unsafe initialization
- **WHEN** the default file is missing or an existing `posts` schema is incompatible
- **THEN** the command fails without replacing the database or modifying its existing objects

### Requirement: Partial failures and safe diagnostics
Authentication, permission, transport, and invalid-response failures MUST return a nonzero exit code and preserve previously committed posts, including those from the current result page. Diagnostics MUST indicate incomplete ingestion without exposing tokens, authorization headers, or secret-bearing URLs. Documentation MUST explain that `latest` is not proof of complete history and an interrupted traversal requires rerunning the original explicit interval.

#### Scenario: Failure after committed posts
- **WHEN** a subsequent API request fails
- **THEN** earlier rows remain stored and the error explains that the interval is incomplete without exposing the token

### Requirement: Initial sample query
The script MUST offer a single-post query using the keyring and the same authentication and confidentiality rules. It MUST display the complete post object without the outer listing envelope, preserve returned nested structures, and MUST NOT modify the database.

#### Scenario: Post inspection
- **WHEN** the user requests a sample by ID
- **THEN** its JSON is displayed and no database rows are changed

### Requirement: Full accessible post structure
Retrieval MUST request all readable Post fields supported by the selected API version and permissions, independently of extracted database columns. It MUST retain unknown fields and nested attachment information returned with the post. It MUST preserve declared media URIs without fetching images or files or rewriting URIs. Separate attachment traversal, comments, and binary downloads are excluded. Unavailable fields MUST be reported without claiming universal completeness.

#### Scenario: Post beyond the database projection
- **WHEN** a post exposes fields such as `story`, `message_tags`, `application`, or nested attachments beyond the extracted SQLite columns
- **THEN** retrieval requests those fields and retains the returned data in `raw_json` rather than archiving only the earlier six-field projection

#### Scenario: Optional field unavailable
- **WHEN** the API explicitly rejects a particular optional field
- **THEN** retrieval isolates that field, continues requesting the other readable fields, and reports the limitation without exposing secrets

#### Scenario: Known rejected fields without metadata
- **WHEN** node metadata is absent and the v26.0 fallback inventory is used
- **THEN** requests omit `allowed_advertising_objectives`, `caption`, `comments_mirroring_domain`, `description`, `is_app_share`, `link`, `name`, `object_id`, `source`, and `type`
- **AND** if node metadata advertises these fields, retrieval still requests them

#### Scenario: Ambiguous optional-field error
- **WHEN** a field request returns generic code 10, 100, or 200 while a probe confirms the same post's core fields are readable
- **THEN** retrieval splits the failed group and isolates unavailable optional fields without discarding readable post data

#### Scenario: Access probe fails
- **WHEN** a generic field-request error is followed by a failed core-field probe
- **THEN** collection fails as incomplete instead of silently skipping the access failure

#### Scenario: Deprecated optional field
- **WHEN** an optional field returns code 12 with an explicit deprecation error
- **THEN** retrieval isolates that field and continues requesting the other readable fields

#### Scenario: Referenced images and files
- **WHEN** the returned post JSON contains image or file URIs and nested attachment metadata
- **THEN** those URIs and metadata are preserved without fetching the referenced resources, rewriting URIs, or following attachment pagination links

#### Scenario: General request failure
- **WHEN** full retrieval encounters an authentication, transport, rate-limit, or malformed-response failure
- **THEN** the run fails as incomplete rather than treating the failure as an unavailable optional field

### Requirement: Best-effort publisher identity
The script SHOULD obtain the human publisher identity through available API attribution fields, including `admin_creator`, and a direct post lookup if listing attribution is absent. It MUST preserve returned identity details in `raw_json`. Missing or inaccessible attribution MUST NOT exclude a post. The script MUST NOT infer the person from Page identity, message signatures, or mentions.

#### Scenario: Direct lookup exposes publisher
- **WHEN** the listing omits attribution but a direct post lookup returns `admin_creator`
- **THEN** its returned identity details are retained in the archived post structure

#### Scenario: Publisher unavailable
- **WHEN** publisher attribution remains unavailable and `from` identifies only the Page
- **THEN** the post is ingested without inventing a human publisher

### Requirement: Nullable local author metadata
The `author` column MUST be nullable text and initially NULL even when publisher details are available. It is reserved for later editorial attribution. Ingestion MUST NOT assign or clear it, including with `--force`, or inject it into `raw_json`. The API publisher identity MUST remain distinct from this local author field.

#### Scenario: Publisher known on insertion
- **WHEN** a new post includes a named `admin_creator`
- **THEN** the identity is retained in `raw_json` while `author` remains NULL

#### Scenario: Editorial author already assigned
- **WHEN** an existing row with a non-NULL author is forcibly refreshed
- **THEN** its author remains unchanged while API fields and the complete post JSON are refreshed
