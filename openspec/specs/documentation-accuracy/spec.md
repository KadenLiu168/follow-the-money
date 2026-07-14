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


### Requirement: SKILL.md SHALL express the feed-dir bridge once, not per step
`SKILL.md` Daily path SHALL 在文档中**只表达一次**「把 `fetch-feed.js` 解析出的 feed 目录桥接给
`prepare-digest.js` / `check-alerts.js`」的逻辑,供步骤 3(prepare)与步骤 6(check-alerts)共同引用;
SHALL NOT 在两处冗余地各自内联完整的 `--print-dir` 解析 + `FOLLOW_THE_MONEY_FEED_DIR` 赋值逻辑。

#### Scenario: feed-dir bridge not redundantly expressed across steps
- **WHEN** 读者检查 `SKILL.md` Daily path 的步骤 3 与步骤 6
- **THEN** 不得在两处各自完整内联「`node scripts/fetch-feed.js --print-dir` 并重新赋值
  `FOLLOW_THE_MONEY_FEED_DIR`」的桥接逻辑(无论两段是否字节级相同)
- **AND** 步骤 3 与步骤 6 对 feed 目录的解析/传递 SHALL 引用同一处定义(或等价地各自简短调用同一封装)

#### Scenario: fallback-to-cwd branch preserved in the single expression
- **WHEN** 文档描述 fetch 不可用时的本地回退
- **THEN** 那段唯一的 feed-dir 桥接逻辑 SHALL 仍包含「解析失败则回退 `node ... prepare-digest.js`(即 `|| cwd`)」的分支
- **AND** 不得因去重而删除该回退分支(否则破坏 `fetch-feed.js` 缺失时的韧性)
