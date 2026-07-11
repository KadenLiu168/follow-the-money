## Why

`scripts/prepare-digest.js` 只输出纯数据 JSON(thirteenF / thirteenDG / stats /
diagnostics)。两件事因此失控:

1. **数据降级不可见(明确缺陷)**。`validateManifest()` 算出的 manifest mismatch
   (行数不符、文件缺失、corrupt 行)只在 `prepare-digest.js` L66-69 `console.warn`
   到 stderr,**不进入 JSON**。渲染期 LLM 既收不到信号,也不会主动告知用户"今天数据
   拉取异常"。注意 `diagnostics.thirteenDGSkipped` 已把 corrupt 行带进 JSON,所以缺的
   仅是 manifest mismatch 这一路警告。

2. **渲染依据散落、靠记忆解析(潜在风险)**。渲染所需的 `config.language` 与 5 个
   prompt 文件由渲染期 LLM 自行读取,优先级 `用户 ~/.follow-the-money/prompts/ >
   仓库 prompts/` 仅写在 `references/prompt-customization.md` 文字里,无代码强制。
   一旦 agent 漏读或读了陈旧的用户副本,digest 不一致且无机制发现。

FB 的对应修法是把 prompts 文本整块塞进 JSON,但那直接否定本项目的设计选择
(`course/index.html` 明确把"LLM 读 prompts 渲染"当作有意特性)。本 change 取窄修:
降级信号进 JSON + 渲染依据用元数据显式化并代码强制优先级,**不把 prompt 文本绑进数据
契约、不剥夺 LLM 渲染灵活性**。

## What Changes

- `prepare-digest.js` 输出新增 `warnings: string[]`,收纳 `validateManifest` 的 mismatch
  警告与 feed 读取失败(原仅 stderr)。
- `prepare-digest.js` 输出新增 `renderContext` 对象,声明渲染依据:
  - `language`:来自用户 `~/.follow-the-money/config.json`(安全读取,缺失/损坏回退默认)。
  - `prompts`:每个 prompt 文件的解析结果 `{ source: "user" | "repo", hash: "<sha256>" }`,
    显式暴露"实际命中哪个版本"并供 LLM 按 hash 核实。
- 新增 `lib/prompts/resolve.js`:单点强制 `user > repo` 优先级,prepare 与(未来)渲染
  工具共用,消除"靠 agent 记忆"的解析。
- 新增 `lib/config/load-user-config.js`(`loadUserConfig()`):安全读取用户 config,
  缺失/损坏返回默认值(`language: "en"`)。`check-alerts.js` 的内联路径改用它。
- SKILL.md Step4 改为:渲染前先读 `renderContext`,按 `prompts.*.source/hash` 选择并核实
  prompt 版本,而非自行猜测优先级。
- 不嵌入 prompt 文本、不把 `lastAlertTimestamp`/`frequency` 等状态字段塞进 digest。

## Capabilities

### New Capabilities
- `digest-output`:规定 `prepare-digest.js` 的 JSON 输出契约——必须包含 `warnings`
  (数据降级信号)与 `renderContext`(渲染依据:language + 各 prompt 的解析来源与内容哈希)。

### Modified Capabilities
- `config-loading-unified`:新增 `loadUserConfig()` 要求——安全读取
  `~/.follow-the-money/config.json` 并在缺失/损坏时回退默认值,供 `prepare-digest.js`
  与 `check-alerts.js` 共用(替代后者的内联路径)。

## Impact

- 代码:`scripts/prepare-digest.js`(输出结构)、新增 `lib/prompts/resolve.js`、
  `lib/config/load-user-config.js`、`scripts/check-alerts.js`(改用统一加载器)。
- 契约:`prepare-digest.js` 输出 JSON schema 新增 `warnings` 与 `renderContext` 两字段
  (向后兼容,纯增量)。
- 文档:`SKILL.md` Step4、`references/prompt-customization.md`(优先级改为代码强制,
  文档降为说明而非唯一依据)。
- 测试:`tests/scripts/prepare-digest.test.js` 需覆盖 warnings 非空、renderContext 结构、
  user/repo 优先级命中、config 缺失回退。
