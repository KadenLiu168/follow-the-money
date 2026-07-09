# 13F 写法

## 触发

`formType in {13F-HR, 13F-HR/A}` 且 `latestFilingDate` 在 lookback 窗口内。

## 单个基金 13F 输出模板

### {filerName}（Q1/Q2/Q3/Q4 {periodOfReport 年份}）

- 总持仓：{totalHoldingsCount} 只，价值 **${totalValueUsd 亿/M}**
- 新进：{newPositions.length} 只
- 清仓：{closedPositions.length} 只
- 加仓：{increasedPositions} 只
- 减仓：{decreasedPositions} 只

前 5 大持仓：

1. {issuerName}（{cusip}）— **{shares}** 股，价值 **${valueUsd 亿/M}**
2. ...（按 valueUsd 降序）

## 排序

fund 间按 `totalValueUsd` 降序。

## 简化规则

- 仅当 `newPositions` / `closedPositions` 非空时才列具体 cusip；否则只写计数。
- 单只基金持仓 ≤ 5 只时全部列出。

## 修订披露（13F-HR/A）

### 触发

`latestFormType` 以 `/A` 结尾时（即 `13F-HR/A` 或未来多级修订如 `13F-HR/A/A`），按本节规则输出。

### 字段说明

- `latestFormType`：当前 entry 的最新表单类型
- `latestFilingDate`：当前 entry 的最新披露日期
- `history[]`：完整披露链，按时间顺序；`history[0]` 是原始披露，`history[history.length-1]` 是最新披露
- `N = history.length`

### 边界处理

- `history` 字段缺失或非数组：按 `length === 1` 处理（跳过表单类型行）。
- `latestFormType` 字段缺失或不以 `/A` 结尾：按常规披露处理（不应用本节规则）。

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
