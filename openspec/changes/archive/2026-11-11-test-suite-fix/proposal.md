# Proposal

## Why

The repository's 101 Python tests currently report 11 failures, and the suite mixes application contracts with checks of dependency behavior. A complete pytest migration will provide a passing, maintainable suite whose assertions protect Sin Dioses code and follow `python-implementation-expert` throughout.

## What Changes

- Add `pytest>=9.0` to the uv `dev` dependency group, resolve the latest compatible stable release in `uv.lock`, and configure native TOML under `[tool.pytest]`, keeping pytest outside runtime dependencies.
- Add pytest-cov as a development dependency. Require at least 85% aggregate line coverage for the Facebook tooling, pursue 90%, and require operator confirmation for every exclusion of project code, permitted only when testing it is completely impractical.
- Migrate and review every repository-owned test, fixture, and double under `tests/`, using typed pytest functions, parametrization, explicit dependency injection, and independently runnable testing tiers.
- Correct stale assertions and fixtures, remove tests that only exercise standard-library or third-party functionality, and retain meaningful application integration coverage.
- Limit implementation to tests, fixtures, doubles, test dependencies/tooling, documentation, and OpenSpec configuration, plus the operator-authorized logging and exception-sanitization changes below. Other production code remains frozen at Fossil check-in `bcbd67de90ea2abd9e7c628e99ffb39947171c76`.
- Give all five commands the shared `LogLevelOption` annotation with `Parameter(alias="-L", env_var="LOGURU_LEVEL")` and an INFO default. Each command calls `log_level.reset_logger()` first. Cyclopts resolves explicit CLI option, then `LOGURU_LEVEL`, then INFO; the reset helper applies that resolved level without reading the environment. Do not configure logging on module import or re-test library severity filtering.
- If a genuine production defect prevents completion and cannot be resolved through valid test corrections, document a minimal proposed fix and request express operator authorization before changing any production code. This includes refactoring, formatting, and adding test seams. Do not weaken contracts to conceal defects.
- Apply the separately approved exception-sanitization patch in `main()`: preserve file, line, function, exception type, and exit code 1 while omitting local variables, raw messages, and chained exceptions. Keep the existing `logger.catch` decorator.
- Make `just test` run the complete pytest suite and update the Spanish usage guide and inaccurate test guidance.
- Add an enduring policy to `openspec/config.yaml` stating that tests must exercise project-owned behavior rather than re-test libraries. Apply the Python implementation skill to the entire suite.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `facebook-post-collection`: initialize logging at the start of every command and use explicit CLI option → `LOGURU_LEVEL` → INFO precedence. Existing confidentiality and nonzero-exit contracts remain unchanged; the operator has separately authorized the minimal exception-sanitization fix.

## Impact

Affected paths include `pyproject.toml`, `uv.lock`, `justfile`, `tests/`, `docs/fb_posts.md`, `openspec/config.yaml`, and the authorized logging changes in `fb_posts.py` and `fb_posts_lib/const.py`. Other production changes require separate express authorization. Existing editorial-message preservation and `--overwrite-message` behavior must remain covered. Dependency versions are resolved with uv during implementation.

Out of scope: new product features, site content or theme changes, a new CI system, dependency-library conformance suites, vendored Reveal tests, live Facebook/keyring testing, shared database changes, deployment, and any unapproved production-code change, including refactoring or formatting. No unchanged test-count target is introduced.
