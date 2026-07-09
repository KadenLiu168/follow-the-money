# 13F 修订披露渲染规则 — 设计

**日期**：2026-07-03
**作者**：brainstorming session with user
**状态**：已批准，待 writing-plans

## 背景

`scripts/prepare-digest.js` 用 `latestFilingDate >= cutoff` 过滤 13F 条目，意味着迟交的修订（如 Coatue Q4 2025 13F-HR/A 在 2026-05-15 提交）会被纳入当期 digest。当前 `prompts/format-13f.md` 没有处理修订场景，渲染时容易让读者误以为这是当前 quarter 的常规披露。

实测数据：Coatue Management LLC Q4 2025 entry

- `latestFormType`: `13F-HR/A`
- `history[0]`: 2026-02-17 13F-HR（原披露）
- `history[1]`: 2026-05-15 13F-HR/A（修订）

## 目标

让所有未来渲染者（人或 LLM agent）都能一眼看出"这是 13F 修订披露"，避免误读为当前 quarter 常规披露。

## 非目标

- 不在 aggregator / schema / 其他代码层加结构化字段
- 不计算 amendment 前后 diff（超出"防误解"范围）
- 不处理 13D/A、13G/A（属 `prompts/format-13dg.md` 范围，YAGNI）
- 不改变非修订场景的输出格式

## 改动范围

**唯一改动**：`prompts/format-13f.md`（新增约 15 行规则）

**不动**：

- `lib/aggregate/pipeline-a.js`
- `lib/store/feed-json.js`（`upsert13FFiling` 的 history 合并逻辑已经够用）
- `feed-13f.json` schema
- 其他 prompt 文件

**新增**（仅验证用）：

- `tests/scripts/prepare-digest-amendment.test.js` — e2e 测试，验证 aggregator 输出包含 amendment 字段（见"验证"章节）

## 设计

### 触发条件

`latestFormType.endsWith('/A')` 视为修订。这样：

- `13F-HR` → 常规
- `13F-HR/A` → 修订
- 未来出现 `13F-HR/A/A` 等多级修订也自动覆盖

### Section title 格式

| 场景 | 格式                                                                                 |
| ---- | ------------------------------------------------------------------------------------ |
| 常规 | `### {filerName}（Q{N} {periodOfReport 年份}）`                                      |
| 修订 | `### {filerName}（Q{N} {periodOfReport 年份} 修订，原披露 {history[0].filingDate}）` |

`Q{N}` 直接用映射表：03=Q1、06=Q2、09=Q3、12=Q4。**prompt 模板里必须列出这张表，不让 LLM 自行推导**。

`history[0].filingDate` 已经是原始 filing 日期 —— 已在 Coatue Q4 2025 实测确认。

### 主体内容新增一行

在 13F 段的"总持仓"行之前加一行表单类型标注：

```
- 表单类型：{latestFormType}（第 {N-1} 次修订，最新披露 {latestFilingDate}）
```

N = `history.length`

- `history.length === 1`（常规）→ 跳过整行
- `history.length === 2`（1 次修订）→ `第 1 次修订`
- `history.length === 3`（2 次修订）→ `第 2 次修订`

### 多次修订

按 `history.length` 自然处理。section title 中的"原披露"始终是 `history[0].filingDate`，主体中的"最新披露"始终是 `history[history.length-1].filingDate`（即 `latestFilingDate`）。

## 实际输出示例

### 修订披露

```
### Coatue Management LLC（Q4 2025 修订，原披露 2026-02-17）

- 表单类型：13F-HR/A（第 1 次修订，最新披露 2026-05-15）
- 持仓：260 只，价值 **$399.63 亿**，环比 **-2.0%**
...
```

### 常规披露

```
### Berkshire Hathaway Inc（Q1 2026）

- 持仓：90 只，价值 **$2630.96 亿**，环比 **-4.0%**
...
```

## 边界情况

| 情况                   | 行为                                       |
| ---------------------- | ------------------------------------------ |
| `history.length === 1` | 跳过表单类型行                             |
| `history.length === 2` | "第 1 次修订"                              |
| `history.length >= 3`  | "第 N-1 次修订"，不展开中间过程            |
| `history` 字段缺失     | 视为 `length === 1`（按 `?? []` fallback） |
| `latestFormType` 缺失  | 视为常规（template 上不应发生）            |

## 验证

### 自动化

由于 prompt 模板是给 LLM 用的，传统的 unit test 不好测。建议在 `tests/scripts/` 加一个 e2e：

1. 构造一个 fixture feed-13f.json，包含一个 13F-HR/A entry（用 Coatue Q4 2025 数据）
2. 跑 `node scripts/prepare-digest.js --lookback 90`，断言输出的 JSON 包含 `latestFormType: "13F-HR/A"` 和 `history.length === 2`
3. （可选）人工检查 LLM 渲染产物包含"修订"字样 —— 这一步不进 CI

### 手动

1. 重跑 `node scripts/fetch-feed.js && node scripts/prepare-digest.js`
2. 喂给 LLM 渲染
3. 验证 Coatue Q4 2025 段 section title 包含"修订，原披露 2026-02-17"
4. 验证其他 7 个 filers section title 不包含"修订"字样

## 风险

| 风险                              | 缓解                                                              |
| --------------------------------- | ----------------------------------------------------------------- |
| LLM 不严格遵循模板                | 在模板里用 `must` / `务必` 强化；考虑在 evals 里加 fixture        |
| 未来 prompt 模板被改回            | 提一条 .editorconfig 风格的 review 规则或 doc comment             |
| periodOfReport 月份推导 Q{N} 写错 | 用 `periodOfReport.slice(5,7)` 映射到 Q1–Q4；模板里直接列出映射表 |
| history 字段未来 schema 变化      | 修改成本低（聚合器控制）                                          |

## 后续可能扩展（不在本期）

- 13D/A、13G/A 修订处理（format-13dg.md）
- 多次修订时展开中间过程（如"2026-02-17 → 2026-05-15 → 2026-06-10 共 2 次修订"）
- aggregator 加 `isAmendment` / `amendmentCount` 结构化字段，给非 LLM 渲染 pipeline 用
