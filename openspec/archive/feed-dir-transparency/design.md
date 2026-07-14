## Context

差异 A 经 explore 分析后收敛出两类残留,均不触及 feed 目录的**解析语义**(已由 `feed-dir-resolution` spec 锁定:单一源、`env` 优先、未设则 `||cwd` 本地回退):

1. **可观测性缺口**。`prepare-digest.js:(17)` 与 `check-alerts.js:(11)` 各自用 `FEED_DIR = process.env.FOLLOW_THE_MONEY_FEED_DIR || REPO` 求值,但这个实际读取的目录**不出现在输出 JSON** 中。调用方(agent/CI)无法判断这次 digest 用的是「刚 `fetch-feed.js` 拉到平台缓存的 fresh 数据」还是「`cwd` 里 committed 的偏旧数据」。在 SKILL agent 路径下靠强制设 env 桥接才正确;一旦离开那段精确 shell(手动 `fetch` 后 `prepare` 无 env)就会静默读 cwd 旧数据。
2. **SKILL.md 表达重复**。Daily path 步骤 3 与步骤 6 各写了一段完全相同的 `--print-dir` 内联 shell 来把 fetch 解析出的目录传给 prepare / check-alerts,任何改动需同步两处。

关键约束:本 change **只做透明化与去重**,绝不重排解析优先级。解析分叉(读侧 `env||cwd` vs 写侧 `env||平台缓存`)属于 (2),由 `feed-dir-resolution` 锁定,不在范围。

## Goals / Non-Goals

**Goals:**
- 让 digest / alert 输出**声明**脚本实际读取的 `feedDir` 绝对路径,把"静默用旧数据"变成可断言事实。
- 把 SKILL.md 的 feed 目录桥接逻辑**表达一次**,消除步骤 3 / 6 的重复内联 shell。

**Non-Goals:**
- 不合并 `fetch-feed.js` 进 `prepare-digest.js`(即拒绝 **A2**):fetch/prepare 分离是 load-bearing——prepare 需能离线跑 fixture 测试,合并会破坏测试架构且引入网络耦合。
- 不做 (2) 解析器分叉重设计:`FOLLOW_THE_MONEY_FEED_DIR` 未设时 cwd 回退的去留、cwd committed vs 平台缓存的优先级,由 `feed-dir-resolution` 决定;本 change 一律沿用。
- 不改主源 hard-fail 语义(铁律"部分输出比无输出更糟"不变)。

## Decisions

### D1 — `feedDir` 作为输出 JSON 的顶层字段
`prepare-digest.js` 的输出已采用顶层布局(`schemaVersion` / `thirteenF` / `diagnostics` / `renderContext` 等均为顶层);`check-alerts.js` 输出为 `{alerts, capped, summary}` 顶层结构。两脚本**均不存在、也不应引入** `diagnostics` 容器来承载 `feedDir`——`diagnostics` 在 prepare-digest 里是降级信号(`valueUnitsAdjusted` / `summaryMissing` / `thirteenDGSkipped`)的归属,混入路径字段会污染其语义。故两脚本统一在**输出顶层**新增 `feedDir` 字段。
- **替代方案**:塞进 `diagnostics.feedDir`。否决——该容器在两个脚本中要么不存在(check-alerts)、要么仅承载降级信号(prepare-digest),不符合其语义;且顶层 `feedDir` 与 prepare-digest 现有顶层风格一致,消费方(agent/CI)取用更直接。

### D2 — `feedDir` 取脚本求值后的 `FEED_DIR` 原值
即 `process.env.FOLLOW_THE_MONEY_FEED_DIR || process.cwd()` 的最终字符串,**不做** `defaultTargetDir()` 平台缓存推导(env 未设时仍报 `cwd`,如实反映"我读了 cwd")。这与 `feed-dir-resolution` 的本地回退契约一致,且正是要暴露"读的是 cwd"这一事实。
- **替代方案**:在 env 未设时也展开成平台缓存路径。否决——那会伪造"我用了缓存"的假象,违背透明化初衷。

### D3 — SKILL.md 去重采用「抽一处、两处引用」而非「内联推导」
步骤 3/6 收敛为一段统一的 feed-dir 解析块(等价 `FEED_DIR="$(node scripts/fetch-feed.js --print-dir)" && FOLLOW_THE_MONEY_FEED_DIR="$FEED_DIR" node ...` 的封装),其余步骤引用同一 `FEED_DIR`。保留「fetch 不可用时回退 cwd」分支(env 未解析成功则直接 `node scripts/prepare-digest.js`),因 `fetch-feed.js` 缺失时 `|| process.cwd()` 兜底仍是合理韧性。

## Risks / Trade-offs

- **[Risk] 输出新增字段被视为 breaking** → 缓解:仅新增顶层 `feedDir`,现有字段/结构不变,消费方(LLM 照常读 `renderContext` / `thirteenF` / `alerts`)零影响;旧 JSON 解析器忽略未知字段。
- **[Risk] 测试需覆盖 feedDir 不变量** → 缓解:`feed-dir-propagation.test.js` 已能构造 env vs cwd 两种目录并断言读取来源,顺手断言 `feedDir` 等于期望目录即可,不新增测试架构。
- **[Trade-off] 透明化不消除分叉** → 接受:本 change 只让分叉"可见",不消除它;真正消除分叉是 (2),需另立 change 且在 explore 中先想透"clone committed feed 会遮蔽 fresh 缓存"的陷阱。

## Migration Plan

纯增量改动。
- 应用:改 `prepare-digest.js` / `check-alerts.js` 输出 + 改 `SKILL.md` + 补测试。
- 回滚:`git revert` 对应提交即可,无数据迁移、无 schema 破坏。
