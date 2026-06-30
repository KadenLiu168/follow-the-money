# 13D/G 写法

## 触发
`formType in {SC 13D, SC 13D/A, SC 13G, SC 13G/A}` 且 `filingDate` 在 lookback 窗口内。

## 单条 13D 输出模板（active 投资者，重点写）
### {filerName} 举牌 {issuerName}（{ticker}）

- 持股比例：**{ownershipPercent}%**
- 持股数：{sharesOwned}
- 性质：active 投资（5% 阈值主动披露）
- 来源：[SEC 文件]({primaryDocUrl})

## 单条 13G 输出模板（passive 投资者，简写）
### {filerName} 披露 {issuerName}（{ticker}）{ownershipPercent}% 持仓

- 来源：[SEC 文件]({primaryDocUrl})

## 排序
13D 在前（按 filingDate 降序）；13G 在后（按 filingDate 降序）。

## 13D/A 多条合并
当 `count > 1` 时，追加一行：`修订 {count} 次，{summary}`