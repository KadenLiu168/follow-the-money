# 13F Amendment Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `prompts/format-13f.md` 加修订披露（13F-HR/A）渲染规则，让 LLM 渲染产物显式标注"这是修订、原披露日期 X"。

**Architecture:** 唯一产品代码改动是 prompt 模板加规则。数据层（`latestFormType` + `history[]`）已经够用，由 aggregator 与 `upsert13FFiling` 在写入时自动维护。e2e 测试断言数据层字段透传，prompt 渲染走 manual checklist。

**Tech Stack:** Node 20+, vitest 2.x, Markdown prompt 模板

## Global Constraints

- 不动 `lib/aggregate/pipeline-a.js`、`lib/store/feed-json.js` 或 `feed-13f.json` schema
- 不动其他 prompt 文件（`digest-intro.md` / `format-13dg.md` / `format-alert.md` / `translate.md`）
- 不为修订场景算 diff（amendment 前后 holdings 变化）—— YAGNI，超出"防误解"范围
- 修订触发条件：`latestFormType.endsWith('/A')` —— 覆盖未来 `13F-HR/A/A` 等多级修订
- 季度由 `periodOfReport` 月份映射：03→Q1、06→Q2、09→Q3、12→Q4；prompt 模板里必须**显式列出**这张表，不让 LLM 推理
- 所有 commit message 用中文
- 任何 commit 不允许 push（per session 规则）

---

### Task 1: 写 e2e 测试验证 amendment 字段透传

**Files:**
- Modify: `tests/scripts/prepare-digest.test.js:130` (在文件末尾追加新 test block)

**Interfaces:**
- Consumes: 现有 `tests/scripts/prepare-digest.test.js` 的 e2e 模式（execSync 跑 `node scripts/prepare-digest.js`，断言 JSON 字段）
- Produces: 新 test case "exposes latestFormType and history for amendment entries (Coatue Q4 2025 13F-HR/A)"

- [ ] **Step 1: 读现有 test 文件尾部结构**

Read `tests/scripts/prepare-digest.test.js` 最后 5 行（line 125-130），确认现有 test 是 `it('...', async () => { ... })` 结构，最后用 `})` 闭合 `describe` 块。模式是 `import { mkdtempSync, ... } from 'node:fs'`，新 test 不需要新 import。

- [ ] **Step 2: 在 describe 块闭合 `})` 之前追加新 test**

在 `tests/scripts/prepare-digest.test.js` 第 128 行的 `});` 之后、第 129 行的 `});`（describe 闭合）之前，**插入**以下代码（与现有 test 风格一致——顶层 `it` 直接调 `execSync`）：

```javascript
  it('exposes latestFormType=13F-HR/A and history[] for amendment entries (Coatue Q4 2025)', () => {
    const cwd = join(__dirname, '..', '..');
    const out = execSync('node scripts/prepare-digest.js --lookback 90', { cwd, encoding: 'utf8' });
    const j = JSON.parse(out);
    // Find Coatue's Q4 2025 amendment entry (periodOfReport=2025-12-31, filed 2026-05-15)
    const coatueQ4 = j.thirteenF.find(
      (f) => f.filerName === 'Coatue Management LLC' && f.periodOfReport === '2025-12-31'
    );
    expect(coatueQ4).toBeDefined();
    expect(coatueQ4.latestFormType).toBe('13F-HR/A');
    expect(coatueQ4.latestFilingDate).toBe('2026-05-15');
    expect(Array.isArray(coatueQ4.history)).toBe(true);
    expect(coatueQ4.history.length).toBe(2);
    // history[0] must be the original 13F-HR filing (2026-02-17), history[1] the amendment
    expect(coatueQ4.history[0].formType).toBe('13F-HR');
    expect(coatueQ4.history[0].filingDate).toBe('2026-02-17');
    expect(coatueQ4.history[1].formType).toBe('13F-HR/A');
    expect(coatueQ4.history[1].filingDate).toBe('2026-05-15');
  });
```

- [ ] **Step 3: 跑新 test 验证它**已经通过**（数据层早就透传，预期 PASS）**

Run: `cd /Users/kaden/follow-the-money && npx vitest run tests/scripts/prepare-digest.test.js`
Expected: PASS — 所有 8 个 test 全过（含新增）。这一步确认数据层已经满足后续 prompt 模板的输入要求。

- [ ] **Step 4: Commit**

Run:
```bash
cd /Users/kaden/follow-the-money && git add tests/scripts/prepare-digest.test.js
```
然后用 heredoc 提交：
```bash
cd /Users/kaden/follow-the-money && \
GIT_AUTHOR_NAME=Claude GIT_AUTHOR_EMAIL=claude-fable-5@noreply.anthropic.com \
GIT_COMMITTER_NAME=Claude GIT_COMMITTER_EMAIL=claude-fable-5@noreply.anthropic.com \
git commit --file=- <<'EOF'
test(prepare-digest): 验证 amendment 字段透传

Coatue Q4 2025 13F-HR/A 修订（filed 2026-05-15）应保留完整 history 链：
- history[0] = 2026-02-17 13F-HR（原披露）
- history[1] = 2026-05-15 13F-HR/A（修订）
- latestFormType = 13F-HR/A
- latestFilingDate = 2026-05-15

为后续 format-13f.md 修订渲染规则提供数据基础。

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: 改 prompts/format-13f.md 加修订规则

**Files:**
- Modify: `prompts/format-13f.md` (在"单个基金 13F 输出模板"之前插入"修订披露"段)

**Interfaces:**
- Consumes: 现有 prompt 模板结构（"## 触发" / "## 单个基金 13F 输出模板" / "## 排序" / "## 简化规则"）
- Produces: 新增"## 修订披露（13F-HR/A）"段，含触发条件、section title 格式、主体新增行

- [ ] **Step 1: 读 prompts/format-13f.md 全文**

Read `prompts/format-13f.md`，确认当前 24 行结构：`# 13F 写法` → `## 触发` → `## 单个基金 13F 输出模板` → `## 排序` → `## 简化规则`。

- [ ] **Step 2: 在"## 简化规则"段之后**追加新段

用 Edit 工具，把以下代码追加到 `prompts/format-13f.md` 末尾（line 24 之后）：

```markdown
## 修订披露（13F-HR/A）

### 触发
`latestFormType` 以 `/A` 结尾时（即 `13F-HR/A` 或未来多级修订如 `13F-HR/A/A`），按本节规则输出。

### 字段说明
- `latestFormType`：当前 entry 的最新表单类型
- `latestFilingDate`：当前 entry 的最新披露日期
- `history[]`：完整披露链，按时间顺序；`history[0]` 是原始披露，`history[history.length-1]` 是最新披露
- `N = history.length`

### Section title 格式
- 常规：`### {filerName}（Q{N} {periodOfReport 年份}）`
- 修订：`### {filerName}（Q{N} {periodOfReport 年份} 修订，原披露 {history[0].filingDate}）`

### 季度映射（必须使用本表，不推理）
- periodOfReport 月份 `03` → Q1
- periodOfReport 月份 `06` → Q2
- periodOfReport 月份 `09` → Q3
- periodOfReport 月份 `12` → Q4
其他月份视为数据异常，跳过该 entry 并在 digest 末尾注明。

### 主体新增行
在"总持仓"行之前**必须**插入：
- `history.length === 1`（常规）：跳过
- `history.length >= 2`（含修订）：`- 表单类型：{latestFormType}（第 {N-1} 次修订，最新披露 {latestFilingDate}）`

### 示例
修订披露：
```
### Coatue Management LLC（Q4 2025 修订，原披露 2026-02-17）

- 表单类型：13F-HR/A（第 1 次修订，最新披露 2026-05-15）
- 总持仓：260 只，价值 **$399.63 亿**
...
```

常规披露（保持原样）：
```
### Berkshire Hathaway Inc（Q1 2026）

- 总持仓：90 只，价值 **$2630.96 亿**
...
```
```

- [ ] **Step 3: 视觉检查修改结果**

Read `prompts/format-13f.md` 全文，确认：
- 原 4 段（"## 触发" / "## 单个基金 13F 输出模板" / "## 排序" / "## 简化规则"）完整保留
- 新增"## 修订披露（13F-HR/A）"段在文件末尾
- 季度映射表存在且完整
- 示例段使用 ``` 代码块包裹

- [ ] **Step 4: Commit**

Run:
```bash
cd /Users/kaden/follow-the-money && git add prompts/format-13f.md
```
然后用 heredoc 提交：
```bash
cd /Users/kaden/follow-the-money && \
GIT_AUTHOR_NAME=Claude GIT_AUTHOR_EMAIL=claude-fable-5@noreply.anthropic.com \
GIT_COMMITTER_NAME=Claude GIT_COMMITTER_EMAIL=claude-fable-5@noreply.anthropic.com \
git commit --file=- <<'EOF'
docs(format-13f): 加修订披露渲染规则

Coatue Q4 2025 13F-HR/A 修订在 2026-05-15 提交，会被 prepare-digest 90 天
lookback 纳入当期 digest。当前模板没有修订处理，渲染时容易让读者
误以为是常规披露。

新增：
- 触发条件：latestFormType 以 /A 结尾
- Section title 加"修订，原披露 history[0]"标注
- 主体加"表单类型"行，含修订次数和最新披露日期
- 季度映射表显式列出，不让 LLM 推理

不动：aggregator / store / schema / 其他 prompt 文件

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
```

---

### Task 3: 完整验证（vitest + manual e2e）

**Files:** 不动文件

**Interfaces:**
- Consumes: Task 1 的 e2e test、Task 2 的 prompt 模板
- Produces: 全量测试报告 + 手动渲染检查清单

- [ ] **Step 1: 跑全量 vitest 确认无回归**

Run: `cd /Users/kaden/follow-the-money && npx vitest run`
Expected: 所有 test PASS。`prepare-digest.test.js` 9 个 test 全过（含 Task 1 新增的 amendment test）。

- [ ] **Step 2: 跑一次 prepare-digest 验证数据没变**

Run: `cd /Users/kaden/follow-the-money && node scripts/prepare-digest.js --lookback 90 > /tmp/digest-amend.json`
然后 `node -e "const d=require('/tmp/digest-amend.json'); const c=d.thirteenF.find(f=>f.filerName==='Coatue Management LLC' && f.periodOfReport==='2025-12-31'); console.log(JSON.stringify({latestFormType:c.latestFormType, latestFilingDate:c.latestFilingDate, historyLen:c.history.length, history0:c.history[0], history1:c.history[1]}, null, 2))"`
Expected: 输出 JSON 包含 `latestFormType: "13F-HR/A"`、`history.length: 2`、两个 history 项（2026-02-17 13F-HR + 2026-05-15 13F-HR/A）。

- [ ] **Step 3: 手动检查 LLM 渲染产物**

把 `/tmp/digest-amend.json` 喂给 LLM，并附 `prompts/digest-intro.md` + `prompts/format-13f.md`（含 Task 2 新增段）+ `prompts/translate.md`，按 skill 描述的标准流程渲染。检查渲染产物里：
- Coatue Q4 2025 段 section title 是 `### Coatue Management LLC（Q4 2025 修订，原披露 2026-02-17）` ✓
- Coatue Q4 2025 段在"总持仓"之前有 `- 表单类型：13F-HR/A（第 1 次修订，最新披露 2026-05-15）` ✓
- 其他 7 个 filer section title 不含"修订"字样 ✓
- 其他 7 个 filer 主体不含"表单类型"行 ✓
- 整体 digest 仍控制在 800 字以内 ✓

如果任一项不符，回到 Task 2 调整 prompt 模板措辞（"必须" / "务必" 强化、示例重写等），重跑 Step 1-3。

- [ ] **Step 4: 跑 `git log --oneline` 确认 commit 历史**

Run: `cd /Users/kaden/follow-the-money && git log --oneline -5`
Expected: 最近 2 个 commit 是 Task 1 和 Task 2 留下的。

- [ ] **Step 5: 跑 `git status` 确认 working tree 干净**

Run: `cd /Users/kaden/follow-the-money && git status`
Expected: `nothing to commit, working tree clean`。spec 文件和实施文件都已 commit。
