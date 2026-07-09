# periodDiff units 归一化 — 设计

**日期**：2026-07-03
**作者**：brainstorming session with user
**状态**：待批准，待 writing-plans

---

## 背景

`tests/enrich/period-diff.test.js` 第 6 个用例（"normalizes prior entry units to match current (Baupost-style units mismatch)"，L86-108）目前**红（故意）**——added in commit `4d80d3b` 用来文档化一个已知 BUG：

- 当前 entry 已经 normalized 到 dollars（`valueUnitAdjusted: true`、holdings ×1000）
- prior entry 是 raw thousands（无 `valueUnitAdjusted`、holdings 未 ×1000）
- `periodDiff` 内部对 prior entry 不做任何 units 处理
- → `priorTotalValueUsd` 量级差 1000 倍，`deltaPct` 失真

测试期望 `priorTotalValueUsd === 110000000`（=110000 ×1000），但实际 `110000`。CI 长期 fail。

仓库**唯一**做 units 归一化的函数是 `lib/enrich/normalize-value-units.js` 的 `normalizeValueUnits(filerEntry, configSources)`：

- 启发式：`sum(valueUsd) < $1B → assume thousands, ×1000, mark valueUnitAdjusted`
- `idempotent`：已 normalized 的 entry 再跑一次（sum ≥ $1B）会原样返回，不二次 ×1000

---

## BUG 真实影响面评估

### 生产路径（scripts/prepare-digest.js）

L42 已经对整份 feed 跑 `normalizeValueUnits`：

```js
const normalizedFeed = f13.thirteenF.map((f) => normalizeValueUnits(f, defaultSources.thirteenF));
```

然后才喂给 `periodDiff`：

```js
const enriched = f13Filtered.map((f) => periodDiff(f, normalizedFeed));
```

注释 L38-41 明说：「Normalize the full feed ONCE so periodDiff can find a prior entry that shares the same unit regime as the current entry」。

**结论**：当前生产路径上，current 和 prior **都已经 normalized**，periodDiff 不会触发 BUG。**生产输出不受影响。**

### 非生产路径（直接调用 periodDiff）

`grep -rn "periodDiff(" lib scripts tests` 显示：

| 调用方                                                           | 是否预 normalize                                  | 是否触发 BUG   |
| ---------------------------------------------------------------- | ------------------------------------------------- | -------------- |
| `scripts/prepare-digest.js` L45                                  | 预 normalize（双重保险）                          | 否             |
| `tests/enrich/period-diff.test.js` L23/41/53/61/82（5 个绿测试） | prior 是 dollars-equivalent（valueUsd 量级 ≥$1B） | 否（巧合）     |
| `tests/enrich/period-diff.test.js` L102（红测试）                | 不预 normalize（故意制造 mismatch）               | **是（故意）** |
| 其他                                                             | 无                                                | 无             |

**结论**：BUG 在仓库所有调用路径里**只有这个红测试触发**，且是**故意**触发的。无生产回归。

### 未来风险

- 任何新的脚本/notebook/Agent 绕过 `prepare-digest.js` 直接调 `periodDiff(rawFeed)` 会立即触发 BUG
- `normalize-value-units.js` 是仓库内唯一的 units normalization pass；`compute13FSummary` 隐式假设 holdings.valueUsd 已统一单位
- 不修则技术债扩大；修则防御深度增加

### 修复决策

**修。** 调整 `periodDiff` 让它对 prior entry 自带 normalize 防御，调用方无需 care units 是否已 normalize。

---

## 目标

- `periodDiff` 内部对 prior entry 调一次 `normalizeValueUnits`，idempotent 防御
- `periodDiff` 接受可选第 3 参数 `configSources`（默认 `[]`）
- `scripts/prepare-digest.js` 显式传 `defaultSources.thirteenF`，保留 L42 预 normalize（双保险）
- 红测试变绿
- 新增 2 个 unit test（幂等性 + small-fund style prior）

---

## 非目标

- 不改 `lib/enrich/normalize-value-units.js`（启发式逻辑不在本次范围）
- 不改 `lib/compute/thirteen-f-summary.js`（已假设统一单位，本次不动）
- 不改 `lib/aggregate/pipeline-a.js` / `lib/store/feed-json.js` / `feed-13f.json` schema
- 不改 `prompts/` 任何文件
- 不改 `scripts/fetch-feed.js` / 其他 scripts（除 prepare-digest 第 3 参数外）
- 不重构归一化责任归属（保持 normalizeValueUnits 单一权威源 + periodDiff 内部防御 + prepare-digest 预 normalize 三层）

---

## 改动范围

**修改**（3 个文件）：

1. `lib/enrich/period-diff.js`
2. `scripts/prepare-digest.js`
3. `tests/enrich/period-diff.test.js`

**不动**：

- `lib/enrich/normalize-value-units.js`
- `lib/compute/thirteen-f-summary.js`
- `lib/aggregate/pipeline-a.js`
- `lib/store/feed-json.js`
- `feed-13f.json`
- `prompts/format-13f.md` 及其他 prompt 文件

---

## 设计

### API 改动 — `periodDiff(filerEntry, allFilings, configSources = [])`

```js
// lib/enrich/period-diff.js
import { normalizeValueUnits } from './normalize-value-units.js';

/**
 * Compute period-over-period summary for a 13F filer entry.
 *
 * Defensive: re-normalizes prior entry units (thousands → dollars) before diffing,
 * so callers don't have to pre-normalize the feed. No-op if already normalized
 * (normalizeValueUnits is idempotent).
 *
 * @param {Object} filerEntry     Current period entry (holdings in any unit; will be summed as-is)
 * @param {Array}  allFilings     All entries to search for prior period (heterogeneous units tolerated)
 * @param {Array}  configSources  config/sources entries with {cik, style} to preserve small-fund detection
 * @return {Object} filerEntry with attached summary: { newPositions, closedPositions, ... }
 */
export function periodDiff(filerEntry, allFilings, configSources = []) {
  const priorEntry = findPriorEntry(filerEntry, allFilings);
  if (!priorEntry) return { ...filerEntry, summary: null };

  const normalizedPrior = normalizeValueUnits(priorEntry, configSources); // ← 新增

  const raw = compute13FSummary(filerEntry.holdings || [], normalizedPrior.holdings || []);
  // ... 其余逻辑不变（currHoldings 用 filerEntry.holdings，priorHoldings 用 normalizedPrior.holdings）...
}
```

**为什么 normalize 只对 prior 而不是 prior+current**：current 已经在调用方传进来的状态，由调用方决定；current 已经被调用方处理过就不应该再被 periodDiff 二次 ×1000（会破坏 prepared 数据）。prior 是从 `allFilings` 里**反向搜**到的，periodDiff 对它的单位状态**没有控制权**，必须自己处理。

### 调用方契约

调用方负责保证 `filerEntry.holdings`（current entry）已经 units 统一（dollars 或 thousands 一致）。periodDiff 只对 prior entry 做归一化，不对 current 做。

- `scripts/prepare-digest.js` L42 已经对整份 feed 跑 `normalizeValueUnits`，所以 current 在调用时保证是 normalized dollars。
- 任何新的调用方脚本必须自己保证 current 已 normalized（或自行决定 units 语义），并把 `configSources` 传给 `periodDiff` 让 prior 也能正确识别。

### 内部行为细节

```js
const priorEntry = findPriorEntry(filerEntry, allFilings);
if (!priorEntry) return { ...filerEntry, summary: null };

const normalizedPrior = normalizeValueUnits(priorEntry, configSources);

const raw = compute13FSummary(filerEntry.holdings || [], normalizedPrior.holdings || []);
const priorHoldings = normalizedPrior.holdings || [];

// currHoldings 仍用 filerEntry.holdings（调用方已 normalize 或显式保持 raw，不动它）
const currHoldings = filerEntry.holdings || [];

const newPositions = raw.newPositions
  .map((cusip) => lookupCusip(cusip, currHoldings))
  .filter(Boolean)
  .map((h) => ({
    cusip: h.cusip,
    issuerName: h.issuerName,
    shares: h.shares,
    valueUsd: h.valueUsd,
  }));

const closedPositions = raw.closedPositions
  .map((cusip) => lookupCusip(cusip, priorHoldings))
  .filter(Boolean)
  .map((h) => ({
    cusip: h.cusip,
    issuerName: h.issuerName,
    sharesAtClose: h.shares,
    valueUsdAtClose: h.valueUsd,
  }));

const priorTotalValueUsd = priorHoldings.reduce((s, h) => s + (Number(h.valueUsd) || 0), 0);
const deltaPct =
  priorTotalValueUsd === 0 ? 0 : (raw.totalValueUsd - priorTotalValueUsd) / priorTotalValueUsd;

return {
  ...filerEntry,
  summary: {
    newPositions,
    closedPositions,
    increasedPositions: raw.increasedPositions,
    decreasedPositions: raw.decreasedPositions,
    totalValueUsd: raw.totalValueUsd,
    priorTotalValueUsd,
    deltaPct,
  },
};
```

### 数据流（三层防御）

```
feed-13f.json (raw, mixed units)
    │
    ▼ normalizeValueUnits × N （prepare-digest L42，**第一层**：所有 N 个 entry 都被规范化）
normalizedFeed
    │
    ▼ periodDiff × M
    │  内部：findPriorEntry → normalizeValueUnits × 1 （**第二层**：prior entry 再被规范化一次，idempotent）
    │  注入防御：即使调用方忘了第一层，这里也会自动跑
    ▼
enriched entries (periodDiff output)
```

第二层对已 normalized entry 是 no-op（idempotent），所以**双保险无副作用**。

### 错误处理

- `normalizeValueUnits` 当前实现所有分支都 return，没有 throw → 不新增 try/catch
- 万一未来 normalizeValueUnits 抛错，透传到调用方（与现有约定一致）

### 测试覆盖（tests/enrich/period-diff.test.js）

| #   | 名称                                                                                      | 状态变化    |
| --- | ----------------------------------------------------------------------------------------- | ----------- |
| 1   | "produces rich newPositions/closedPositions with prior + delta fields"                    | 绿（不动）  |
| 2   | "returns summary: null when no prior period exists"                                       | 绿（不动）  |
| 3   | "uses the most recent prior when multiple exist"                                          | 绿（不动）  |
| 4   | "only diffs within same CIK (never cross-CIK)"                                            | 绿（不动）  |
| 5   | "breaks periodOfReport ties by latestFilingDate desc"                                     | 绿（不动）  |
| 6   | "normalizes prior entry units to match current (Baupost-style units mismatch)"            | **红 → 绿** |
| 7   | **新增**："returns identical result when prior entry is already in dollars (idempotency)" | 新增        |
| 8   | **新增**："treats prior entry as small-fund style when its CIK matches small-fund config" | 新增        |

测试 7（幂等性）验证：

```js
const current = baseEntry('0001061768', '2026-03-31', [
  { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 1000000000, ... },
]);
const prior = baseEntry('0001061768', '2025-12-31', [
  { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 1100000000, ... },
]);
const cfg = [{ cik: '0001061768', name: 'Baupost Group', style: 'value' }];
const out = periodDiff(current, [current, prior], cfg);
expect(out.summary.priorTotalValueUsd).toBe(1100000000);  // sum≥$1B → 不×1000
```

测试 8（small-fund）验证：

```js
// 当前 size 30M dollars（不会被 normalize 触发），prior size 30 raw dollars（会被识别为 thousands）
const current = baseEntry('0001061768', '2026-03-31', [
  { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 30000000, ... },
]);
const prior = baseEntry('0001061768', '2025-12-31', [
  { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 30, ... },
]);
const cfg = [{ cik: '0001061768', name: 'Tiny Filer', style: 'small-fund' }];
const out = periodDiff(current, [current, prior], cfg);
// small-fund style → valueUnit: 'unknown' → 不×1000
expect(out.summary.priorTotalValueUsd).toBe(30);  // raw 保留
```

### 注释

- `lib/enrich/period-diff.js` L1-6 头部注释：从原「Period-over-period summary... Adds priorTotalValueUsd + deltaPct.」扩展说明 units 防御职责
- `scripts/prepare-digest.js` L38-41 注释：从原「Normalize the full feed ONCE so periodDiff can find a prior entry...」扩展说明双保险

---

## 实施步骤（交给 writing-plans）

1. 改 `lib/enrich/period-diff.js`：新增 import、新签名、normalize 调用、JSDoc
2. 改 `scripts/prepare-digest.js` L45：加第 3 参数 `defaultSources.thirteenF`，注释更新
3. 加 2 个新 unit test 到 `tests/enrich/period-diff.test.js`（幂等性 + small-fund）
4. 跑 `npx vitest run tests/enrich/period-diff.test.js`：期望 8/8 pass
5. 跑 `node scripts/prepare-digest.js --lookback 90`：取 Baupost Q1 2026 段，确认 `summary.priorTotalValueUsd` 量级 ≈ ×10^9（确认生产路径不受影响）
6. 三连 commit：
   - `fix(period-diff): normalize prior entry units defensively`
   - `test(period-diff): cover idempotency and small-fund style prior`
   - `docs(period-diff): document units normalization defensive layer`

---

## 成功标准

- `npx vitest run tests/enrich/period-diff.test.js` → 8/8 pass
- `npx vitest run` → 所有原本绿的 test 仍绿，无新回归
- `node scripts/prepare-digest.js --lookback 90` → Baupost Q1 2026 `summary.priorTotalValueUsd` ≈ $1B+ 量级（与现状一致）
- CI 红测试消失
