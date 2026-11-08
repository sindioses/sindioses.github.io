# Proposal

## Why

Sin Dioses needs to ingest all API-accessible Facebook Page posts into its existing local SQLite database for later querying, classification, and possible website publication. Date-bounded ingestion and explicit replacement control let users extend the archive without silently overwriting stored messages.

## What Changes

- Add a standalone Python CLI built with Cyclopts and authorized through Sin Dioses App, storing the Page token in the operating system's secure keyring through hidden interactive input.
- Validate Page identity, app, token validity, absence of scheduled token expiry, and the separate data-access deadline before saving credentials or querying posts. Provide a read-only credential check and warn before data access expires; do not promise irrevocable access or automatic renewal.
- Provide `collect INITIAL_DATE [FINAL_DATE] [--force]`. Delegate date conversion to Cyclopts, documenting `YYYY-MM-DD` for dates, and accept the literal `latest` for the mandatory initial argument. Resolve `latest` from the most recent stored post for the selected Page. Default the final bound to the current timestamp captured when ingestion starts.
- Ingest every returned post in the requested period without filtering by content, signature, or publisher, including posts without a message field.
- Retrieve the full post structure available to the API version and granted permissions, including returned attachment metadata and original media URIs, rather than restricting retrieval to the extracted SQLite columns. Do not fetch referenced images or files. Attempt to identify the poster through API attribution and preserve returned identity details.
- Preserve existing posts by ID unless `--force` is supplied. Forced updates refresh Facebook fields and the original JSON while preserving local author, category, and slug metadata.
- Use a new `posts` table in the existing `../sindioses.db`, preserving legacy tables and views. Store `id`, `message`, `created_time`, `permalink_url`, `raw_json`, and nullable `author`, `category`, and `slug`. Initialize local metadata to NULL. Preserve the complete retrieved post structure in `raw_json`. Future article generation stores the Nikola slug, also used as the generated `.rst` filename stem.
- Keep category metadata aligned with Nikola's configured categories for future reStructuredText conversion. Support pagination, sample retrieval, safe diagnostics, and documented date boundaries and resume limitations.

## Capabilities

### New Capabilities

- `facebook-post-collection`: secure local credentials, date-bounded and paginated Page ingestion, explicit replacement control, and SQLite storage with category metadata.

### Modified Capabilities

None; there are currently no main specifications.

## Impact

Add `fb_posts.py`, focused tests, and usage documentation. Declare Cyclopts, keyring, Loguru, Rich, and Windows timezone data in `pyproject.toml` and update `uv.lock` using uv. Run directly with `uv run fb_posts.py`; use standard libraries for HTTP, JSON, dates, and SQLite. Keep Nikola's published sources unchanged. Resolve `../sindioses.db` from the repository root and back up the shared database before adding `posts`.

Content filtering, automatic classification, unsupported guesses about poster identity, Facebook password authentication, linked-article or media downloads, comment collection, reStructuredText conversion, and website publication are out of scope. All planning artifacts and updates remain in English.
