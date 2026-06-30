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