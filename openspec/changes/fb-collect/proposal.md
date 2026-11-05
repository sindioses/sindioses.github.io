# Proposal

## Why

Sin Dioses needs to collect Facebook posts in a local SQLite database for later querying and processing. Authorized API tests returned `admin_creator` for some posts but omitted it for a post confirmed as published by Iván Gonzáles Mairena, so the agreed filter matches text rather than automatically identifying the publisher.

## What Changes

- Add a standalone script to read the Page's posts through Graph API using an authorized credential from Sin Dioses App.
- Store the Page access token in the operating system's keyring through hidden interactive input, without credential files or command arguments containing secrets.
- Automatically select posts whose `message` contains either `Iván Gonzáles Mairena` or `[Godless Freeman]`, using case-insensitive substring matching with OR semantics. Allow users to configure other expressions.
- Store only matching posts in SQLite, with `id` as the primary key and columns named `message`, `created_time`, `permalink_url`, and `raw_json`. The JSON column preserves the entire returned post object, including additional and nested fields.
- Support pagination, repeated collection without duplicates, and error diagnostics that do not expose credentials.
- Document setup, sample retrieval, collection, and queries against the stored JSON.

## Capabilities

### New Capabilities

- `facebook-post-collection`: local credentials, authorized and paginated post retrieval, text filtering, and temporary SQLite storage.

### Modified Capabilities

None; there are currently no main specifications.

## Impact

Add `fb_collect.py`, focused tests, and usage documentation. Follow the PEP 723 script metadata precedent in `checkoutput.py`, declaring `keyring` as a script dependency and using standard libraries for HTTP, JSON, and SQLite. Keep temporary data outside paths published by Nikola. Editorial content, templates, and deployment remain unchanged. Facebook password authentication, inferred publisher identity, downloading linked articles, collecting comments or media, and publishing to the website are outside the scope of this change.
