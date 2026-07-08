# delivery Specification

## Purpose
TBD - created by archiving change stdout-only-delivery. Update Purpose after archive.
## Requirements
### Requirement: Stdout-only delivery

The local skill MUST emit digests and alerts exclusively to stdout via `scripts/print.js`. The script MUST accept a `--text <string>` argument or a `--file <path>` argument and write the supplied content to stdout. No other delivery channel (push notification, email, queue, webhook) is part of the contract.

#### Scenario: Deliver text to stdout

- **WHEN** an agent runs `node scripts/print.js --text "hello"`
- **THEN** the script writes `hello` to stdout and exits with status 0

#### Scenario: Deliver file contents to stdout

- **WHEN** an agent runs `node scripts/print.js --file /path/to/digest.txt`
- **THEN** the script writes the file's UTF-8 contents to stdout and exits with status 0

#### Scenario: Missing required arguments

- **WHEN** an agent runs `node scripts/print.js` with neither `--text` nor `--file`
- **THEN** the script writes an error message to stderr and exits with non-zero status

### Requirement: No config dependency

The delivery script MUST NOT read `~/.follow-the-money/config.json` to determine its behavior. Delivery behavior is fixed at stdout and does not depend on user configuration. The `delivery` block in user config is no longer required and is ignored if present.

#### Scenario: Run with no config file

- **WHEN** `~/.follow-the-money/config.json` does not exist
- **THEN** `node scripts/print.js --text "x"` still writes `x` to stdout and exits with status 0

#### Scenario: Run with stale config containing delivery.method=telegram

- **WHEN** `~/.follow-the-money/config.json` contains `{ "delivery": { "method": "telegram" } }`
- **THEN** `node scripts/print.js --text "x"` still writes `x` to stdout (the `delivery` block is ignored; no Telegram API call is made)

### Requirement: No outbound network calls

The delivery script MUST NOT make any outbound HTTP or network requests. Stdout delivery is purely local and operates offline. No secrets, API keys, or user data leave the machine through the delivery script.

#### Scenario: Run with no network connectivity

- **WHEN** the machine has no internet access
- **THEN** `node scripts/print.js --text "x"` still writes `x` to stdout and exits with status 0

#### Scenario: Verify no fetch calls in source

- **WHEN** the script source is inspected
- **THEN** it contains no calls to `fetch`, no `http`/`https` module imports, and no references to Telegram or Resend API endpoints

### Requirement: No dotenv loading

The delivery script MUST NOT load or depend on `dotenv`. No `.env` file is required for delivery. The `dotenv` package MUST NOT appear in the project's runtime dependencies.

#### Scenario: Run without any .env file

- **WHEN** no `.env` file exists anywhere on the filesystem
- **THEN** `node scripts/print.js --text "x"` still writes `x` to stdout and exits with status 0

#### Scenario: Verify no dotenv import

- **WHEN** the script source is inspected
- **THEN** it contains no `import ... from 'dotenv'` and no equivalent `require('dotenv')`

### Requirement: Local file read failure is surfaced, not retried

When `--file` points to a non-existent or unreadable path, the script MUST write the error message to stderr and exit with non-zero status. The script MUST NOT retry, back off, or fall back to a different path.

#### Scenario: File does not exist

- **WHEN** `node scripts/print.js --file /missing/path` is run and the file does not exist
- **THEN** the script writes an error to stderr including the path and exits with non-zero status

#### Scenario: File read permission denied

- **WHEN** `--file` points to a path the process cannot read
- **THEN** the script writes the underlying error to stderr and exits with non-zero status

