# Tasks

## 1. Cyclopts CLI and credentials

- [x] 1.1 Add `cyclopts`, `keyring`, and Windows-only `tzdata` to the project's `pyproject.toml` using uv, updating `uv.lock` together; verify `uv sync --locked` succeeds without introducing a separate script environment.
- [x] 1.2 Create `fb_posts.py` without a PEP 723 dependency block, exposing `credential set`, `sample`, and `collect`; verify `uv run fb_posts.py --help` works in the project environment and Spanish help exposes mandatory `INITIAL_DATE`, optional `FINAL_DATE`, `--force`, and database/Page/version options without content filters.
- [x] 1.3 Implement hidden token registration, replacement, and retrieval using a secure native backend; test service/account selection, missing tokens, insecure backends, and safe errors with a substitute backend.
- [x] 1.4 Document installation through `uv sync --locked`, direct invocation through `uv run fb_posts.py`, and token setup and renewal through Sin Dioses App and Windows Credential Manager; verify examples avoid secrets in arguments, files, or command history and agree with CLI help.

## 2. Date bounds and stored history

- [x] 2.1 Declare the initial CLI argument as `date | Literal["latest"]` and final argument as `date | None`, relying on Cyclopts built-in conversion without custom date/datetime parsing or redundant format checks. Implement only site-timezone bounds, range validation, and a single captured current timestamp; verify typed values reach the command, invalid/missing inputs cause no external effects, and test reversed ranges, inclusive calendar days, and fixed default bounds.
- [x] 2.2 Resolve `latest` from parsed aware timestamps for the selected Page, ignoring NULL and rejecting malformed timestamps; test no table, no usable dates, other-Page rows, equivalent instants with different offsets, and conversion from UTC to the previous Buenos Aires calendar day.
- [x] 2.3 Document `YYYY-MM-DD` examples, Cyclopts-owned date conversion, timezone, inclusive explicit end days, the current-instant default, empty-history errors, and overlapping `latest` runs; verify examples against date-resolution tests and explain recovery by rerunning the original explicit interval after a partial failure.

## 3. Authorized retrieval and pagination

- [x] 3.1 Implement HTTPS GET with an explicit version, Bearer header, timeout, and Page identity check; test incorrect identities, insufficient permissions, token expiration, invalid JSON, and safe diagnostics using substitute transport.
- [x] 3.2 Implement `/{page-id}/posts` ingestion with `since`/`until` and cursor pagination retaining fixed bounds; test multiple pages, pages containing only existing IDs, empty results, repeated cursors, and rejection of authorization-exposing redirects. Verify posts with missing text, absent publisher attribution, or unrelated text are all retained.
- [x] 3.3 Implement sample retrieval without database writes; test complete nested JSON preservation and omission of only the outer listing envelope, and document samples and the API visibility limits of Page posts versus comments, inbox messages, and media.
- [x] 3.4 Implement full post retrieval independently of the listing projection: verify API field discovery where supported and a version-aware inventory against Meta's reference/official SDK, request all readable Post fields in bounded groups, and isolate specifically unavailable fields; test unknown properties, optional-field rejection, preservation of returned attachment metadata and exact media URIs, safe transport URL sanitization, and fatal general request failures. Verify no media URI, separate attachment resource, or attachment pagination link is fetched, no files are downloaded, and samples use the same retrieval path. Document actual API limitations.
- [x] 3.5 Implement best-effort publisher lookup through `admin_creator` and direct post lookup when listing attribution is absent; test available, missing, and explicitly inaccessible identities, preservation of returned identity details in `raw_json`, and no inference from Page identity, signatures, or mentions.
- [x] 3.6 Omit the ten optional fields rejected in the user's v26.0 queries from the fallback inventory to avoid repeated failed requests. Verify actual fallback requests exclude them and metadata-based discovery can still include them.

## 4. SQLite ingestion and local metadata preservation

- [x] 4.1 Resolve the existing `../sindioses.db` default independently of working directory and retain overrides; test missing default files, incompatible schemas, backups that do not overwrite existing files, and creation of only `posts` without altering legacy objects or rows.
- [x] 4.2 Implement nullable-message storage, JSON validation, parameterized inserts, batched transactions, and nullable `author`, `category`, and `slug` columns defaulting to NULL; test Unicode, complete post structures beyond extracted columns, missing versus empty messages, NULL dates, invalid IDs, and initial NULL metadata even with a known API publisher.
- [x] 4.3 Implement default conflict skipping and forced updates of API fields only; test byte-for-byte preservation of existing row values without `--force`, refreshed complete JSON with `--force`, new-ID insertion in both modes, and preservation of assigned author, category, and slug values in all cases. Verify ingestion never injects local metadata into `raw_json`.
- [x] 4.4 Integrate ingestion with read/inserted/skipped/updated counts and failure handling; test repeated and overlapping periods, committed-post preservation after failure, and completion by rerunning the explicit interval without duplicate rows or deletion of earlier records.
- [x] 4.5 Document the schema, configured category names and destination keys, SQL queries, shared database backups, row retention, and `--force`; check examples against a test database and explain initial NULL author/category/slug, API publisher versus editorial author, slug as the future `.rst` stem, full-structure retrieval limits, preservation of legacy data, and future conversion/publication as out of scope.

## 5. Integration verification

- [x] 5.1 Run focused `unittest` tests in the configured shared project environment; verify tests use no network or real credentials and do not modify the user's credential store. Run Ruff on changed Python files if available.
- [x] 5.2 Register an authorized token interactively and retrieve a real sample; confirm the Page identity, complete JSON, no exposed secrets, and no database mutation. Record unavailable access as a blocker rather than marking unperformed checks complete.
- [x] 5.3 Ingest a small explicit interval into the backed-up shared database, repeat it without force, then test `latest` and an explicit forced interval; verify skip/update counts, no duplicates, preservation of assigned author/category/slug, complete accessible post data with unchanged returned media URIs and no file downloads, attempted poster lookup, and unchanged unrelated database objects and data. Review Git for accidental credentials, database files, or changes to published sources; record actual API blockers and unavailable fields without claiming universal completeness.

## 6. Long-lived credential validation

- [x] 6.1 Validate Page identity, PAGE type/profile, Sin Dioses App, validity, and zero scheduled token expiry before keyring replacement and API use; verify wrong-identity registration preserves the previous credential and metadata tests reject User, wrong-app, short-lived, missing-expiry, and invalid tokens.
- [x] 6.2 Add `credential check`, separate data-access expiration from token expiration, warn within seven days, and reject expired data access; verify deterministic deadline tests and the live stored Page token report no scheduled expiry and data access until `2027-02-04T15:48:48-03:00`.
- [x] 6.3 Document long-lived User-to-Page token setup and the limits of scheduled expiry guarantees, update planning artifacts, and verify 81 automated tests, Ruff, and strict OpenSpec validation. Live credential verification does not modify SQLite.

## 7. Loguru diagnostics and Rich output

- [x] 7.1 Declare Loguru and Rich as direct project dependencies and replace warning callbacks with direct Loguru calls. Field diagnostics use `logger.debug` with the post ID; operator warnings use `logger.warning`. Configure stderr using `LOGURU_LEVEL`, defaulting to INFO, and verify diagnostics through a Loguru sink.
- [x] 7.2 Configure Loguru outside commands using its default format, route expected failures through `logger.error`, and decorate `main()` with `logger.catch` for unexpected failures and nonzero exit status; disable traceback variable dumps and sanitize raw exception details and chains. Verify subprocess tests confirm default log format, severity, nonzero exit status, and absence of sensitive marker values.
- [x] 7.3 Use Rich for console output while preserving literal sample JSON; verify long strings and markup-like text round-trip through JSON parsing, document the logging behavior, and run the full 84-test suite and Ruff checks.
- [x] 7.4 Commit every `BATCH_COMMIT_ITEMS` inserted or updated posts, default 10, and on completion or errors including Ctrl-C. Verify a second connection sees each completed batch and the final remainder, failures preserve pending writes after reopening SQLite, and skips stay silent.
- [x] 7.5 Replace the ID-only helper with `post_info` returning a frozen `PostInfo` dataclass containing the validated ID and parsed aware publication date. Include that date in printed progress, preserve original API data and NULL dates, and test offsets, UTC suffixes, malformed timestamps, and missing dates.

## Verification notes

- Project dependencies were installed with uv and `uv sync --locked` passed.
- Automated collection tests use simulated Graph responses and temporary SQLite databases; they do not access the user's keyring or Facebook.
- Ruff checks and the Nikola build passed. Documentation SQL examples were exercised against a temporary database, and the current category mapping was read successfully from `conf.py`.
- The user registered the Page token in Windows Credential Manager. Live verification confirmed the configured Page identity and retrieved a sample with 37 fields; Facebook omitted publisher attribution for that sample and did not expose field-discovery metadata.
- Live field probing reproduced generic code 100 for `allowed_advertising_objectives`, code 200 for an optional-field group, and code 12 for deprecated `caption`. Handling now isolates these fields only after verifying core post access when the error is ambiguous. Regression tests cover both successful probes and fatal access failures.
- All 67 automated tests and Ruff checks passed after the correction. Strict OpenSpec validation passed.
- Collection from `2026-11-01` inserted five posts. Repeating the range skipped all five with every stored row value unchanged; `latest` skipped the single post on the latest local day. A forced `2026-11-05` collection updated one post while retaining local metadata.
- Read-only before/after comparisons confirmed no duplicate IDs, agreement between extracted columns and stored JSON, unchanged local metadata, and unchanged unrelated schema objects and legacy table contents. Tasks 5.2 and 5.3 are complete. Unavailable optional fields remain reported; exhaustive API field coverage is not guaranteed when discovery metadata is absent.
- A subsequent read-only identity check returned code 190/subcode 463, confirming token expiration. Diagnostics now preserve the numeric subcode and explain how to replace the token without exposing API error bodies. New collection requests require a renewed Page token; no database changes were made during this check.
- After long-lived setup, the saved credential was initially a User token. Using its existing Page authorization, the matching Sin Dioses Page token was obtained, verified, and stored in the OS keyring without displaying it. Live `/debug_token` verification returned type PAGE, the expected Page/app IDs, `is_valid=true`, `expires_at=0`, and the separate data-access deadline above. The CLI now enforces these distinctions and never claims revocation or future reauthorization can be prevented.
