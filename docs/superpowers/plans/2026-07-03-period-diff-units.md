# periodDiff units 归一化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `tests/enrich/period-diff.test.js` 第 6 个测试（commit 4d80d3b 红测试）变绿，同时为 `periodDiff` 增加 units 归一化防御层。

**Architecture:** 在 `periodDiff` 内部对 `priorEntry` 调 `normalizeValueUnits`（idempotent 防御）。`prepare-digest.js` 显式传 `defaultSources.thirteenF` 让小-fund filer 的 prior 也能正确识别 units。production 路径（prepare-digest L42 已经预 normalize）保持现状不变。

**Tech Stack:** Node 20+, vitest 2.x, ESM modules

## Global Constraints

- 不动 `lib/enrich/normalize-value-units.js`（启发式逻辑不在本次范围）
- 不动 `lib/compute/thirteen-f-summary.js`（已假设统一单位）
- 不动 `lib/aggregate/pipeline-a.js` / `lib/store/feed-json.js` / `feed-13f.json` schema
- 不动 `prompts/` 下任何文件
- `periodDiff` 只对 prior 做 normalize；current 由调用方负责（prepare-digest L42 预 normalize）
- 新签名：`periodDiff(filerEntry, allFilings, configSources = [])`，`configSources` 默认 `[]`
- 所有 commit message 用中文（per 项目 convention）
- 任何 commit 不允许 push（per session 规则）
- commit author 用 `Claude <claude-fable-5@noreply.anthropic.com>`（GIT_AUTHOR_NAME 走 env vars）

---

### Task 1: 修 periodDiff + 让现有 red test 变绿

**Files:**
- Modify: `lib/enrich/period-diff.js`（加 import + 新第 3 参数 + 内部 normalize 调用 + JSDoc）
- Modify: `scripts/prepare-digest.js:45`（传第 3 参数）

**Interfaces:**
- Consumes: `lib/enrich/normalize-value-units.js` 的 `normalizeValueUnits(filerEntry, configSources)`（已有幂等实现）
- Produces: `periodDiff(filerEntry, allFilings, configSources = [])` 新签名；`prepare-digest.js` L45 改为 `periodDiff(f, normalizedFeed, defaultSources.thirteenF)`

- [ ] **Step 1: 读现有 lib/enrich/period-diff.js（已读过）**

`lib/enrich/period-diff.js` 当前 67 行，函数签名 `periodDiff(filerEntry, allFilings)`。`lib/enrich/normalize-value-units.js` 导出 `normalizeValueUnits(filerEntry, configSources)`，对 sum(valueUsd) < $1B 的 entry ×1000 并标 `valueUnitAdjusted: true`，对 sum ≥ $1B 的 entry 不动（idempotent），对 matchedSource.style === 'small-fund' 的 entry 标 `valueUnit: 'unknown'` 不 ×1000。

- [ ] **Step 2: 改 lib/enrich/period-diff.js**

完整替换文件为以下内容：

```javascript
// Period-over-period summary for a 13F filer entry.
//
// Finds the most recent prior filing for the same CIK, calls
// compute13FSummary, then reshapes the CUSIP-string outputs into
// rich object arrays (cusip + issuerName + shares + valueUsd) for
// renderer use, and adds priorTotalValueUsd + deltaPct.
//
// Defensive units normalization: prior entry is re-normalized here
// (sum<1B → ×1000 to dollars) so callers don't have to pre-normalize
// the feed. normalizeValueUnits is idempotent, so this is a no-op
// when prior is already in dollars. Current entry is the caller's
// responsibility — see scripts/prepare-digest.js for the canonical
// pre-normalization pass.

import { compute13FSummary } from '../compute/thirteen-f-summary.js';
import { normalizeValueUnits } from './normalize-value-units.js';

/**
 * @param {Object} filerEntry  Current period entry. Caller must pre-normalize units if needed.
 * @param {Array}  allFilings  All entries to search for prior period (heterogeneous units tolerated).
 * @param {Array}  [configSources=[]]  Filers config (with `cik` and optional `style: 'small-fund'`) for units detection.
 * @return {Object} filerEntry with attached summary: { newPositions, closedPositions, increasedPositions, decreasedPositions, totalValueUsd, priorTotalValueUsd, deltaPct }.
 */
export function periodDiff(filerEntry, allFilings, configSources = []) {
  const priorEntry = findPriorEntry(filerEntry, allFilings);
  if (!priorEntry) {
    return { ...filerEntry, summary: null };
  }

  // Defensive units normalization: prior entry's unit regime is uncontrolled by
  // periodDiff (it was reverse-looked-up). normalizeValueUnits idempotent — no-op
  // when prior is already normalized dollars or a small-fund style.
  const normalizedPrior = normalizeValueUnits(priorEntry, configSources);

  const raw = compute13FSummary(filerEntry.holdings || [], normalizedPrior.holdings || []);
  const currHoldings = filerEntry.holdings || [];
  const priorHoldings = normalizedPrior.holdings || [];

  const newPositions = raw.newPositions
    .map((cusip) => lookupCusip(cusip, currHoldings))
    .filter(Boolean)
    .map((h) => ({ cusip: h.cusip, issuerName: h.issuerName, shares: h.shares, valueUsd: h.valueUsd }));

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
  const deltaPct = priorTotalValueUsd === 0 ? 0 : (raw.totalValueUsd - priorTotalValueUsd) / priorTotalValueUsd;

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
}

function findPriorEntry(filerEntry, allFilings) {
  const sameCik = (allFilings || []).filter(
    (e) =>
      e.filerCik === filerEntry.filerCik &&
      (e.periodOfReport || '') < (filerEntry.periodOfReport || ''),
  );
  sameCik.sort((a, b) => {
    const p = (b.periodOfReport || '').localeCompare(a.periodOfReport || '');
    return p !== 0 ? p : (b.latestFilingDate || '').localeCompare(a.latestFilingDate || '');
  });
  return sameCik[0] || null;
}

function lookupCusip(cusip, holdings) {
  return (holdings || []).find((h) => h.cusip === cusip) || null;
}
```

- [ ] **Step 3: 改 scripts/prepare-digest.js:45**

当前 L45 为：

```javascript
  const enriched = f13Filtered.map((f) => periodDiff(f, normalizedFeed));
```

替换为：

```javascript
  // Pass defaultSources.thirteenF so periodDiff's defensive normalizeValueUnits
  // can correctly identify small-fund style prior entries (e.g. tiny CIKs that
  // publish in dollars rather than thousands). Idempotent for already-normalized
  // entries.
  const enriched = f13Filtered.map((f) => periodDiff(f, normalizedFeed, defaultSources.thirteenF));
```

- [ ] **Step 4: 跑 period-diff.test.js 确认 red test 变绿**

Run: `cd /Users/kaden/follow-the-money && npx vitest run tests/enrich/period-diff.test.js`
Expected: **6 tests passed**（5 个原本绿的 + 第 6 个红测试变绿。Task 2 的 2 个新增 test 在下个 task 加完后才会跑到 8/8 pass）。

如果 fail，常见原因：
- `normalizedPrior.holdings` 在小-fund style 下返回 `undefined` → 已被 `|| []` 兜底
- `summary.priorTotalValueUsd` 没拿到 110000000 → 检查 `normalizeValueUnits` 是否调用（应在 L28 之后立即），或检查 `priorHoldings` 引用的是 `normalizedPrior.holdings` 而不是 `priorEntry.holdings`
- `summary.deltaPct` 不是 -0.0909 → 检查 `raw.totalValueUsd`（应是 100000000）和 `priorTotalValueUsd`（应是 110000000），公式 `(100M - 110M) / 110M = -0.0909`

- [ ] **Step 5: 跑 prepare-digest e2e 验证 Baupost 数据**

Run: `cd /Users/kaden/follow-the-money && node scripts/prepare-digest.js --lookback 90 > /tmp/digest-pd.json`
然后：
```bash
node -e "const d=JSON.parse(require('fs').readFileSync('/tmp/digest-pd.json','utf8')); const b=d.thirteenF.find(f=>f.filerName==='Baupost Group' && f.periodOfReport==='2026-03-31'); if(!b){console.log('NOT FOUND'); process.exit(1);} console.log(JSON.stringify({priorTotalValueUsd:b.summary&&b.summary.priorTotalValueUsd, deltaPct:b.summary&&b.summary.deltaPct}, null, 2))"
```

Expected: `priorTotalValueUsd` 量级应在 $10^9~$10^11 范围（与 commit 4d80d3b 之前的现状一致——production 路径不被本次改动影响）。`deltaPct` 是个正负小百分数（不要是 -99.9% 那种失真值）。

如果 `priorTotalValueUsd` 是 6 位数（5M-50M）而不是 9-11 位数（5B-50B），说明 production 路径回归了——回到 Step 2 检查 `prepare-digest.js` 是否还在 L42 调用 `normalizeValueUnits`。

- [ ] **Step 6: Commit（fix）**

Run:
```bash
cd /Users/kaden/follow-the-money && git add lib/enrich/period-diff.js scripts/prepare-digest.js
```

然后：

```bash
cd /Users/kaden/follow-the-money && \
GIT_AUTHOR_NAME=Claude GIT_AUTHOR_EMAIL=claude-fable-5@noreply.anthropic.com \
GIT_COMMITTER_NAME=Claude GIT_COMMITTER_EMAIL=claude-fable-5@noreply.anthropic.com \
git commit --file=- <<'EOF'
fix(period-diff): normalize prior entry units defensively

之前 periodDiff 收到 raw thousands prior 时不会 ×1000，与已 normalize 的
current 一起算 deltaPct 会失真 1000×。生产路径靠 scripts/prepare-digest.js
L42 全局预 normalize 没有触发，但任何绕过的调用方都会中招。

修法：
- periodDiff 加可选第 3 参数 configSources = []
- 拿到 priorEntry 后立刻 normalizeValueUnits（idempotent，对已 normalize
  entry 是 no-op）
- prepare-digest.js 显式传 defaultSources.thirteenF，让小-fund filer 的
  prior 也能被识别

调用方契约：current 由调用方负责（prepare-digest L42 已经预 normalize）。
periodDiff 只防御 prior 这条由 findPriorEntry 反向检索到的路径。

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: 加 2 个新 unit test 覆盖幂等性和 small-fund

**Files:**
- Modify: `tests/enrich/period-diff.test.js`（在文件末尾 describe 块闭合 `})` 之前追加 2 个新 `it(...)`）

**Interfaces:**
- Consumes: Task 1 的新 `periodDiff(filerEntry, allFilings, configSources = [])` 签名
- Produces: 2 个新 test case：`idempotency: leaves prior entry alone when already in dollars` + `small-fund: honors style flag and does not normalize prior`

- [ ] **Step 1: 读 tests/enrich/period-diff.test.js 末尾**

Read `tests/enrich/period-diff.test.js` 最后 10 行（L99-109），确认现有测试用 `baseEntry(cik, period, holdings)` helper，关闭 `describe` 的 `})` 在 line 109。

- [ ] **Step 2: 在 L109（`describe` 闭合 `})` 之前）追加 2 个 test**

在文件 line 108（"normalizes prior entry units to match current" 的 `});`）之后、line 109（`});` 闭合 describe）之前插入以下代码：

```javascript

  it('idempotent: leaves prior entry alone when already normalized to dollars (defense does not double-normalize)', () => {
    // Simulate post-normalizeValueUnits state: sum ≥ $1B → dollars.
    const current = baseEntry('0001061768', '2026-03-31', [
      { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 1000000000, votingAuthority: { sole: 100, shared: 0, none: 0 } },
    ]);
    const prior = baseEntry('0001061768', '2025-12-31', [
      { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 1100000000, votingAuthority: { sole: 100, shared: 0, none: 0 } },
    ]);
    const cfg = [{ cik: '0001061768', name: 'Baupost Group', style: 'value' }];
    const out = periodDiff(current, [current, prior], cfg);
    // valueUsd sum = 1.1B ≥ $1B → normalizeValueUnits should NOT ×1000.
    expect(out.summary.priorTotalValueUsd).toBe(1100000000);
    // deltaPct = (1B - 1.1B) / 1.1B = -0.0909...
    expect(out.summary.deltaPct).toBeCloseTo(-0.0909, 4);
  });

  it('honors small-fund style flag on prior: does not normalize even when sum < $1B', () => {
    // Prior sum < $1B BUT CIK matches small-fund config → should NOT ×1000.
    const current = baseEntry('0001061768', '2026-03-31', [
      { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 30000000, votingAuthority: { sole: 100, shared: 0, none: 0 } },
    ]);
    const prior = baseEntry('0001061768', '2025-12-31', [
      { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 30, votingAuthority: { sole: 100, shared: 0, none: 0 } },
    ]);
    const cfg = [{ cik: '0001061768', name: 'Tiny Filer', style: 'small-fund' }];
    const out = periodDiff(current, [current, prior], cfg);
    // small-fund style → valueUnit: 'unknown' → prior valueUsd stays raw.
    expect(out.summary.priorTotalValueUsd).toBe(30);
  });
```

- [ ] **Step 3: 跑 period-diff.test.js 确认 8/8 pass（含 2 个新增）**

Run: `cd /Users/kaden/follow-the-money && npx vitest run tests/enrich/period-diff.test.js`
Expected: **8 tests passed**（5 个原本绿的 + 1 个红→绿 + 2 个新增）。

如果 fail，常见原因：
- 幂等性测试 fail：`priorTotalValueUsd` 是 1100000000000（说明 ×1000 了） → 检查 `normalizeValueUnits` 在 sum ≥ $1B 时确实走 dollars 分支不 ×1000；或检查 `cfg` 里 `style: 'value'`（不是 'small-fund'，不会被 small-fund 分支误命中）
- small-fund 测试 fail：`priorTotalValueUsd` 是 30000 → 检查 `cfg` 里 `cik: '0001061768'` 与 prior `filerCik: '0001061768'` 完全相等；style === 'small-fund' 走对分支

- [ ] **Step 4: Commit（test）**

Run:
```bash
cd /Users/kaden/follow-the-money && git add tests/enrich/period-diff.test.js
```

然后：

```bash
cd /Users/kaden/follow-the-money && \
GIT_AUTHOR_NAME=Claude GIT_AUTHOR_EMAIL=claude-fable-5@noreply.anthropic.com \
GIT_COMMITTER_NAME=Claude GIT_COMMITTER_EMAIL=claude-fable-5@noreply.anthropic.com \
git commit --file=- <<'EOF'
test(period-diff): cover idempotency and small-fund style prior

修 4d80d3b 文档化的 prior entry units mismatch BUG 后，加 2 个 unit test
防止回归：

1. 幂等性：当 prior entry 的 sum(valueUsd) ≥ $1B（已 normalize dollars 状态）
   时，periodDiff 内部的 normalizeValueUnits 不应再次 ×1000。
2. small-fund：prior entry 的 CIK 命中 cfg style: 'small-fund' 时，
   不会被启发式 "sum<1B → thousands" 误判为 thousands 而 ×1000。

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
```

---

### Task 3: 完整验证（vitest 全量 + prepare-digest e2e + 工作树 clean）

**Files:** 不动文件

**Interfaces:**
- Consumes: Task 1 的 fix、Task 2 的 tests
- Produces: 全量 vitest 通过 + Baupost 数据无回归 + 3 个 commit 落地

- [ ] **Step 1: 跑全量 vitest**

Run: `cd /Users/kaden/follow-the-money && npx vitest run`
Expected: 所有原本绿的 test 仍绿；原 pre-existing failure `tests/integration.test.js > integration: aggregate → digest → alert` 仍然按现状 fail（与本任务无关，本来就 fail）；`tests/enrich/period-diff.test.js` 8/8 全绿。**关键**：之前 commit 4d80d3b 留下的红测试现在绿了，CI 红测试消失。

如果在 Task 1/2 之后反而引入了新 fail，停下来调查——本任务不应该引入新回归。

- [ ] **Step 2: 跑 prepare-digest 验生产路径不被回归**

Run: `cd /Users/kaden/follow-the-money && node scripts/prepare-digest.js --lookback 90 > /tmp/digest-final.json`
然后：
```bash
node -e "const d=JSON.parse(require('fs').readFileSync('/tmp/digest-final.json','utf8')); const b=d.thirteenF.find(f=>f.filerName==='Baupost Group' && f.periodOfReport==='2026-03-31'); if(!b){console.log('NOT FOUND'); process.exit(1);} console.log('Baupost Q1 2026 priorTotalValueUsd:', b.summary && b.summary.priorTotalValueUsd); console.log('Baupost Q1 2026 deltaPct:', b.summary && b.summary.deltaPct);"
```

Expected: `priorTotalValueUsd` 量级 ≥ $10^9（与 Task 1 Step 5 一致）。`deltaPct` 是合理小百分数。

- [ ] **Step 3: 跑 git log 确认 commit 历史**

Run: `cd /Users/kaden/follow-the-money && git log --oneline -6`
Expected: 最近 3 个 commit 分别是：
1. `test(period-diff): cover idempotency and small-fund style prior`（Task 2）
2. `fix(period-diff): normalize prior entry units defensively`（Task 1）
3. `docs(spec): periodDiff units normalization design`（已存在的 spec commit）

- [ ] **Step 4: 跑 git status 确认 working tree 干净**

Run: `cd /Users/kaden/follow-the-money && git status`
Expected: `nothing to commit, working tree clean`。3 个文件改动（`lib/enrich/period-diff.js`, `scripts/prepare-digest.js`, `tests/enrich/period-diff.test.js`）都已经 commit。
