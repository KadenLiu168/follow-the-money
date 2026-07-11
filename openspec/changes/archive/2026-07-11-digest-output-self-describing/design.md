## Context

`prepare-digest.js` 当前输出纯数据 JSON(见 `scripts/prepare-digest.js` L97-112):
`schemaVersion / generatedAt / lookbackDays / thirteenF / thirteenDG / stats /
diagnostics`。两处缺口:

- `validateManifest(feedDir, manifest)`(lib/store/feed-ndjson.js L74-98)返回
  `{ ok, warnings }`,但调用方 L66-69 仅在 `!v.ok` 时 `console.warn`,警告不进 JSON。
  渲染期 LLM 完全看不到数据降级(manifest 行数不符、year 文件缺失、corrupt 行)。
  注:`read13DFilings` 的 corrupt 行计数已通过 `diagnostics.thirteenDGSkipped` 进 JSON,
  因此本 change 只需补齐 manifest mismatch 这一路。
- 渲染期 LLM 自行读取 `~/.follow-the-money/config.json`(language)与 5 个 prompt 文件,
  优先级 `user > repo` 只写在 `references/prompt-customization.md`,无代码强制。

约束:
- 本项目刻意让 LLM 承担渲染(`course/index.html` L574-575),故**不**把 prompt 文本嵌入
  JSON(那是 FB 的 O1 方案,会否定该设计、把模板绑成数据契约)。
- `config-loading-unified` 已确立"单一加载器"原则,目前只覆盖 repo 的
  `default-sources.json`;用户 config 仍由 `check-alerts.js` L13 内联手写读取。

## Goals / Non-Goals

**Goals:**
- 数据降级信号(`validateManifest` 警告 + feed 读取失败)进入 JSON,LLM 可见。
- 渲染依据(language + 各 prompt 实际命中来源与内容哈希)在 JSON 中显式声明,优先级由
  代码单点强制,LLM 可按哈希核实。
- 安全读取用户 config,缺失/损坏回退默认值,并统一 check-alerts 的内联路径。

**Non-Goals:**
- 不嵌入 prompt 文本到 JSON。
- 不把 `lastAlertTimestamp` / `frequency` 等状态字段塞进 digest。
- 不新增服务端渲染脚本(不把 LLM 移出渲染环)。
- 不改动 `diagnostics.thirteenDGSkipped` 现有行为。

## Decisions

### D1:降级信号进 `warnings: string[]`,且 prepare 仍照常写 stdout
`prepare-digest.js` 在输出前收集 `v.warnings`(manifest mismatch)与 feed 读取失败信息,
追加到 `out.warnings`。保留 `console.warn` 作为终端可见性,但**同时**入 JSON。
- 备选:删除 stderr 只留 JSON。否决——终端运行(🅱️ 本地模式)仍依赖 stderr 观察,
  且 FB 自身也是 warnings 进 JSON + 保留 stderr。

### D2:新增 `lib/prompts/resolve.js` 单点强制优先级
导出 `resolvePrompts({ names, userDir, repoDir })` → 返回每个 prompt 的
`{ source: "user" | "repo", text?, hash }`。prepare 只取 `source`+`hash`(不取 text),
渲染工具未来可取 `text`。优先级 `user > repo` 在此唯一实现,替代文档约定。
- 备选:在 SKILL.md 加更强措辞要求 agent 遵守优先级。否决——约定无法被测试或验证,
  正是 D2 指出的根因。

### D3:`renderContext.language` 经新建 `loadUserConfig()` 安全读取
新增 `lib/config/load-user-config.js` 导出 `loadUserConfig()`,读取
`~/.follow-the-money/config.json`,缺失/损坏/无 `language` 时回退 `"en"`。
`check-alerts.js` 的内联 `join(homedir(),'.follow-the-money','config.json')` 改用它。
- 备选:prepare 内联手写读取。否决——违背 `config-loading-unified` 的单一加载器原则,
  且重复脆弱路径(历史上有过路径写错导致配置永不可达的 bug,见
  `docs/code-quality-review-2026-07-08.md` L97-101)。

### D4:内容哈希用 sha256 的前 16 进制字符
prompt 文件内容取 `sha256` 摘要,输出前 16 位(`hash` 字段),足够 LLM 核实"读到的版本
与 prepare 解析的版本一致",且短小。使用 Node 内置 `crypto`,不引依赖。

## Risks / Trade-offs

- [Risk] `renderContext` 引入后,若 SKILL.md 未同步,旧 agent 仍忽略它 → 收益落空。
  → Mitigation:本 change 含 SKILL.md Step4 改写任务,明确"渲染前读 renderContext"。
- [Risk] `loadUserConfig()` 在 CI/无用户 config 环境返回默认 `language:"en"`,与真实
  用户 `bilingual` 不符 → 渲染语言与用户设置错位。
  → Mitigation:默认值 `"en"` 仅影响 renderContext 声明;渲染期 LLM 仍可直接读 config
  拿到真实值。renderContext 起"提示+核实"作用,非唯一真相源。
- [Risk] 输出体积略增(warnings 通常空,renderContext ~几百字节)。
  → Mitigation:均为纯增量字段,不影响现有字段;renderContext 不含 prompt 文本,增量极小。
- [Trade-off] 选 O2 而非 FB 的 O1:保留 LLM 渲染灵活性,代价是 prompt 文本仍需 LLM 从
  磁盘读(仅用 hash 核实)。这是为尊重项目设计的刻意取舍。

## Migration Plan

- 纯增量:新增 `warnings` / `renderContext` 字段,旧消费方(print.js、现有测试)忽略即可。
- `check-alerts.js` 改用 `loadUserConfig()` 为行为等价替换(路径与回退一致),无外部契约变化。
- 回滚:删除新增字段与两个 lib 文件即可,不影响数据管线。

## Open Questions

- 无。范围已与用户确认(O0+O2 窄修,不向 FB 全面对齐)。
