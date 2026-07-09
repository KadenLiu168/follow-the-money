## Why

`feed-13f.json` 存在**混合单位数据债务**：374 个「filer×期」快照中，71 个以 **dollars** 存储（最大单持仓 raw ≥ 1e9，如 Berkshire 2022-12-31 期 Apple = 86.8e9），其余 303 个以 **thousands** 存储（同 filer 2016 期 Apple = 2.9e7）。这一现象同 filer 跨期混用单位。

在 `fix-value-units-config`（P1-1，已归档推送）之后，金额单位改由 `config/default-sources.json` 的 `valueUnit: "thousands"` 驱动，并对 `holdings[].valueUsd` 统一 ×1000。于是那 71 个 dollars 存储的快照被放大 **1000 倍**（$86.8B → $86.8T），digest 输出对约 19% 的跟踪期是错的。

该问题在 P1-1 实施时以 F1 重大发现暴露，目前仅靠把 `prepare-digest` 测试从精确量级断言放宽为结构性断言来"掩盖"——底层数据仍不一致。**现在需一次性修复数据并加防复发约束**，否则每轮 `prepare-digest` 都会产出失真金额。

## What Changes

- **一次性数据修复**：读取 `feed-13f.json`，逐快照检测单位（该快照最大单持仓 raw ≥ 1e9 即判定为 dollars 存储），将 dollars 快照的 `holdings[].valueUsd` 与 `summary` 合计 ÷1000 归一为 thousands；全量统一为单一单位后在每个 filer 条目盖上 `valueUnit` 标记，原子写回。
- **加固 `normalizeValueUnits`**：优先读取 feed 条目**自带**的 `valueUnit` 标记，config 仅作兜底——使数据自描述，消除"全局 config 猜测"的脆弱性。
- **防复发**：feed 生成环节（pipeline-b 写入 `feed-13f.json` 时）显式盖上 `valueUnit` 标记，使未来快照自带单位声明，不再混用。
- **反转 F1 测试放宽**：数据一致后，将 `tests/scripts/prepare-digest.test.js` 中因 F1 放松的断言恢复为精确量级。
- **新增修复脚本**：`scripts/repair-feed-units.js`（或等价的 lib 函数 + CLI），可重复运行、幂等、报告转换条数。

## Capabilities

### New Capabilities

<!-- 无新增能力；本 change 是既有 value-units-normalization 能力的补强与数据修复 -->

### Modified Capabilities

- `value-units-normalization`: 新增约束——feed 中每个 filer 条目**必须声明** `valueUnit` 标记；不允许存在混合单位债务；`normalizeValueUnits` 优先采用条目自带标记（config 兜底）。同时记录"一次性数据修复使历史快照归一为单一单位"这一已落地事实。

## Impact

- **数据**：`feed-13f.json`（已提交的大数据文件，将被重写——需用户 sign-off，已在生成本 proposal 前确认）。
- **代码**：`lib/enrich/normalize-value-units.js`（标记优先）、`lib/aggregate/pipeline-b.js`（写入时盖标记）、`scripts/repair-feed-units.js`（新增）。
- **测试**：`tests/enrich/normalize-value-units.test.js`（标记优先）、`tests/scripts/prepare-digest.test.js`（恢复精确量级）、新增 `tests/scripts/repair-feed-units.test.js`（检测/归一/标记）。
- **依赖**：无新增运行期依赖。
