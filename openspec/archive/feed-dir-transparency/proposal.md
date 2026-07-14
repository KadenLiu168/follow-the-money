## Why

差异 A 残留两类问题:其一是**可观测性缺口**——`prepare-digest.js` / `check-alerts.js` 实际读取的 feed 目录(`FEED_DIR`)不体现在输出里,当 `FOLLOW_THE_MONEY_FEED_DIR` 未设时脚本静默回退 `process.cwd()`,而该目录里是仓库 committed(可能偏旧)的 feed;调用方无法区分"用的是刚 fetch 的缓存"还是"用的是 cwd 旧数据"。其二是 **SKILL.md 表达重复**——Daily path 步骤 3 与步骤 6 各写了一段完全相同的 `--print-dir` 内联 shell 来桥接 feed 目录,任何改动需同步两处,是维护性债务。两者同源(差异 A 残留),且都能在不改解析语义的前提下一次收口。

## What Changes

- `prepare-digest.js` 输出的 `diagnostics` 对象新增 `feedDir` 字段,值为脚本**实际读取**的 FEED_DIR 绝对路径(= `process.env.FOLLOW_THE_MONEY_FEED_DIR || process.cwd()`)。
- `check-alerts.js` 输出同样新增 `feedDir` 字段,语义与 prepare 一致。
- `SKILL.md` Daily path 步骤 3 / 步骤 6 收敛两段重复的 `--print-dir` 内联 shell(行为等价,仅消除重复)。
- 测试补充:`feed-dir-propagation.test.js` 断言输出含 `feedDir` 且等于 env 设的目录;`prepare-digest.test.js` 现有无-env 用例顺带断言 `feedDir === cwd`。

## Capabilities

### New Capabilities
<!-- 无新增 capability -->

### Modified Capabilities
- `digest-output`: 新增 requirement——digest/alert 输出 SHALL 在 JSON **顶层**声明实际读取的 `feedDir` 绝对路径(透明化,不引入新解析语义,不塞入 `diagnostics` 降级信号容器)。
- `documentation-accuracy`: 新增 requirement——`SKILL.md` 的 feed 目录桥接逻辑 SHALL 只表达一次,不在步骤 3 与步骤 6 重复 `--print-dir` 内联 shell。

> 明确**不修改** `feed-dir-resolution` spec:其已锁定的解析规则(单一源、`env` 优先、`||cwd` 本地回退)本 change 一律不动。

## Impact

- 代码:`scripts/prepare-digest.js`(输出加字段)、`scripts/check-alerts.js`(输出加字段)、`SKILL.md`(去重两段 shell)。
- 测试:`tests/scripts/feed-dir-propagation.test.js`、`tests/scripts/prepare-digest.test.js`。
- 依赖:无新依赖。
- **非目标(BREAKING 均无)**:
  - 拒绝 **A2**——不合并 `fetch-feed.js` 进 `prepare-digest.js`(会破坏离线 fixture 测试架构,且 fetch/prepare 分离是 load-bearing)。
  - 不碰 **(2) 解析器分叉重设计**:读侧 `env||cwd` 与写侧 `env||平台缓存` 的优先级权衡由 `feed-dir-resolution` 锁定,不在本 change 范围。
  - 不改变 `prepare-digest.js` 的主源 hard-fail 语义(铁律"部分输出比无输出更糟"不变)。
