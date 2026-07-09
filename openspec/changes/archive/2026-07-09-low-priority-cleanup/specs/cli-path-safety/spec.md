## WHY

`scripts/print.js --file <path>` reads an arbitrary filesystem path with no validation, allowing reads outside the project (e.g. `--file /etc/passwd`). As a CLI it should at least block path traversal / escapes.

## WHAT

Validate the `--file` argument so it resolves inside the repo root; reject traversal and absolute escapes.

## ADDED Requirements

### Requirement: print.js rejects file paths escaping the repo root
The `print.js` `--file` resolver SHALL reject any path that, after resolution, lies outside the repository root.

#### Scenario: in-repo file allowed
- **WHEN** `--file digest.txt` is passed and `digest.txt` resolves inside the repo root
- **THEN** the file content is read and written to stdout

#### Scenario: traversal blocked
- **WHEN** `--file ../../etc/passwd` is passed
- **THEN** the process prints an error and exits with a non-zero code, reading nothing

#### Scenario: absolute escape blocked
- **WHEN** `--file /etc/passwd` is passed
- **THEN** the process prints an error and exits with a non-zero code
