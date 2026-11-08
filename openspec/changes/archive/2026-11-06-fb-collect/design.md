# Design

## Context

See `proposal.md` for motivation. This Nikola repository already has standalone PEP 723 scripts and no general application test suite. User-provided Graph API v26.0 responses confirm Page `115097879246`, read permissions, and inconsistent availability of `admin_creator`. Ingestion now includes all returned posts regardless of publisher or text.

Read-only inspection of `../sindioses.db` found legacy tables such as `articulos`, `secciones`, and `migracion`, plus views, but no `posts` table. This change adds a separate table and does not repurpose legacy article records.

## Goals / Non-Goals

**Goals:** a small local ingestion tool, complete preservation of returned post objects and media URIs, best-effort identification of the poster through API attribution, predictable date ranges, safe reuse of the existing database, and explicit control over replacement.

**Non-Goals:** guess poster identity when API evidence is unavailable, download referenced images or files, filter content, classify automatically, implement browser login or an OAuth server, convert posts to reStructuredText, or publish the website. The user obtains and renews tokens through Meta's tools. Attempting to identify the poster from explicit API attribution is in scope.

## Decisions

### Script and dependencies

Add `fb_posts.py` for Python >=3.13, executed directly with `uv run fb_posts.py` from the repository root. Declare `cyclopts` and `keyring` in the project's `pyproject.toml` dependencies, plus `tzdata` with a Windows platform marker so `zoneinfo` can resolve `America/Argentina/Buenos_Aires`. Use uv to update `pyproject.toml` and `uv.lock` together and verify installation with `uv sync --locked`. Use standard libraries for HTTP, JSON, dates, and SQLite. Do not add an SDK, ORM, PEP 723 dependency block, or a separate script environment. The shared project environment includes Nikola, allowing category configuration to be read from `conf.py` without duplicating its dependencies.

Use simple functions separating CLI validation, keyring access, date resolution, transport, and persistence. Test external boundaries with substitutes and temporary databases. Cyclopts handles command dispatch, help, and built-in date conversion. Do not implement custom CLI date/datetime parsers, converters, regex checks, or redundant format validation. See [Cyclopts date conversion](https://cyclopts.readthedocs.io/en/stable/rules.html#date).

Declare Loguru and Rich as direct project dependencies as well. Use the supported `logger.warning()` method for warnings; Loguru 0.7.3 has no `logger.warn()`. Missing field metadata and unavailable optional fields use `logger.debug()` and include the post ID. Replace warning callbacks with direct Loguru calls. Configure stderr logging once at module scope, outside commands, using LOGURU_LEVEL with an INFO fallback when unset, preserving Loguru's default format with `diagnose=False` and `backtrace=False`. Expected operational failures use `logger.error()`. Decorate `main()` with `logger.catch` and a nonzero-exit handler for unexpected failures. Before they reach the decorator, preserve stack locations but replace raw exception text and suppress chained exceptions, so tokens cannot leak through local values, URLs, or exception messages. Use `from rich import print` for console messages; render sample JSON through Rich with markup, highlighting, and wrapping disabled to preserve its literal content and validity.

### CLI

- `credential set`: use `getpass` to store or explicitly replace a token under keyring service `sindioses.fb-collect`, with the Page ID as account.
- `credential check`: inspect the stored token and report scheduled token expiry and the separate data-access deadline without modifying credentials or SQLite.
- `sample --post-id ID`: print one complete post object without modifying SQLite.
- `collect INITIAL_DATE [FINAL_DATE] [--force]`: ingest a period. Annotate the mandatory initial argument as `date | Literal["latest"]` and the optional final argument as `date | None = None`, letting Cyclopts perform conversion. Document `YYYY-MM-DD` as the date format; omit the final argument to use the current timestamp.
- Retain non-secret `--page-id`, `--api-version`, and `--database PATH` options. Initial defaults are `115097879246`, `v26.0`, and the repository sibling database. The API version is grounded in the user's tested query, not a claim that it is the latest version.
- Use `collect` as the collection command and expose no content-filtering options.
- Report resolved bounds and counts of posts read, inserted, skipped, and updated. Report incomplete runs explicitly. CLI help and usage documentation remain in Spanish; OpenSpec artifacts remain in English.

Examples:

```text
uv run fb_posts.py collect 2026-01-01
uv run fb_posts.py collect 2026-01-01 2026-01-31
uv run fb_posts.py collect latest
uv run fb_posts.py collect 2026-01-01 2026-01-31 --force
```

### Date ranges and latest

Proposed boundary convention: interpret calendar dates in the site's `America/Argentina/Buenos_Aires` timezone. An initial date begins at local midnight, inclusive. An explicit final date includes that entire local day, implemented as an exclusive bound at the following midnight. Without a final date, capture the current aware timestamp once at command start and use it as the exclusive upper bound throughout pagination. Convert bounds to UTC epoch values for API `since` and `until` parameters. Keep original API timestamps in SQLite.

Let Cyclopts reject malformed or impossible CLI dates. Accept the formats its built-in `date` conversion supports instead of imposing a second syntax policy; `YYYY-MM-DD` remains the documented form. Application logic validates only reversed explicit ranges and initial bounds at or after the default final instant before any API call or database mutation. Timezone boundaries, the runtime current-timestamp default, and resolving `latest` from stored history remain application responsibilities. Stored Facebook timestamps are external data rather than CLI arguments; use standard-library ISO timestamp conversion for those values without writing a custom datetime parser.

For `latest`, inspect stored `created_time` values for the selected Page only, using the Page prefix of the composite Facebook post IDs. Compare parsed timezone-aware instants, not raw timestamp strings. Resolve the latest instant to its calendar date in the site timezone and start at midnight that day. Re-reading that day avoids treating the latest timestamp as an exclusive checkpoint; existing IDs are skipped by default. Ignore NULL timestamps; reject malformed non-NULL timestamps with a clear diagnostic. If there are no usable dates or no `posts` table, fail with instructions to supply an explicit initial date; do not infer a date from legacy tables or silently ingest all history.

An ordinary run does not update old records, and `latest` is not a completeness checkpoint: an interrupted API traversal may leave gaps before the newest stored date. Users must rerun the original explicit interval after a partial failure. Use an older explicit interval with `--force` to refresh historical content; this does not happen automatically.

### Authorized retrieval and pagination

Use the secure native keyring, Windows Credential Manager in the current environment, rejecting null, failure, and plaintext-file backends without fallback. No Facebook password or app secret is needed for queries.

Credential registration validates before overwriting the stored token. A read-only `credential check` command and every sample/collection query check `/me` and `/debug_token` using the supplied Page token. Live testing confirmed this self-inspection works for the authorized Sin Dioses Page token without an app secret. Require the configured Page, type PAGE, profile ID matching the Page, app ID `1603408681013331`, `is_valid = true`, and explicit `expires_at = 0`. Reject missing or scheduled token expiration rather than assuming an absent timestamp means no expiry. Keep token input in memory and the OS keyring only; never log introspection query URLs.

Treat `data_access_expires_at` separately. A positive future timestamp is accepted and displayed by `credential check`; warn within seven days and reject expired data access. Zero means no data-access deadline was declared. A token with no scheduled expiry can still be revoked or require later reauthorization; no automated token exchange or promise of perpetual authorization is introduced.

Verify `/me?fields=id,name` against the configured Page. Use HTTPS, a timeout, and a Bearer authorization header. Discover post IDs through `/{page-id}/posts` with the resolved time bounds, then retrieve each eligible post's full accessible structure. Discovery may request a small ID/date projection, but that projection must never be mistaken for the archived post. Skip detailed retrieval for existing IDs unless `--force` is enabled. Missing text or publisher attribution does not exclude a returned object. Comments, private inbox messages, and downloaded media remain outside scope; attachment metadata is part of the post structure.

Retain fixed bounds throughout pagination. Reconstruct requests with returned cursors to the same host, version, and endpoint, rather than following secret-bearing `paging.next` URLs. Continue through pages containing only already stored IDs. Reject repeated cursors, invalid pagination, and redirects that could expose authorization. Report selected safe error codes and explanations without dumping requests, secret-bearing URLs, headers, or complete error responses.

### Full post structure and publisher lookup

Request every readable Post field exposed by the selected API version and token rather than only the fields represented by database columns. Graph responses depend on requested fields and permissions; do not assume that omitting `fields` or using an unverified wildcard returns everything. Use node metadata to discover fields where supported, with an explicit version-aware field inventory grounded in Meta's Post reference and official SDK as a fallback. Check discovery support against the actual API during implementation. Meta's official SDK lists many more Post fields than the earlier six-field projection; see [Meta's Post model](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/post.py). The public Post reference returned HTTP 429 during planning, so no claim is made that live exhaustive field discovery has already been verified.

When metadata is absent, omit `allowed_advertising_objectives`, `caption`, `comments_mirroring_domain`, `description`, `is_app_share`, `link`, `name`, `object_id`, `source`, and `type` from the v26.0 fallback inventory. The user's live queries rejected these fields; requesting them again for each post causes repeated group splitting. This exclusion applies only to the fallback inventory. If node metadata advertises them, request them normally.

Fetch fields in bounded groups when necessary. Isolate a specifically rejected optional field and continue with other fields instead of silently reducing the archive to the original projection. Preserve all returned fields, unknown properties, and nested objects when assembling the single post object for `raw_json`. Retain attachment and subattachment information included in the retrieved post JSON, including images, files, and their URIs exactly as declared. Do not fetch media URIs, download files, traverse separate attachment resources or their pagination links, recursively traverse unrelated graph nodes, or collect comments. Full structure means readable Post fields and the nested information returned with them, not downloaded attachments, inaccessible/private data, or the entire connected Facebook graph. Do not rewrite media URIs to local paths or test their reachability.

Live API verification confirmed that an unavailable optional field can produce generic code 100 (unsupported object request) or code 200 (permissions error), while deprecated fields can produce code 12. For ambiguous codes 10, 100, or 200 during field retrieval, first verify that the same post's core fields remain readable. Only after that succeeds may the failed group be split and optional fields isolated. If the core probe fails, propagate the error. Never skip a failed core field or treat authentication, transport, or rate-limit failures as optional-field rejections.

Request `admin_creator` and available identity attributes explicitly. If it is omitted by the Page listing, attempt a direct post-node lookup with the Page token. Preserve returned IDs, names, types, and other attribution attributes in the archived object. `from` can identify the Page rather than the human publisher; signatures and mentions are not identity evidence. Missing or specifically inaccessible attribution is an expected best-effort outcome and does not prevent ingestion.

Warn safely about unavailable post fields, distinguishing limited API visibility from a complete archive. Attachment information is preserved as returned; deliberately not following media URIs or attachment pagination is outside scope, not a retrieval failure. Authentication, transport, rate-limit, malformed-response, or general ingestion failures remain errors; do not suppress them as optional-field failures. When combining responses, preserve their API values without adding guessed fields. Transport pagination URLs containing credentials must be sanitized before storage; this is the sole confidentiality exception to otherwise lossless field preservation and does not authorize rewriting declared media URIs. Sample retrieval uses the same full-structure and attribution path as ingestion.

### SQLite and replacement behavior

Table `posts`: `id TEXT PRIMARY KEY NOT NULL`, `message TEXT NULL`, `created_time TEXT NULL`, `permalink_url TEXT NULL`, `raw_json TEXT NOT NULL CHECK(json_valid(raw_json))`, `author TEXT NULL DEFAULT NULL`, `category TEXT NULL DEFAULT NULL`, `slug TEXT NULL DEFAULT NULL`. Nullable `message` preserves posts whose API object lacks text; an empty message remains an empty string. Preserve full composite IDs, original timestamp values, and semantically complete UTF-8 JSON, including unknown and nested fields. Do not store the outer listing's `data/paging` envelope or transport secrets; nested attachment structures remain part of the post archive.

Use parameterized SQL and batched transactions. Default insertion uses `ON CONFLICT(id) DO NOTHING`, preserving every field of existing rows even when Facebook returns newer content. With `--force`, use UPSERT to update only `message`, `created_time`, `permalink_url`, and `raw_json`. Always preserve `author`, `category`, and `slug`. Never use SQLite REPLACE, delete stored rows missing from results, or require `--force` for new IDs. Keep extracted API columns and JSON consistent for each inserted or updated row.

Replace the ID-only helper with `post_info(post) -> PostInfo`, a frozen dataclass containing the validated ID and an aware `created_time` parsed from the API timestamp and converted to the site timezone. Missing or NULL dates remain None; reject malformed or naive timestamps. Preserve the original timestamp string and post JSON in SQLite.

Count inserted and updated posts toward `BATCH_COMMIT_ITEMS`, default 10, across listing pages. Commit at each batch boundary and in finalization on normal completion or any exception, including Ctrl-C. After each successful write, update counts and print `Guardado post {id} ({date})`, using the parsed aware timestamp or `fecha desconocida` when missing. These progress messages can precede batch commits. Skipped rows neither print a message nor count toward the batch. Ctrl-C propagates to the CLI's exit-130 handler after pending writes are committed.

### Author metadata

Initialize `author` to NULL for every inserted post, even when the API exposes a publisher. Keep the best-effort publisher identity in `raw_json`; the separate `author` column is reserved for later editorial attribution and must not conflate the person who published a post with the article's credited author. Ingestion neither assigns nor clears `author`, including with `--force`, and never injects this local value into the archived Facebook object.

### Categories

Use `CATEGORY_DESTPATH_NAMES[DEFAULT_LANG]` from `conf.py`, where `DEFAULT_LANG` is `es`, rather than a literal `"DEFAULT_LANG"` key. Proposed representation remains the configured display name, such as `Escepticismo`, rather than destination key `escepticismo` or a legacy section ID. Consult configuration rather than maintaining a duplicate hardcoded list.

New rows start with NULL category, meaning unclassified. Ingestion neither assigns nor clears categories, including with `--force`. Keep local category metadata outside the original Facebook JSON. Classification and the decision to convert or publish are future operations, not ingestion side effects.

### Article slug metadata

Initialize `slug` to NULL on insertion. When a future article-generation workflow creates a Nikola article, it stores the article's slug here, matching the generated `.rst` filename stem without its extension or directory. For example, `slug = 'el-ateismo-ante-la-muerte'` corresponds to `el-ateismo-ante-la-muerte.rst`. Ingestion does not generate, assign, or clear slugs, including during forced refreshes. Slugs are local workflow metadata and must not be injected into `raw_json`. Slug creation and collision handling belong to the future generation workflow; no uniqueness constraint is introduced here.

### Shared database

Default to `../sindioses.db` relative to the script's repository root, independent of the working directory. In this checkout the path is `D:\MARCELO\FUENTES\WebSites\sindioses\sindioses.db`. Retain `--database PATH` overrides, which may create a new database; the default file must already exist.

Before adding `posts` to an existing database, create a SQLite-consistent backup without overwriting an existing backup. Create the table transactionally and reject incompatible existing schemas without changing them. Preserve unrelated tables, views, data, and database-wide settings. Do not reuse `articulos` or create a cache database. Cleanup must target collector rows or the new table, never delete the shared database. Keep alternative paths outside `files/`, `images/`, and `output/`.

## Risks / Trade-offs

- Facebook may omit posts or fields: preserve what it returns without claiming to archive everything visible in the UI.
- Tokens may expire or lose permissions: fail with safe diagnostics and allow replacement through `credential set`.
- Native keyring and timezone support vary by system: verify the secure backend and provide timezone data on Windows.
- A partial run can store the newest posts before older ones: preserve committed posts, report incomplete ingestion, and document rerunning the explicit interval instead of relying on `latest`.
- Default conflict skipping preserves old content intentionally: users choose `--force` when refreshing Facebook fields; local classification is always retained.
- JSON duplicates extracted fields intentionally to support SQL queries and future processing without losing returned metadata.

## Migration Plan

Introduce only the script, tests, and documentation. Validate against synthetic API responses and temporary databases with representative legacy objects, then an authorized sample and real ingestion. Back up the shared database before adding `posts`; do not migrate legacy data. Rollback may remove the new files, credential, and collector's table or rows at the user's discretion while retaining the database and unrelated objects. Do not deploy Nikola.
