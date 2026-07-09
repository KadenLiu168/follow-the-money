## Context

`feed-13f.json` 是聚合产物，含 374 个「filer×期」快照（8 支基金、各多期），每个快照带 `holdings[]`（`valueUsd`）与 `summary`。实测：

- **71/374 快照以 dollars 存储**（该快照最大单持仓 raw ≥ 1e9，如 Berkshire 2022-12-31 期 Apple = 86.8e9）。
- **303/374 以 thousands 存储**（同 filer 2016 期 Apple = 2.9e7）。
- 同一 filer 跨期混用单位——典型数据债务，源于历史多次 feed 重生成未统一单位。

`fix-value-units-config`（P1-1，已归档）把单位解析改为按 `config/default-sources.json` 的 `valueUnit: 'thousands'` 驱动，并对 `holdings[].valueUsd` 统一 ×1000。于是那 71 个 dollars 快照被放大 **1000 倍**（$86.8B → $86.8T），`prepare-digest` 输出对约 19% 的跟踪期失真。该缺陷在 P1-1 以 F1 重大发现暴露，现靠放宽 `prepare-digest` 测试为结构性断言掩盖。

本 change 一次性修复历史数据，并以"条目自带单位标记"约束杜绝复发。

## Goals / Non-Goals

**Goals:**
- 将 `feed-13f.json` 全部 374 快照归一为单一单位（thousands），与 config 假设一致。
- 每个 filer 条目盖上 `valueUnit` 标记，使数据自描述。
- 加固 `normalizeValueUnits`：优先采用条目自带标记（config 兜底），消除"全局猜测"脆弱性。
- feed 生成环节显式盖标记，未来快照不再混用。
- 反转 F1 时期的测试放宽，恢复精确量级断言。

**Non-Goals:**
- 不改动 SEC 13F `<value>` 官方"thousands"语义。
- 不为每支基金引入差异化单位（保持 config 统一 thousands）。
- 不重写聚合/抓取管线逻辑，仅在"写入 feed 时盖标记"这一最小切面介入。
- 不处理其他 P2/P3 项（如抽 `atomic-write.js`、CI 门禁等）。

## Decisions

**D1 — 目标单位定为 thousands（而非 dollars）**
理由：config 已声明 `thousands`，`normalizeValueUnits` 的 ×1000 逻辑保持不变 → 修复后全量数据 ×1000 即正确美元，blast radius 最小。若选 dollars，则需同步改 config 与 `normalizeValueUnits` 两处，风险更大。

**D2 — 检测启发式：`maxRaw >= 1e9` 判为 dollars**
理由：单个持仓在 thousands 下最大为（约）`持仓美元额 / 1000`。一个 $1B 持仓在 thousands 下 raw = 1e6，**绝不可能是 1e9**。故 raw ≥ 1e9 唯一对应"以 dollars 存储"，阈值无歧义。改用 `total >= 1e11` 亦可，但 max 更鲁棒（稀疏/空持仓不影响）。

**D3 — 修复即 `valueUsd /= 1000`，并盖 `valueUnit: 'thousands'` 标记**
对判定为 dollars 的快照：其 `holdings[].valueUsd` 与 `summary` 合计均 ÷1000；全部快照统一为 thousands 后，每个 filer 条目写入 `valueUnit: 'thousands'`，并清除历史遗留的 `valueUnitAdjusted` 歧义。

**D4 — `normalizeValueUnits` 优先读条目自带 `valueUnit` 标记**
函数签名不变，新增优先级：`entry.valueUnit` 已声明（repair 后所有条目都有）→ 以它为准；未声明（旧/外部数据）→ 回退 config。config 仍兜底的语义保持不变，但"全局 config 猜测"不再对 repaired 数据起决定作用。

**D5 — feed 生成环节盖标记（防复发）**
`lib/aggregate/pipeline-b.js` 在构造/追加 filer 条目写入 `feed-13f.json` 时，显式写入 `valueUnit`（来自 SEC `<value>` 官方 thousands 语义）。未来快照自带声明，即使 config 漂移也不会再产生混合债务。

**D6 — 修复脚本幂等、可重复、原子**
`scripts/repair-feed-units.js`：读全量 → 逐快照检测/归一/盖标记 → `temp + rename` 原子写回；重复运行结果稳定（已归一快照 `maxRaw < 1e9` 不再被改动）；运行后打印"转换 N 个快照"。

## Risks / Trade-offs

- **[Risk] 检测误判单位** → `maxRaw >= 1e9` 在数学上无歧义（见 D2），误判概率 0；脚本运行前先在内存统计"将转换 N 个"并打印，人工可核对。
- **[Risk] 改写已提交的大数据文件** → 已获用户 sign-off；采用原子写 + git 历史天然留存旧版，回滚即 `git revert`；不改文件名、不改 schema。
- **[Risk] `summary` 合计未随 `holdings` 同步** → 修复同时归一 `summary` 内合计字段，避免"持仓对、汇总错"。
- **[Trade-off] 选 thousands 而非 dollars** → 见 D1，换来最小改动面；代价是 feed 文件数值仍是"千美元"紧凑表示（人类可读性略低，但机器一致）。
- **[Trade-off] 新增 `valueUnit` 标记字段** → feed 体积微增、schema 多一个字段；换来自描述与防复发，收益大于成本。

## Migration Plan

1. 本地运行 `node scripts/repair-feed-units.js`（或经 `/opsx:apply` 跑 tasks）。
2. `git diff feed-13f.json` 复核：应只见数值 ÷1000 与新增 `valueUnit` 字段，无结构变更。
3. 提交修复后的 `feed-13f.json`（单独 commit，便于回滚）。
4. 跑 `npm test`：新增 repair 测试 + 反转后的 prepare-digest 精确断言均应通过。
5. **回滚**：`git revert <commit>` 即恢复旧 feed；`normalizeValueUnits` 代码改动回滚需同步 revert 对应 commit。

## Open Questions

- 无。修复策略（目标单位 / 检测阈值 / 防复发切面）已在生成本 proposal 前与用户对齐。
