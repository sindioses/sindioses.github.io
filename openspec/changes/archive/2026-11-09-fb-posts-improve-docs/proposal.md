# Proposal

## Why

The operator guide still describes a collection-only tool even though `fb_posts.py` now generates articles and optionally downloads images. Its token-expiration instructions need a complete recovery procedure, and its filename no longer matches the CLI.

## What Changes

- Rename `docs/fb-collect.md` to `docs/fb_posts.md`, preserving Fossil history and updating current documentation references.
- Refresh the Spanish guide against the current CLI and supporting modules, covering credentials, samples, collection, article generation, options, persistence, classification prerequisites, and diagnostics.
- Add a numbered recovery guide for expired, revoked, or data-access-expired tokens: obtain fresh authorization, extend a valid User token, derive the correct Page token, verify it, replace the keyring credential, check it, and resume collection safely.
- Explain expected results and troubleshooting at each step, distinguish User tokens from Page tokens, and link official Meta documentation without exposing secrets.

## Capabilities

### New Capabilities

None. This is a documentation-only change; `.openspec.yaml` declares `skip_specs: true`.

### Modified Capabilities

None. Existing runtime requirements are not changed. Observed differences between the current implementation and the collection specification will be identified in the design rather than silently changing either contract.

## Impact

Primary output: `docs/fb_posts.md`. Other changes are limited to current links and Fossil rename metadata, with Git rename metadata preserved when applicable. No new dependencies or API behavior changes.

Out of scope: runtime fixes, schema migrations, automatic token renewal, handling real credentials, generating articles during validation, deployment, VCS commits, and rewriting archived proposals.
