# Tasks

## 1. Documentation rename and repository state

- [x] 1.1 Record scoped Git/Fossil status and confirm the tracked source and absent destination, then rename `docs/fb-collect.md` to `docs/fb_posts.md` with one physical move and `fossil mv --soft` as described in the design. Verify the new file is tracked in Fossil, the intended rename is reported, neither documentation path is missing, and unrelated changes remain intact. Preserve Git rename metadata when tracked. Estimated time: 30 minutes.
- [x] 1.2 Update current documentation links to the new filename without rewriting archived proposals. Verify each changed link resolves and a scoped search finds no stale active links outside this change's explanatory artifacts. Estimated time: 30 minutes.

## 2. Current command and storage documentation

- [x] 2.1 Refresh the Spanish introduction, installation, credential commands, sample, and collection sections against the inspected implementation. Document actual options, date bounds, skip/force behavior, batch commits, interruption recovery, progress dates, `--log-level`/`-L`, and `LOGURU_LEVEL` precedence. Verify command syntax with top-level and subcommand `--help`, and check behavior claims against source without live credentials or collection. Estimated time: 60 minutes.
- [x] 2.2 Add the existing `gen` workflow, eligibility conditions, exclusive cut date, partial slug matching, distinct overwrite switches, section/category mapping prerequisites, article/image paths, output-directory prerequisites, and generation side effects. Explain that collection does not download media while generation may, and generation does not deploy. Verify every option against `gen --help` and every selection/output claim against `SQL_POST_QUERY`, `get_section_mappings`, and the generation implementation; do not generate files. Estimated time: 60 minutes.
- [x] 2.3 Correct storage and diagnostics descriptions, including TIMESTAMP conversion, existing-database requirements for overrides, local metadata, and discrepancies between historical specifications and current generation behavior. Retain valid JSON, retention, and backup guidance. Verify against storage, logging, token validation, and generation code; do not migrate the database or promise absent behavior. Estimated time: 45 minutes.

## 3. Expired-token recovery guide

- [x] 3.1 Recheck the design's official Meta links for current token-extension and Page-token instructions. Draft numbered Spanish steps 1-6 from the design, with app/Page IDs, exact permissions, fresh User authorization, long-lived extension, `/me/accounts` selection, debugger checks, and expected results. Include UI-control alternatives only when supported by an official source, and explicitly disclose any remaining access or UI-verification limits. Verify the guide never proposes exchanging an already expired token or saving a User token as the Page credential. Estimated time: 90 minutes.
- [x] 3.2 Complete recovery steps 7-8 with hidden `credential set` input, validation-before-replacement, `credential check` success criteria, separate token/data-access expiry, and explicit-interval recovery. Add troubleshooting for code 190/463, revoked or missing permissions, wrong User/Page/app identity, scheduled expiry, and expired data access. Verify examples contain placeholders only and no secret-bearing terminal commands, and trace the walkthrough against the implemented credential checks without obtaining real tokens. Estimated time: 60 minutes.

## 4. Integrated review

- [x] 4.1 Read the entire renamed guide as an operator following setup, token recovery, collection, editorial preparation, and generation. Verify consistent Spanish, complete numbered recovery steps, working local links, source-matched command examples, and clear side effects; check `git diff --check` and strict OpenSpec validation. Record external-source limitations without claiming a live renewal test. Estimated time: 45 minutes.
- [x] 4.2 Recheck the final scoped Fossil and Git status after content edits. Verify the rename remains recorded, the new document is tracked rather than extra, no old documentation file is missing, and unrelated changes are preserved. Report the documentation path, validations, and any limitations without committing or deploying. Estimated time: 15 minutes.

## Verification notes

- Verified top-level help, credential help and set/check help, sample help, collect help, and gen help with the configured interpreter. Parsed all 15 non-help CLI examples without executing their commands.
- Reviewed the guide against current CLI, generation SQL, formatting, storage, collection, and token code. Checked the eight recovery steps, Markdown fences, local link targets, secret-marker scan, and whitespace; strict OpenSpec validation passed.
- Git records the documentation rename; Fossil records the renamed and edited document, tracks the new path, and reports no missing documentation files or unmanaged renamed document. Existing unrelated state was preserved. No commit or deployment was performed.
- Official Meta documentation returned HTTP 429 or was inaccessible on 2026-11-09. The guide discloses that current UI labels and a live renewal were not verified. No credentials were accessed, no collection or generation command was executed, and SQLite was not changed.
