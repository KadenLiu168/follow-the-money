## ADDED Requirements

### Requirement: README 🅱️ local mode states JSON output, not markdown rendering

`README.md` 🅱️ (local self-run) instructions SHALL accurately state that `scripts/prepare-digest.js` emits a digest JSON document and that `scripts/print.js` only echoes that JSON to stdout. The README SHALL NOT claim the 🅱️ flow produces a rendered markdown summary; markdown rendering is performed only in the 🅰️ agent mode (LLM applies `prompts/` templates). This corrects the prior claim that running the 🅱️ commands yields "一份 markdown 摘要".

#### Scenario: 🅱️ step describes JSON, not markdown
- **WHEN** a reader follows README.md 🅱️ step 4 (run `prepare-digest.js`, then `print.js`)
- **THEN** the instructions state the output is the digest JSON (echoed verbatim by `print.js`), and they do NOT promise a markdown summary
- **AND** they note markdown rendering requires the 🅰️ agent mode
