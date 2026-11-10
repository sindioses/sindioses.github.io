# Design

## Context

See proposal.md for motivation. `docs/fb-collect.md` is tracked by both Fossil and Git. Fossil's checkout root is the repository's parent, so the stored documentation path is `gen/docs/fb-collect.md`; CLI paths must be resolved from the actual working directory.

Inspection on 2026-11-09 found commands `credential set`, `credential check`, `sample`, `collect`, and `gen`. Collection commits every ten writes and on finalization, including errors and Ctrl-C. The database uses a TIMESTAMP column and datetime converters, and explicit database overrides must already exist. `collect` and `gen` expose `--log-level`/`-L`; `LOGURU_LEVEL` overrides the selected CLI level through `LogLevelName.reset_logger`.

`gen` selects non-NULL message/category/slug/author rows with messages longer than 2,000 characters. Its optional cut date is exclusive and slug matching is partial. Category values are looked up through legacy `secciones.idseccion` mappings with nonempty `prefijo`, and generated metadata uses `nombreseccion`. Outputs are section-specific `.rst` files under `posts/`; optional attachment images are downloaded under `images/`. Existing articles and images have separate overwrite switches. The command does not publish the website.

The collection specification describes article generation as future work and category display names as the editorial convention. Those statements differ from the current generation implementation. This documentation change will describe the implemented commands and their database prerequisites explicitly without changing the specification, assigning categories, or claiming those representations are interchangeable. The old guide's assertions about globally sanitized logging and database-override creation also need checking against current code rather than repetition.

## Goals / Non-Goals

Goals: provide one Spanish operator guide, distinguish collection from generation side effects, make token recovery executable by a human, and preserve file history in both VCS checkouts.

Non-goals: exercising credentials, changing token policy or application permissions, repairing runtime/specification differences, generating files, migrating SQLite, or publishing content. Planning artifacts remain English; the operator guide remains Spanish. No delta specification is required for documentation-only work.

## Decisions

### Use current implementation as the documentation baseline

Structure the guide around installation, credentials and recovery, samples, collection, editorial prerequisites, generation, storage, and troubleshooting. Confirm command spelling and examples with read-only `--help` invocations, then cross-check effects against `fb_posts.py`, `const.py`, `collection.py`, `storage.py`, and token modules. Do not retain the old collection-only introduction or extrapolate capabilities from historical proposals. Document limitations such as existing output-directory prerequisites where the implementation requires them.

### Describe recovery as obtaining fresh authorization

Provide a numbered procedure with expected outcomes:

1. Recognize code 190, subcode 463, revoked permission, or a separate data-access deadline. Explain why re-saving an expired value cannot renew it.
2. Sign into the Facebook account authorized for Sin Dioses; select Sin Dioses App, app ID `1603408681013331`, in Graph API Explorer.
3. Obtain fresh User authorization for Page `115097879246` with `pages_show_list`, `pages_read_engagement`, and `pages_read_user_content`; explain checking Page selection when it is absent from results.
4. Extend the valid User token using Meta's supported tools. Explain the User-to-Page distinction and how to locate the current extension procedure if a UI control is unavailable. Never suggest exchanging an already expired token.
5. Use the extended User token for `/me/accounts?fields=id,name,access_token,tasks`, and select only the Sin Dioses Page entry's token.
6. Inspect the resulting token in Meta's debugger. Check PAGE type, Page and app identity, validity, granted permissions, no scheduled token expiry, and the separate data-access expiration. Explain why no scheduled expiry does not guarantee permanent access.
7. Store the new Page token with `uv run fb_posts.py credential set` through hidden input. Explain that validation precedes replacement and failed validation leaves the old entry intact.
8. Run `uv run fb_posts.py credential check`, inspect its expected non-secret result, and rerun the original explicit collection interval. Existing IDs are skipped unless forced; `latest` cannot prove an interrupted interval is complete.

Use placeholders only. Keep tokens and app secrets out of terminal arguments, screenshots, logs, tracked files, and shell history. Prefer the existing browser-tool workflow to introducing a helper that stores secrets. Include troubleshooting for User tokens, incorrect Page/app, missing permissions, scheduled expiry, and expired data access. No automatic-renewal or permanent-validity promise.

Official references to verify during implementation: [long-lived tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived/), [token debugging](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/debugging-and-error-handling/), [Pages setup](https://developers.facebook.com/docs/pages-api/getting-started/), [Explorer](https://developers.facebook.com/tools/explorer/), and [Debugger](https://developers.facebook.com/tools/debug/accesstoken/). The documentation endpoints were inaccessible or returned HTTP 429 during planning; exact current UI controls are not verified. Recheck these specific sources during implementation and disclose remaining access limitations instead of inventing controls.

### Record the rename in both version-control systems

Before moving, inspect scoped Fossil/Git status, confirm the source is tracked and destination absent, and retain unrelated edits. When both track the source, use `git mv -- docs/fb-collect.md docs/fb_posts.md`, then `fossil mv --soft docs/fb-collect.md docs/fb_posts.md` from the Git repository root. The latter records the already-completed move without moving the file again. If Git does not track the source, use a single filesystem move followed by Fossil's soft rename. If Fossil's source is unexpectedly untracked, report the actual state before claiming a historical rename; do not manufacture a source entry.

Update current links found by scoped searches. Keep archived proposals as historical records. Verify Fossil reports the intended rename, the new path is tracked and not an extra, and neither documentation path is missing. Verify Git's rename status separately. Do not commit either repository.

## Risks / Trade-offs

- Meta UI and token policy can change. Mitigation: use official references, verification checkpoints, and explicit uncertainty about inaccessible pages.
- Generation modifies article and image files. Mitigation: separate its effects from collection and validate examples using help/source inspection only.
- Existing specification and implementation differ. Mitigation: document concrete current behavior and flag discrepancies without expanding into a runtime or specification rewrite.
- Dual VCS roots can cause double moves or unrelated staging. Mitigation: use one physical rename, one Fossil soft rename, scoped status checks, and no broad add/reset commands.

## Migration Plan

Rename the guide, refresh its content, and update current references. Verify the documentation and VCS state before reporting completion. If rollback is needed, reverse the scoped rename in Git and record the reverse move with Fossil `mv --soft`, preserving any intervening content edits and unrelated working changes.
