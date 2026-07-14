# digest-output Specification

## MODIFIED Requirements

### Requirement: digest output SHALL include renderContext declaring the render basis
`prepare-digest.js` 输出的 JSON SHALL 包含 `renderContext` 对象,声明渲染所需依据:
- `language`:字符串,取自用户 `~/.follow-the-money/config.json` 的 `language` 字段,
  缺失或无法读取时回退 `"en"`。
- `prompts`:对象,键为 5 个 prompt 文件名(去扩展名、连字符转下划线,如 `digest_intro`),
  每项为 `{ source: "user" | "remote" | "repo" | "missing", text: string }`,其中
  `source` 为该 prompt 实际命中的来源,`text` 为该 prompt 文件的**完整 markdown 正文**——
  由 `lib/prompts/resolve.js` 在解析时读取并嵌入,LLM 直接消费,无需自行读文件或校验。

#### Scenario: renderContext embeds user-overridden prompt text
- **WHEN** 用户存在 `~/.follow-the-money/prompts/format-13f.md` 且仓库 `prompts/format-13f.md` 也存在
- **THEN** `renderContext.prompts.format_13f.source` SHALL 为 `"user"`
- **AND** `renderContext.prompts.format_13f.text` SHALL 等于该用户文件完整正文(非空)

#### Scenario: renderContext embeds remote prompt text when reachable
- **WHEN** 用户目录无覆盖且 GitHub `main` 分支该 prompt 可达(返回 2xx)
- **THEN** `renderContext.prompts.<name>.source` SHALL 为 `"remote"`
- **AND** `renderContext.prompts.<name>.text` SHALL 为 GitHub 上的最新正文

#### Scenario: renderContext embeds repo prompt text when offline or non-2xx
- **WHEN** 用户目录无覆盖且 GitHub 不可达或返回非 2xx(超时 / 网络错误 / 404 等)
- **THEN** `renderContext.prompts.<name>.source` SHALL 为 `"repo"`
- **AND** `renderContext.prompts.<name>.text` SHALL 为仓库 clone 内 `prompts/` 的快照正文

#### Scenario: language falls back when user config missing
- **WHEN** `~/.follow-the-money/config.json` 不存在或不含 `language`
- **THEN** `renderContext.language` SHALL 为 `"en"`

### Requirement: prompt resolution priority SHALL be enforced by code, not convention
prompt 解析优先级 SHALL 为 `user > GitHub 远程 > repo(clone)`,由单一解析函数
`lib/prompts/resolve.js`(现 async)实现,供 `prepare-digest.js`(及未来渲染工具)调用。
用户目录最高;其次尝试从 `raw.githubusercontent.com/<owner>/<repo>/<branch>/prompts/` 拉取最新版
(带 **5s 超时**,超时 / 网络错误 / 非 2xx / `fetch` 不可用均降级);最后回退到仓库 clone 内的 `prompts/`
快照(离线兜底,非默认源)。解析函数对每个 prompt 的远程尝试 SHALL 吞掉所有异常(超时 / 网络 / 非 2xx /
`fetch` 缺失),仅做层间降级,**绝不抛出**,以保证调用方的顶层 `await` 不会因网络问题 reject。
LLM SHALL 直接消费 `renderContext.prompts.*.text`,不依据 `source` 自行定位或校验 prompt 文件
(`source` 枚举含 `remote`,但 `remote` 无对应本地路径,不可映射为文件读取)。

#### Scenario: single resolver decides priority across three tiers
- **WHEN** 同时存在用户副本、GitHub 最新版、仓库 clone 三份同名 prompt
- **THEN** 解析结果 `source` SHALL 始终为 `"user"`,且 `lib/prompts/resolve.js` 为唯一实现该优先级的代码位置

#### Scenario: remote tier takes precedence over clone when reachable
- **WHEN** 无用户覆盖且 GitHub 可达
- **THEN** `source` SHALL 为 `"remote"`(而非 `"repo"`)

#### Scenario: remote fetch timeout falls back to clone within 5s
- **WHEN** GitHub 请求超过 5s、发生网络错误,或返回非 2xx(如 404)
- **THEN** 解析 SHALL 在 ≤5s 内降级到 clone,`source` 为 `"repo"`,digest 正常产出

## REMOVED Requirements

### Requirement: digest output SHALL NOT embed prompt text or config state
(本 change 推翻此要求:prompt 文本 SHALL 嵌入 `renderContext.prompts.*.text`;用户 config 状态字段
`lastAlertTimestamp`/`frequency` 等仍 SHALL NOT 嵌入,见下方 ADDED Requirement 的排除场景。)

## ADDED Requirements

### Requirement: prompt text SHALL be embedded in digest output
`prepare-digest.js` 输出的 `renderContext.prompts.<name>.text` SHALL 包含对应 prompt 文件的完整
markdown 正文。LLM 渲染时 SHALL 直接使用该 `text`,SHALL NOT 重新从磁盘读取 prompt 文件,SHALL NOT
对 prompt 内容做哈希校验。

#### Scenario: output includes prompt bodies
- **WHEN** 检查 `prepare-digest.js` 的输出 JSON
- **THEN** 对任意**命中 user / remote / repo 某一层(文件存在于该层)**的 prompt,
  JSON 中 SHALL 存在 `renderContext.prompts.<name>.text` 且为非空字符串
- **AND** `missing`(三层皆无文件,属配置错误且实际不可达)`text` 为空字符串,不在此不变量约束内

#### Scenario: output excludes config state
- **WHEN** 检查输出 JSON
- **THEN** JSON SHALL NOT 包含 `lastAlertTimestamp` / `frequency` 等用户 config 状态字段
- **AND** `renderContext` 仅含 `language` 与 `prompts` 的 `source`/`text` 数据
