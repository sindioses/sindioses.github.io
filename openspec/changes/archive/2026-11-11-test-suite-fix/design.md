# Design

## Context

See `proposal.md` for motivation and scope. Read-only discovery found seven unittest modules plus `tests/fb_posts_doubles.py`. The current command runs 101 tests and reports 11 failures:

- Seven failures compare `sqlite3.Row` results directly with tuples. `open_database()` intentionally enables named row access for application callers.
- One progress-date failure uses `PageSource.pages()`, which discards `created_time` before the collector formats the listing's publication date.
- Three logging failures expose application configuration gaps. Import-time logging retains Loguru's default DEBUG sink, and `main()` does not sanitize unexpected exception details as required by the existing specification.

`pytest` is not declared in `pyproject.toml`; `just test` and the Spanish guide invoke unittest. OpenSpec context incorrectly states that no project test suite exists. Tests also contain unittest setup methods, nested helper classes, repeated loops, and direct library checks that do not meet the Python implementation skill's testing constraints.

The existing `facebook-post-collection` specification already requires safe diagnostics, preserved committed writes, and publication-date progress. Tests must verify those contracts; implementing production corrections requires separate express operator authorization. Its historical forced-refresh wording predates the explicit editorial-message preservation request; retain current `--overwrite-message` semantics and do not revert that authorized behavior or broaden this change into spec synchronization.

## Goals / Non-Goals

**Goals:** Review the entire owned suite under `python-implementation-expert`, retain meaningful regression protection, make the default run deterministic and passing, and provide separate execution of pure, injected-double, and local integration tests.

**Non-Goals:** A test-count target, dependency conformance coverage, a general testing framework, live-service credentials, or a new mandate to add coverage for every legacy script and bundled plugin. The full suite means all repository-owned Python tests collected under `tests/`; vendored library suites remain excluded.

## Decisions

### Use pytest as a development dependency

Run `uv add --dev --upgrade-package pytest "pytest>=9.0"` during implementation, selecting the latest stable release compatible with the project and recording it in `[dependency-groups].dev` and `uv.lock`. Keep the declared lower bound at `pytest>=9.0`; do not select prereleases or silently fall back below 9.0.

Configure native TOML settings under `[tool.pytest]` in the existing `pyproject.toml`, as supported since pytest 9.0. Do not use the legacy `[tool.pytest.ini_options]` table or INI-style string encodings of arrays and booleans:

```toml
[tool.pytest]
minversion = "9.0"
testpaths = ["tests"]
strict_markers = true
addopts = ["--cov", "--cov-config=pyproject.toml", "--cov-report=term-missing"]
markers = [
    "unit: pure computation without runtime I/O",
    "boundary: application contracts with injected in-memory doubles",
    "integration: application integration with temporary local infrastructure",
]
```

Keep a single canonical invocation, `uv run pytest`, and have `just test` execute it without a default marker filter. Provide documented `-m` selections for individual tiers. Verify the resolved version with `uv run pytest --version` and the active project configuration during collection.

Keeping unittest classes and merely changing the runner would preserve the current structural problems. A separate pytest configuration file or test-only runtime dependency would add unnecessary configuration or deployment requirements. Resolve the latest compatible stable pytest release during implementation rather than freezing a possibly stale exact version in this proposal. The [pytest configuration reference](https://docs.pytest.org/en/stable/reference/customize.html#pyproject-toml) documents `[tool.pytest]` and its native TOML types.

### Enforce meaningful coverage without artificial exclusions

Add the latest compatible stable `pytest-cov` as a development dependency, locking a coverage.py version that supports subprocess measurement. The hard acceptance floor is 85% aggregate line coverage; the desired goal is at least 90%. A result from 85% up to 90% meets the minimum but must identify remaining gaps and explain why the desired goal was not reached. Below 85% fails the default full-suite command even when every test passes.

The coverage denominator is the complete Facebook tooling already in this suite's scope: `fb_posts.py` and every Python module under `fb_posts_lib/`, including unimported modules and subprocess-only code. Keep that source inventory fixed throughout implementation and report it with the result. Tests and support doubles are measurement infrastructure, not production code. Do not narrow the source inventory or move code outside it to raise the percentage. Any newly extracted application module remains in the denominator.

Use native coverage TOML alongside `[tool.pytest]` in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["fb_posts", "fb_posts_lib"]
patch = ["subprocess"]

[tool.coverage.report]
fail_under = 85
precision = 2
show_missing = true
exclude_lines = []
```

The empty exclusion list disables coverage.py's default line-exclusion patterns, including placeholder bodies and `pragma: no cover`. Start with no project-code omissions or additional exclusion patterns. Audit the resolved configuration and report for implicit as well as explicit exclusions. Keep coverage enabled in the default `uv run pytest` / `just test` command and collect fresh data for the full run, including CLI child processes. Validate that subprocesses inherit the correct configuration when their working directory differs. Partial tier runs may use `--no-cov` for focused checks; their percentages do not establish full-suite acceptance.

Increase coverage through meaningful tests of our own behavior, using the Python implementation skill throughout. Every exclusion of project code, whether a file omission, source-filter change, regex, pragma, or tool default, requires a concrete explanation of why testing is completely impractical and explicit operator confirmation before applying it. Convenience, platform differences alone, difficult setup, or a desire to meet either percentage do not justify an exclusion. Document each proposed exclusion's exact file/section, reason, attempted testing approaches, coverage impact, and operator decision in the change's implementation record. No exclusion is pre-approved by this proposal. Without confirmation, keep the code counted and report any unmet threshold honestly.

Do not weaken assertions, add tests that only execute lines, re-test dependencies, skip failing cases, lower the gate, or delete/restructure code solely to improve the metric. Review uncovered lines for missing success, error, validation, and boundary behavior. The final review must report the achieved coverage, whether 90% was reached, and every operator-confirmed exclusion or explicitly state there were none.

### Audit assertions by the application behavior they protect

Each retained test must identify a project-owned function, rule, or observable contract that could regress independently of its dependencies. Libraries may execute as infrastructure when a test asserts our integration or policy. They must not be the subject of a test by themselves.

| Existing module | Review and migration decision |
| --- | --- |
| `test_fb_posts_unit.py` | Retain date-bound rules, post validation, safe credentials, response validation, pagination sanitization, and redirect policy. Replace the timezone object's key check with an application-visible date result. Parametrize independent input variants. |
| `test_fb_posts_token_status.py` | Retain application token identity, app, expiry, access-deadline, and safe registration policies. Inject credential and Graph doubles, keeping each parameterized case independent. |
| `test_fb_posts_graph.py` | Retain field discovery/fallback, optional-error isolation, fatal access errors, publisher lookup, and bounded pagination. Replace the unittest logging base class with explicit fixtures and typed support doubles. |
| `test_fb_posts_http.py` | Retain our authentication placement, timeout choice, error translation, host restrictions, and secret handling. Inject the existing HTTP boundary rather than testing urllib itself. |
| `test_fb_posts_storage.py` | Retain our persistence, refresh, metadata preservation, schema compatibility, backup, and latest-date policies against temporary databases. Remove the direct invalid-JSON INSERT test that only proves SQLite enforces a CHECK. Test our schema validator and persistence entry points instead. |
| `test_fb_posts_collection.py` | Retain skip/refresh counts, commit boundaries, failure/interrupt persistence, and emitted dates. Preserve listing timestamps in the double. Replace library date-converter checks with a small number of command-contract cases for our aliases, defaults, and validation before side effects. |
| `test_fb_posts_logging.py` | Retain our logging configuration, safe error boundary, exit codes, and literal sample JSON. Test the project's configuration function or actual CLI boundary, not bare `logger.debug()` behavior or Loguru's timestamp format. |

Normalize rows to tuples or assert named fields in tests; do not remove the application's row factory. Keep preserved-message and `-M` regressions. No meaningful behavior case may be silently removed to make the suite pass. Record a concise mapping of old cases to retained, merged, or removed coverage in the implementation review.

### Apply the Python implementation skill to all test code

Use typed pytest functions and fixtures throughout, including migrated doubles and support code. Use fixed inputs and `pytest.mark.parametrize` for independent scenarios. Test modules contain imports, fixtures, and test functions only; shared constants, classes, builders, and process-driving helpers belong in a small typed support module. Import application code to exercise it, not to borrow fixtures or derive expected values.

Pure `unit` tests perform no runtime filesystem, database, network, process, or patch operations. `boundary` tests inject protocol-compatible in-memory doubles. `integration` tests exercise our storage or CLI with temporary infrastructure. Do not use monkeypatching or mock patching. Use fixtures for cleanup and existing injection boundaries. Do not add production seams, split modules, reformat application code, or change public functions to make testing easier. If existing boundaries prevent a skill-compliant test, document the limitation and ask before changing production code. Keep test modules within the skill's size constraints.

Assertions use `==` for equality and `is` for identity. Use `pytest.raises` with a specific exception and assert its defined diagnostic when meaningful. Avoid broad catches, retries, sleeps, vague comparisons, or library formatting snapshots. Use exact expected values rather than copying an implementation into a test.

### Freeze production code and require express authorization

Restart from Fossil check-in `bcbd67de90ea2abd9e7c628e99ffb39947171c76`. The application files and original test suite were restored to that check-in after the operator clarified the scope. Session-created production extractions and tests depending on those extractions were removed. Retain approved development dependency and runner configuration while restarting the test migration against the restored application.

Only the test suite, fixtures, doubles, development dependencies, test-runner/coverage configuration, related documentation, and OpenSpec guidance may change autonomously. Application source must remain byte-for-byte identical to that Fossil baseline except for the explicitly authorized logging-option changes described below. Skill preferences for decomposition or injection do not authorize production edits. Do not format, refactor, extract, or alter application functions to meet testability or file-size preferences.

Correct invalid fixtures and stale assertions in tests. Keep real regression checks for the documented logging and confidentiality contracts. If a retained test demonstrates an application defect that cannot be resolved through legitimate test changes, record the exact failure, affected function, minimal proposed correction, and validation steps. Express operator approval is required before every production-code change, even for a genuine indispensable defect. A suspected defect, existing failure, or coverage shortfall is not authorization. Do not silently delete, weaken, skip, or mark a failing contract expected-failing to claim success.

Continue independent test work while authorization is pending. If the remaining acceptance criteria require an unapproved source change, report the concrete blocker and incomplete tasks. The prior unrestricted 92.56% result does not count as acceptance for this restarted scope.

### Authorized command logging precedence

The operator expressly authorized the shared CLI option and reset-helper change after the test-only restart. This authorization covers `fb_posts.py` command signatures, their first logging-initialization instruction, and `fb_posts_lib/const.py` applying the resolved level. It does not authorize exception sanitization or unrelated source cleanup.

Use a shared annotation:

```python
LogLevelOption = Annotated[LogLevelName, Parameter(alias="-L", env_var="LOGURU_LEVEL")]
```

All five commands (`collect`, `gen`, `sample`, `credential set`, `credential check`) declare `log_level: LogLevelOption = LogLevelName.INFO` and execute `log_level.reset_logger()` first. Cyclopts handles explicit CLI option, then environment fallback, then signature default. The helper passes `self.value` directly to `logger.add`; it must not read `LOGURU_LEVEL` again. Python calls use their explicit argument or INFO; environment resolution belongs to CLI parsing. Importing the module does not initialize logging.

Replace the import-only default-level test and severity-filter matrix with focused tests of our command configuration and error handling. Verify all registered commands expose the common option/alias, environment mapping, and INFO default. A small real-command check verifies the resolved option reaches logging before application validation without being overridden by a second environment lookup. Do not test Cyclopts enum conversion algorithms or Loguru's general severity filtering. Preserve the unrelated confidentiality regression.

The `facebook-post-collection` delta changes the previous outside-command logging contract to command-start initialization and the new precedence. Preserve every other scenario in that requirement, including confidentiality, pending separate approval for its implementation repair.

### Make the ownership policy persistent

During apply, append this guidance to the existing `context` block in `openspec/config.yaml`, preserving other instructions:

> Tests must exercise project-owned behavior and contracts. Do not add tests whose sole purpose is to verify standard-library or third-party library functionality. Dependencies may be used as infrastructure to verify our integration, configuration, validation, error handling, and observable results. Apply python-implementation-expert to the entire Python test suite, including fixtures and doubles.

Include the coverage policy in that future guidance: enforce the 85% minimum, pursue 90%, and permit exclusions only for code that is completely impractical to test, with explicit operator confirmation for each exclusion. Do not use exclusions to inflate coverage.

Also replace the obsolete no-test-suite statement with the pytest invocation. Keep the policy in `context`, so planning and implementation both receive it. Update the Spanish guide's command and tier descriptions. Make no application or config edits during this proposal workflow.

## Risks / Trade-offs

- Removing redundant tests could discard application coverage. Mitigate with the case mapping and retained contract regressions rather than a fixed count.
- Logging state and inherited environment can make results order-dependent. Mitigate with controlled subprocess environments or fixture-managed, explicitly configured sinks and cleanup.
- A mass mechanical conversion could preserve weak assertions. Mitigate by reviewing each case's ownership and tier during migration.
- A safer unexpected-error handler can accidentally discard useful stack information. Mitigate by checking both safe stack content and secret exclusion against the existing diagnostic contract.
- Local integration tests validate our use of SQLite and CLI libraries, but cannot establish live Facebook or native-keyring behavior. Keep those limitations explicit.
- A percentage can conceal weak tests or a reduced denominator. Mitigate with the fixed source inventory, missing-line review, and individual operator confirmation of every exclusion.

## Migration Plan

1. Record the current case inventory and baseline, then add the dev dependency and pytest configuration.
2. Convert support code and each test module in bounded groups, correcting test fixtures and assertions while preserving the Fossil application baseline.
3. Update `just test`, Spanish documentation, and OpenSpec context. Run Ruff checks and formatting on test code only; report production lint issues without changing source.
4. Sync with `uv sync --locked`; run all three marker selections, then fresh unfiltered coverage runs through `uv run pytest` and `just test`. All collected project tests must pass without skips or expected failures used to hide defects; aggregate line coverage must reach at least 85%, with 90% the desired goal. Review every remaining gap and obtain operator confirmation before applying any exclusion.
5. Review the coverage mapping and final diff. If rollback is needed, revert only this change's dependency, test, documentation, config, and narrowly scoped code edits, preserving pre-existing working-tree modifications. No shared database migration or deployment is involved. Any indispensable production defect correction requires express operator authorization before implementation.

Implementation references: [uv development dependencies](https://docs.astral.sh/uv/concepts/dependencies/), [pytest configuration](https://pytest.org/en/stable/reference/customize.html), [pytest-cov configuration](https://pytest-cov.readthedocs.io/en/stable/config.html), [subprocess coverage](https://pytest-cov.readthedocs.io/en/stable/subprocess-support.html), [coverage exclusions](https://coverage.readthedocs.io/en/latest/excluding.html).


## Restart implementation record

The earlier source-changing attempt was reverted to Fossil check-in `bcbd67de90ea2abd9e7c628e99ffb39947171c76` before this restart. Only the subsequent, explicitly authorized command-logging amendment changes production source. No coverage exclusions have been authorized or applied.

### Original-case accounting

`case-inventory.json` records the destination or explicit replacement rationale for every one of the 101 baseline test methods. The migration retains all application contracts. The five replaced cases are the timezone object's key, direct SQLite CHECK enforcement, two Cyclopts converter-only checks, and the import-only logging-level expectation superseded by the operator-authorized command-initialization contract. Their relevant application behavior remains covered through date results, schema/persistence contracts, and CLI argument/alias and validation-before-side-effects tests.

| Original module | Original methods | Disposition |
| --- | ---: | --- |
| `test_fb_posts_collection.py` | 15 | 13 migrated; 2 replaced |
| `test_fb_posts_graph.py` | 15 | 15 migrated; 0 replaced |
| `test_fb_posts_http.py` | 6 | 6 migrated; 0 replaced |
| `test_fb_posts_logging.py` | 4 | 3 migrated; 1 replaced |
| `test_fb_posts_storage.py` | 18 | 17 migrated; 1 replaced |
| `test_fb_posts_token_status.py` | 13 | 13 migrated; 0 replaced |
| `test_fb_posts_unit.py` | 30 | 29 migrated; 1 replaced |

Additional tests cover our article formatter and invalid Graph structures, identity mismatches, field metadata, HTTP configuration, and command validation. Parametrized scenarios explain why the collected case count differs from the original method count. Test modules contain only imports and typed test functions; shared fixtures and helpers reside in test-owned support modules. No mock patching or application test seams were introduced.

### Previously blocking application defect, now authorized for correction

Before the approved correction, `main()` allowed unexpected exceptions to reach the unsanitized `logger.catch` handler. A synthetic chained exception exposed raw messages, violating the existing confidentiality contract. The operator explicitly approved the reviewed sanitization patch, which is now applied; the original regression is retained without weakening its assertions.

`proposed-diagnostics-fix.patch` records the reviewed, subsequently approved exception-sanitization change. It does not include import-time INFO initialization, which the operator rejected in favor of command-start initialization. No new module, refactoring, injection seam, or formatting sweep is proposed. The operator supplied that separate express authorization with “Apply it.” The implementation also documents the intentional broad CLI exception boundary with a lint-only `BLE001` suppression; this is not a coverage exclusion.

### Verification before the authorized logging amendment

- pytest 9.2.0 and pytest-cov 7.1.0 are development dependencies; locked synchronization succeeds.
- Pure tier: 48 passed. Injected-boundary tier: 40 passed.
- At the pre-amendment checkpoint: 126 passed, 3 failed. Two failures concerned the superseded import-time logging expectation; the remaining failure concerns exception confidentiality.
- Aggregate line coverage: 86.44%, above the mandatory 85% minimum. No excluded lines, omitted production files, added regex exclusions, or narrowed source filters were used.
- The 90% desired goal is not yet reached. Remaining gaps are chiefly CLI orchestration/article file generation, native keyring/hidden-input adapters, and a few validation paths. These remain counted. The frozen API has no injectable dependencies for several of these paths; no application seam was added and no live keyring, real shared database, or Facebook endpoint was used.
- Ruff checks and formatting checks cover test code only. Application lint issues are outside the authorized modification scope.
- Full-suite acceptance remains incomplete pending express authorization for the concrete diagnostics correction. A passing coverage gate does not make the failing test suite acceptable.

Final restart checks: `just test` reproduces 126 passed / 3 failed and 86.44% coverage, returning exit code 1 as required for failures. The integration tier reports 38 passed / 3 failed. Ruff and formatting checks pass for all 16 test/support files. OpenSpec validation passes. The coverage JSON reports zero excluded lines; configured run/report omissions and extra exclusion patterns are empty. Production bytes were compared with Fossil for every application Python file. At that checkpoint, tasks 5.2, 5.3, and 7.5 remained incomplete. The command-logging amendment supersedes the import-default expectation; exception sanitization remains unapproved.


### Authorized logging amendment verification

- Explicit operator authorization: apply the shared Cyclopts environment fallback, CLI → LOGURU_LEVEL → INFO precedence, all-command first-instruction initialization, and matching test/proposal changes. Production edits are limited to `fb_posts.py` and `fb_posts_lib/const.py`; all other application Python files still match the Fossil baseline byte-for-byte.
- Logging-focused run: 26 passed; the only failure is the pre-existing exception-confidentiality regression. The 24 new option/invocation cases cover the five command registrations, both CLI aliases, environment/default resolution, and application of the selected level before validation.
- `just test`: 146 passed, 1 failed; aggregate line coverage 86.19%, zero excluded lines. The 85% floor passes; the desired 90% remains unreached for the previously recorded gaps. The suite correctly exits nonzero because of the outstanding confidentiality defect.
- Test lint and formatting checks pass. Three pre-existing production lint findings remain untouched: import ordering in the CLI/constant module and the CLI's unused legacy `takewhile` import. No unrelated formatting was applied.
- OpenSpec strict validation passes with the logging delta. Tasks 5.1 and 5.3 are complete. Tasks 5.2 and 7.5 remain pending separate express authorization for exception sanitization. No import-time logging setup or exception-handling changes were applied.


### Final acceptance after separately approved exception sanitization

The operator reviewed the diff and explicitly instructed “Apply it.” The approved catch-all CLI error boundary is now implemented in `fb_posts.py`. It emits only traceback locations and the exception type and exits with status 1; local values, original messages, and chained exceptions are not rendered. The existing `logger.catch` decorator remains. Documentation now describes this behavior.

Final checks:

- Focused diagnostics: 3 passed, including the unchanged confidentiality assertions.
- Unit tier: 48 passed; boundary tier: 40 passed; integration tier: 59 passed.
- Fresh full-suite invocation through `just test` / `uv run pytest`: 147 passed, exit code 0.
- Aggregate line coverage: 86.30%, zero excluded lines. The mandatory 85% floor is met. The desired 90% goal remains unmet because CLI file-generation/orchestration and native keyring/input paths remain incompletely covered; no production seam, live-service call, omission, or exclusion was added to raise coverage.
- Locked dependency sync, test Ruff checks, test formatting checks, and strict OpenSpec validation pass. Existing production import-order/unused-import lint findings remain outside the approved correction scope.
- Only `fb_posts.py` and `fb_posts_lib/const.py` differ from the Fossil production baseline, within the two express approvals. All other production Python files were checked byte-for-byte. Unrelated workspace changes were preserved.
- All 28 implementation tasks are complete. The change has not been archived or deployed. Live Facebook and native-keyring integrations were not exercised.
