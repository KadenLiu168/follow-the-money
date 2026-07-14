## ADDED Requirements

### Requirement: digest and alert output SHALL declare the feedDir actually read
`prepare-digest.js` 与 `check-alerts.js` 输出的 JSON SHALL 在**顶层**包含 `feedDir: string`
字段,其值为脚本**实际读取** feed 的 `FEED_DIR` 绝对路径(即求值为
`process.env.FOLLOW_THE_MONEY_FEED_DIR || process.cwd()` 后的最终字符串)。该字段 SHALL
如实反映读取来源(env 设了就是该目录;未设就是 `process.cwd()`),使调用方能区分
"用了刚 fetch 的缓存" 与 "用了 cwd 里 committed(可能偏旧)的 feed"。`feedDir` SHALL 位于
输出 JSON 顶层(与 `thirteenF` / `alerts` 等字段同级),SHALL NOT 被塞入 `diagnostics`
降级信号容器。

#### Scenario: skill-mode run reports the env-resolved dir
- **WHEN** `FOLLOW_THE_MONEY_FEED_DIR=/some/cache` 已设置且 `prepare-digest.js` 运行
- **THEN** 输出 JSON **顶层**的 `feedDir` SHALL 等于 `/some/cache`
- **AND** 该值与 `fetch-feed.js --print-dir` 在同一 env 下打印的目录一致

#### Scenario: local-mode fallback reports cwd
- **WHEN** `FOLLOW_THE_MONEY_FEED_DIR` 未设置且 `prepare-digest.js` 运行于 `process.cwd()` 为仓库根
- **THEN** 输出 JSON **顶层**的 `feedDir` SHALL 等于该 `process.cwd()` 绝对路径
- **AND** 输出的其余业务字段(`thirteenF` / `renderContext` / `diagnostics` 等)SHALL 不受影响

#### Scenario: check-alerts reports the same feedDir shape
- **WHEN** `check-alerts.js` 带 `FOLLOW_THE_MONEY_FEED_DIR` 运行
- **THEN** 其输出 JSON **顶层** SHALL 包含 `feedDir` 且等于该 env 目录(与 prepare-digest 同义,亦为顶层字段)
