# documentation-accuracy Specification

## Purpose
TBD - created by archiving change fix-doc-drift-findings. Update Purpose after archive.
## Requirements
### Requirement: Documentation accurately reflects implementation
The project documentation (`references/`, `README.md`, `prompts/`, `docs/`) SHALL describe the
actual implemented behavior of the system, not an outdated or assumed behavior. Contradictions
between docs and code identified by the OpenSpec consistency audit SHALL be corrected at the
source (the doc), not by changing correct code.

#### Scenario: thirteenF entry cardinality is correct
- **WHEN** a reader consults `references/data-formats.md` for the `thirteenF` feed shape
- **THEN** it states the upsert key is `filerCik + periodOfReport` (one entry per filer per quarter), and it does NOT claim a hard "max 8" cap

#### Scenario: CI cron is described as UTC with DST caveat
- **WHEN** a reader consults `README.md` or `references/architecture.md` for the aggregation schedule
- **THEN** it shows the literal cron `0 12 * * *` + `0 0 * * *` (UTC) and labels it "≈08:00 ET (DST-naive)"

#### Scenario: Local feed fetch file count is correct
- **WHEN** a reader consults `references/architecture.md` for what `fetch-feed` downloads
- **THEN** it states "4 static files + per-year NDJSON discovered from manifest", not "5 data files"

#### Scenario: Alert classification taxonomy is unambiguous
- **WHEN** a reader consults `references/alert-rules.md` for the classification model
- **THEN** it states "three-level" is a behavior taxonomy; `classify.js` returns only `alert`/`digest`; `merged alert` is emergent; `intent` is written by the parsers

#### Scenario: Alert render does not duplicate amendment count
- **WHEN** an alert with N amendments is rendered via `prompts/format-alert.md`
- **THEN** the phrase "修订 N 次" appears exactly once (sourced from `merge-amendments.js` summary), not doubled by a prompt prefix

#### Scenario: Node engine floor matches syntax usage
- **WHEN** a contributor sets up the repo (reads `.nvmrc` / `package.json` `engines.node`)
- **THEN** the floor is `>=20.19.0`, matching `prepare-digest.js` use of `import ... with { type: 'json' }`

#### Scenario: Resolved review findings are annotated
- **WHEN** a reader opens `docs/code-quality-review-2026-07-08.md`
- **THEN** its High items H1/H2/H3 are marked resolved by OpenSpec changes `stdout-only-delivery`, `value-units-normalization`, `add-digest-time-seam`

### Requirement: README 🅱️ local mode states JSON output, not markdown rendering

`README.md` 🅱️ (local self-run) instructions SHALL accurately state that `scripts/prepare-digest.js` emits a digest JSON document and that `scripts/print.js` only echoes that JSON to stdout. The README SHALL NOT claim the 🅱️ flow produces a rendered markdown summary; markdown rendering is performed only in the 🅰️ agent mode (LLM applies `prompts/` templates). This corrects the prior claim that running the 🅱️ commands yields "一份 markdown 摘要".

#### Scenario: 🅱️ step describes JSON, not markdown
- **WHEN** a reader follows README.md 🅱️ step 4 (run `prepare-digest.js`, then `print.js`)
- **THEN** the instructions state the output is the digest JSON (echoed verbatim by `print.js`), and they do NOT promise a markdown summary
- **AND** they note markdown rendering requires the 🅰️ agent mode

