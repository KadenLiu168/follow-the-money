## 1. 数据修复核心（repair script）

- [x] 1.1 新建 `scripts/repair-feed-units.js`（lib 函数 `repairFeed` + CLI 入口）：读取 `feed-13f.json`，遍历每个 filer、每个「期」快照
- [x] 1.2 逐快照检测单位：该快照 `holdings[].valueUsd` 的最大值 `>= 1e9` 即判为 dollars 存储（数学无歧义）
- [x] 1.3 将 dollars 快照的 `holdings[].valueUsd` 与 `summary.totalValueUsd` 统一 `÷1000` 归一为 thousands
- [x] 1.4 全量归一后，给每个 filer 条目盖上 `valueUnit: 'thousands'`，并清除遗留的 `valueUnitAdjusted` 歧义
- [x] 1.5 原子写回（复用 `lib/store/feed-json.js` 的 `writeFeedJson` tmp+rename）；重复运行幂等（已归一快照 `maxRaw < 1e9` 不再改动）；运行后打印"转换 N 个快照"
- [x] 1.6 本地运行脚本，`git diff feed-13f.json` 复核：仅见数值 `÷1000` 与新增 `valueUnit` 字段，无结构变更（实际转换 71 个快照，0 残留 dollars）

## 2. 加固 normalizeValueUnits（防复发核心）

- [x] 2.1 `lib/enrich/normalize-value-units.js`：当 `entry.valueUnit` 已声明（valid）时优先采用该条目自带标记，config 仅作兜底
- [x] 2.2 保持既有 config 解析语义与 `valueUnitAdjusted` 守卫不变；未带 marker 的 entry（旧/外部数据）仍走 config 兜底路径，既有测试不破

## 3. 写入时盖标记（防复发）

- [x] 3.1 ✅ **冲突最小调整**：proposal/design/spec 原写"在 `lib/aggregate/pipeline-b.js` 写入 `feed-13f.json` 时盖标记"——但 `pipeline-b.js` 实际写 13D/G 的 NDJSON 目录，**不碰 `feed-13f.json`**。真实 13F feed 写入函数是 `lib/store/feed-json.js` 的 `upsert13FFiling`（由 `runPipelineA` 调用）。故落到 `upsert13FFiling` 对每个持久化条目盖 `valueUnit: 'thousands'`，并同步修正 spec delta 的 prevent-recurrence 措辞以保持一致。

## 4. 反转 F1 测试放宽

- [x] 4.1 `tests/scripts/prepare-digest.test.js`：数据一致后，将 Berkshire `priorTotalValueUsd` / `totalValueUsd` 断言从结构性（finite/>0）恢复为精确量级（`274160086701` / `263095703570`——恰好等于 P1-1 前被放宽的原始值，证伪 1000× 失真）。

## 5. 测试

- [x] 5.1 `tests/scripts/repair-feed-units.test.js`：fixture 含混合单位（部分 dollars、部分 thousands）→ 全部归一为 thousands + 盖 `valueUnit` 标记；幂等重跑 `count = 0` 且值不变
- [x] 5.2 `tests/enrich/normalize-value-units.test.js`：新增 entry marker 优先场景（marker 与 config 冲突时 marker 胜出；marker 缺失回退 config）
- [x] 5.3 全量 `npm test` 通过（144 tests，含反转后的 prepare-digest 精确断言与新增 upsert 盖标记断言）

## 6. Notes / Findings

- **F1（重大，本 change 的由来，已解决）**：`feed-13f.json` 374 个「filer×期」快照中，71 个以 dollars 存储（maxRaw ≥ 1e9）、303 个以 thousands 存储；config `valueUnit: 'thousands'` 统一 ×1000 后，那 71 个被放大 1000×，`prepare-digest` 输出约 19% 跟踪期失真。该缺陷在 `fix-value-units-config`（P1-1）实施时暴露，彼时仅放宽测试掩盖，未修数据。**本轮一次性修复：71 快照 ÷1000 归一 + 全量盖 `valueUnit:'thousands'`，0 残留 dollars。**
- **数据文件改写需 sign-off**：本 change 重写了已提交的 `feed-13f.json`，已于生成本 proposal 前与用户确认。回滚方式：`git revert` 对应 commit（旧版留存于 git 历史）。
- **目标单位定为 thousands**：与现有 config 假设一致，`normalizeValueUnits` 的 ×1000 逻辑保持不变，blast radius 最小。
- **检测阈值无歧义**：单个持仓在 thousands 下最大为（美元额 / 1000），一个 $1B 持仓在 thousands 的 raw = 1e6，绝不可能 = 1e9，故 `maxRaw >= 1e9` 唯一对应 dollars 存储。
