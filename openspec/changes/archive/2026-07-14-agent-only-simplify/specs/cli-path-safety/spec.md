# cli-path-safety Specification

## REMOVED Requirements

### Requirement: print.js rejects file paths escaping the repo root
**Reason**: Agent-only refactor deletes `scripts/print.js`. The only code that read an arbitrary user-supplied file path from the CLI (`print.js --file`) is gone, so the path-traversal guard has no subject.
**Migration**: No replacement. In agent-only mode no script reads user-supplied file paths from the CLI; `prepare-digest.js` and `check-alerts.js` read feed files from a fixed `FOLLOW_THE_MONEY_FEED_DIR` resolved against the repo, not from free-form CLI arguments.
