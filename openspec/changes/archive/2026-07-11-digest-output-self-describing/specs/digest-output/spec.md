# digest-output Specification

## Purpose
规定 `scripts/prepare-digest.js` 输出的 digest JSON 必须自我描述:数据降级信号可见
(`warnings`),渲染依据显式声明并可核实(`renderContext`)。目标是让渲染期 LLM 无需
依赖散落的文档约定即可获得一致、可核查的渲染上下文,且不把 prompt 文本绑入数据契约。

## ADDED Requirements

### Requirement: digest output SHALL include a warnings array for degradation signals
`prepare-digest.js` 输出的 JSON SHALL 包含 `warnings: string[]` 字段。该数组 SHALL
收纳 `validateManifest()` 返回的 manifest mismatch 警告(行数不符、year 文件缺失、
corrupt 行),以及 feed 文件读取失败的信息。`console.warn` 可保留用于终端可见性,
但 SHALL 同时写入 `warnings`,不得只输出到 stderr。

#### Scenario: manifest mismatch is surfaced in JSON
- **WHEN** `feed-13dg/manifest.json` 声明某 year 有 N 条,但对应 ndjson 实际只有 M 条(N ≠ M)
- **THEN** `prepare-digest.js` 的输出 JSON SHALL 包含 `warnings` 数组且其中至少一项描述该 count mismatch
- **AND** 进程 SHALL 仍以退出码 0 正常输出(降级可见但不阻断)

#### Scenario: year file missing is surfaced in JSON
- **WHEN** `manifest.json` 记录了某 year,但对应 `<year>.ndjson` 文件不存在
- **THEN** 输出的 `warnings` SHALL 包含描述该 year 文件缺失的项

#### Scenario: clean run produces empty warnings
- **WHEN** manifest 与实际数据一致、无读取失败
- **THEN** 输出的 `warnings` SHALL 为 `[]`

### Requirement: digest output SHALL include renderContext declaring the render basis
`prepare-digest.js` 输出的 JSON SHALL 包含 `renderContext` 对象,声明渲染所需依据:
- `language`:字符串,取自用户 `~/.follow-the-money/config.json` 的 `language` 字段,
  缺失或无法读取时回退 `"en"`。
- `prompts`:对象,键为 5 个 prompt 文件名(去扩展名、连字符转下划线,如 `digest_intro`),
  每项为 `{ source: "user" | "repo", hash: string }`,其中 `source` 为该 prompt 实际
  命中的来源,`hash` 为所命中文件内容的 sha256 摘要前 16 位十六进制字符。

#### Scenario: renderContext reports user-overridden prompt
- **WHEN** 用户存在 `~/.follow-the-money/prompts/format-13f.md` 且仓库 `prompts/format-13f.md` 也存在
- **THEN** `renderContext.prompts.format_13f.source` SHALL 为 `"user"`
- **AND** `renderContext.prompts.format_13f.hash` SHALL 等于该用户文件内容的 sha256 前 16 位

#### Scenario: renderContext reports repo prompt when no user override
- **WHEN** 某 prompt 仅存在于仓库 `prompts/` 且用户目录无对应文件
- **THEN** `renderContext.prompts.<name>.source` SHALL 为 `"repo"`

#### Scenario: language falls back when user config missing
- **WHEN** `~/.follow-the-money/config.json` 不存在或不含 `language`
- **THEN** `renderContext.language` SHALL 为 `"en"`

### Requirement: prompt resolution priority SHALL be enforced by code, not convention
用户 prompt 目录(`~/.follow-the-money/prompts/`)SHALL 优先于仓库 `prompts/` 目录。
该优先级 SHALL 由单一解析函数(`lib/prompts/resolve.js`)实现,供 `prepare-digest.js`
(及未来渲染工具)调用;渲染期 LLM SHALL 依据 `renderContext.prompts.*.source` 选择版本,
而非依赖文档约定的记忆。

#### Scenario: single resolver decides priority
- **WHEN** 同时存在用户与仓库两份同名 prompt 文件
- **THEN** 解析结果 SHALL 始终以用户版本为 `source`,且 `lib/prompts/resolve.js` 为唯一实现该优先级的代码位置

### Requirement: digest output SHALL NOT embed prompt text or config state
`prepare-digest.js` 的输出 JSON SHALL NOT 包含 prompt 文件的完整文本内容,也 SHALL NOT
包含用户 config 的状态字段(`lastAlertTimestamp`、`frequency` 等)。`renderContext` 仅
携带来源与哈希等元数据。

#### Scenario: output excludes prompt bodies
- **WHEN** 检查 `prepare-digest.js` 的输出 JSON
- **THEN** JSON 中 SHALL NOT 存在任何 prompt 文件的完整 markdown 文本
- **AND** `renderContext` SHALL 仅含 `language` 与 `prompts` 的 `source`/`hash` 元数据
