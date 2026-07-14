# delivery Specification

## REMOVED Requirements

### Requirement: Stdout-only delivery
**Reason**: Agent-only refactor deletes `scripts/print.js`. The local skill no longer owns a delivery layer; the "exclusively via `scripts/print.js`" contract has no subject.
**Migration**: Agents invoke `scripts/prepare-digest.js` / `scripts/check-alerts.js`, read the JSON from stdout, render via `prompts/`, and deliver to the user through the agent runtime. No skill-side delivery script or channel exists.

### Requirement: No config dependency
**Reason**: This requirement existed solely to constrain `print.js` (which did not read config). With `print.js` deleted, the constraint is moot.
**Migration**: N/A — delivery is the agent's responsibility; the skill reads no delivery config.

### Requirement: No outbound network calls
**Reason**: This requirement constrained `print.js` from making HTTP calls. `print.js` is deleted.
**Migration**: N/A.

### Requirement: No dotenv loading
**Reason**: This requirement constrained `print.js` from loading `dotenv`. `print.js` is deleted.
**Migration**: N/A.

### Requirement: Local file read failure is surfaced, not retried
**Reason**: This requirement described `print.js --file` error handling. `print.js` is deleted.
**Migration**: N/A.
