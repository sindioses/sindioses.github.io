## MODIFIED Requirements

### Requirement: Structured diagnostics and literal console output
Each command MUST initialize Loguru before other command work, using its default format. Warnings MUST use `logger.warning()`, expected failures MUST use `logger.error()`, and `main()` MUST use `logger.catch` for unexpected failures with nonzero exit status. Logs MUST omit sensitive locals, original exception messages, and chained errors. Console output MUST use Rich while preserving literal, valid sample JSON including long strings. Dependencies MUST be declared in the project.

#### Scenario: Stored post progress
- **WHEN** a post is inserted or updated
- **THEN** the collector prints `Guardado post {id} ({date})` after writing the row, including its aware publication timestamp or `fecha desconocida` when missing
- **AND** skipped posts produce no progress message

#### Scenario: Batch persistence
- **WHEN** `BATCH_COMMIT_ITEMS` posts have been inserted or updated, default 10
- **THEN** the collector commits pending writes, counting across listing pages and excluding skips
- **AND** normal completion or any error also commits the remaining completed writes

#### Scenario: Operator interrupts collection
- **WHEN** Ctrl-C interrupts processing of the current result page
- **THEN** all previously stored posts, including those from the current page, remain committed and included in the counts before interruption propagates
- **AND** the CLI exits with status 130

#### Scenario: Field diagnostics do not clutter operator output
- **WHEN** field metadata is missing or an optional field is unavailable
- **THEN** the collector logs the diagnostic through `logger.debug()` with the post ID
- **AND** the stderr sink uses the explicit command-line level when supplied, otherwise `LOGURU_LEVEL` when set, otherwise INFO, hiding those diagnostics by default

#### Scenario: Expected operational error
- **WHEN** an API or credential failure produces a safe diagnostic
- **THEN** it is logged at ERROR level without a traceback and the CLI exits nonzero

#### Scenario: Unexpected failure with sensitive context
- **WHEN** an internal exception contains sensitive locals, a raw message, or a chained exception
- **THEN** the CLI logs an exception stack without those values and exits nonzero

#### Scenario: Sample contains markup-like text
- **WHEN** a sample contains literal Rich-like markup or a long message string
- **THEN** console output remains valid JSON with the original string content

#### Scenario: Shared logging options across commands
- **WHEN** the operator invokes `collect`, `gen`, `sample`, `credential set`, or `credential check`
- **THEN** the command accepts `--log-level` and `-L`, and initializes logging before validation or external access
- **AND** importing the module alone does not need to configure logging

#### Scenario: Explicit level overrides environment
- **WHEN** `LOGURU_LEVEL` is WARNING and the command explicitly receives `-L DEBUG`
- **THEN** the command uses DEBUG

#### Scenario: Environment supplies omitted option
- **WHEN** no level option is supplied and `LOGURU_LEVEL` is WARNING
- **THEN** the command uses WARNING

#### Scenario: Default level without either override
- **WHEN** neither a level option nor `LOGURU_LEVEL` is supplied
- **THEN** the command uses INFO
