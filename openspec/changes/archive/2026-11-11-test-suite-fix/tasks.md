# Tasks

Restarted against Fossil check-in `bcbd67de90ea2abd9e7c628e99ffb39947171c76`. Production changes require express operator authorization. The operator has since authorized only the shared logging option with CLI → LOGURU_LEVEL → INFO precedence and command-start initialization; the operator has now separately approved and applied the minimal exception-sanitization patch. Each checkbox is scoped to at most two hours. Read and apply `python-implementation-expert` and its applicable references before implementing any test, fixture, double, or Python correction.

## 1. Pytest development tooling

- [x] 1.1 Add `pytest>=9.0` with `uv add --dev --upgrade-package pytest "pytest>=9.0"`, selecting the latest compatible stable release and updating `uv.lock`; verify `uv sync --locked` and `uv run pytest --version` succeed and pytest is declared only in the development group, not runtime dependencies.
- [x] 1.2 Configure native TOML under `[tool.pytest]` in `pyproject.toml` with `minversion = "9.0"`, `testpaths = ["tests"]`, a TOML array registering `unit`, `boundary`, and `integration`, and boolean `strict_markers = true`; verify there is no legacy INI-options table, and `uv run pytest --no-cov --collect-only` reads the project configuration, discovers the owned suite, and excludes vendored tests after the coverage plugin is installed.
- [x] 1.3 Change `just test` to run unfiltered `uv run pytest` and replace the unittest invocation in `docs/fb_posts.md`; verify `just --dry-run test` and the guide show the same canonical command.
- [x] 1.4 Add the latest compatible stable pytest-cov as a development dependency and lock a coverage.py version supporting subprocess coverage. Configure native TOML with the complete `fb_posts.py` / `fb_posts_lib/` source inventory, subprocess measurement, missing-line reporting, `fail_under = 85`, and no default line-exclusion patterns; verify resolved configuration, denominator completeness, and a visible initial full-suite coverage report, recording any initial threshold failure.
- [x] 1.5 Document the mandatory 85% minimum, desired 90% goal, fixed measurement scope, individual operator-confirmation requirement for every exclusion, and `--no-cov` for focused tier runs in the Spanish guide; verify the default commands retain the full-suite coverage gate.

## 2. Shared fixtures and pure behavior coverage

- [x] 2.1 Replace unittest setup/base classes and nested helpers with typed pytest fixtures and protocol-compatible doubles in a support module; verify migrated consumers run without monkeypatching, real network access, native keyring access, or the shared database.
- [x] 2.2 Migrate date, post-validation, response-decoding, and sanitization cases from `test_fb_posts_unit.py` into focused, parametrized pure tests; verify retained project rules pass under `uv run pytest --no-cov -m unit` and replace the timezone-key check with an observable application result.
- [x] 2.3 Migrate token metadata cases from `test_fb_posts_token_status.py` to typed pytest tests, keeping independent cases for missing/invalid metadata, wrong identity/app/type, expiry, and access deadlines; verify the migrated pure cases pass without I/O.
- [x] 2.4 Record a concise case mapping in this change's design document as each module is migrated, identifying retained, merged, replaced, and removed cases with their application contract or removal reason; verify every original test case is accounted for by the end of migration.

## 3. Injected-boundary coverage

- [x] 3.1 Migrate credential-store workflows and `test_fb_posts_http.py` using injected typed doubles; verify our credential policies, headers, timeout choice, host rejection, redirects, and safe error translation pass with `uv run pytest --no-cov -m boundary`.
- [x] 3.2 Migrate `test_fb_posts_graph.py`, replacing inherited logging setup with fixtures and splitting oversized modules if needed; verify field discovery, fallback, error isolation, core-access probes, publisher lookup, fixed pagination bounds, and fatal failures remain covered and pass.
- [x] 3.3 Document the three marker selections and their offline boundaries in Spanish in `docs/fb_posts.md`; verify each documented selection collects the intended tier and the default command still selects all tiers.

## 4. Persistence and collection integration coverage

- [x] 4.1 Migrate `test_fb_posts_storage.py` to temporary SQLite fixtures, retaining named-row behavior and correcting tuple comparisons in tests; verify persistence, NULL/empty messages, backups, incompatible schemas, and latest-date selection pass without accessing the real sibling database.
- [x] 4.2 Remove the direct SQLite CHECK enforcement test and replace any library-only assertions with project-entry-point contract checks; verify schema compatibility and our response/persistence validation remain covered, and record the removal in the case mapping.
- [x] 4.3 Migrate collection persistence/count tests, preserve listing timestamps in `PageSource`, and correct row assertions; verify batch commits, normal/error/interrupt persistence, skips, counts, and aware publication-date output pass with local temporary databases.
- [x] 4.4 Preserve regressions for message retention on forced refresh, replacement with `--force -M`, long/short aliases, no update with `-M` alone, metadata preservation, and insertion of new IDs; verify all retained scenarios pass without weakening the current message policy.
- [x] 4.5 Replace Cyclopts converter-only tests with focused application CLI contract tests for configured arguments, aliases, defaults, and rejected invocation before side effects; verify the selected integration cases pass without testing the library's conversion algorithm.

## 5. Existing diagnostics contracts and approval boundaries

- [x] 5.1 Apply the expressly authorized logging amendment: shared `LogLevelOption` with `env_var="LOGURU_LEVEL"`, INFO defaults, and first-instruction `reset_logger()` in all five commands. Remove the helper's environment lookup. Verify our registered command configuration and application of the resolved level; remove import-only initialization and library severity-filter expectations. Keep exception sanitization outside this authorization.
- [x] 5.2 Apply the separately operator-approved sanitization patch to `main()` and retain the safe unexpected-error/nonzero-exit regressions; verify stack locations and exception type remain available while sensitive locals, raw messages, and chained details are omitted. Do not hide a failure with skips, weaker assertions, or coverage exclusions.
- [x] 5.3 Migrate expected-error and sample-JSON cases with test-owned support helpers and existing application entry points; verify safe diagnostics, exit codes, long strings, and markup-like text. Do not add injection seams to production code; report any blocking testability limitation and request authorization for a specific indispensable fix.

## 6. Future testing policy

- [x] 6.1 Verify and retain the test methodology now recorded in `context` in `openspec/config.yaml`, covering project-owned behavior rather than standard-library or third-party functionality, the Python implementation skill across tests/fixtures/doubles, the mandatory 85% minimum and desired 90% goal, and explicit operator confirmation for every completely impractical-to-test exclusion; verify YAML parses and OpenSpec instructions expose the policies.
- [x] 6.2 Replace the obsolete no-test-suite statement in OpenSpec context with `just test` / `uv run pytest`, preserving other guidance and existing working-tree edits; verify the config and Spanish guide describe the same runner and suite boundaries.

## 7. Full-suite acceptance

- [x] 7.1 Review all migrated tests and support code against `python-implementation-expert`: typed signatures, deterministic single-scenario cases, parametrization, explicit injection, tier separation, permitted assertion operators, no helpers/constants/classes in test modules, no monkeypatching, and file-size constraints. Verify the case mapping accounts for the original seven modules and all 101 baseline cases, without requiring an unchanged final count.
- [x] 7.2 Run `ruff check` on the entire test suite only and resolve every issue found in that scope; verify the command exits successfully and the diff contains no unrelated legacy cleanup.
- [x] 7.3 Run `ruff format` on the entire test suite only, then `ruff format --check` and `ruff check` on the same test paths; verify both checks pass.
- [x] 7.4 Review the complete coverage report and add meaningful tests for uncovered application behavior, including subprocess-only paths, to reach at least 85% aggregate line coverage and pursue 90%; verify no source-inventory reduction or excluded section inflated the result. For any completely impractical-to-test section, record exact scope, reason, attempted approaches, and coverage impact, and obtain explicit operator confirmation before applying its exclusion; otherwise leave it counted.
- [x] 7.5 Run `uv sync --locked`, each tier via `uv run pytest --no-cov -m unit`, `uv run pytest --no-cov -m boundary`, and `uv run pytest --no-cov -m integration`, then fresh unfiltered coverage runs through `uv run pytest` and `just test`; verify every collected owned test passes, aggregate coverage is at least 85%, and no skip, expected failure, deselection, or excluded failing module hides a defect. Repair test-suite defects only. For any remaining genuine application defect, obtain express operator authorization before making a specific production correction; otherwise report the blocked acceptance criteria honestly.
- [x] 7.6 Review the final diff, case mapping, dependency group/lock consistency, fixed coverage inventory, and runtime-file impact; verify only authorized files changed. Record achieved coverage, whether 90% was reached, remaining gaps if below 90%, each individually operator-confirmed exclusion or the absence of exclusions, and final test/check results plus the live Facebook/native-keyring coverage limitation. Verify application source remains identical to the Fossil baseline, except for any specifically operator-authorized correction, which must be recorded with its approval and validation.
