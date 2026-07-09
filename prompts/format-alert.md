# Alert 写法

## 触发

由 `check-alerts.js` 产出；每条对应一次 13D 或一次合并后的 13D/A。

## 长度

单条 alert 不超过 80 字（中文）。

## 模板

🚨 **{filerName} 举牌 {issuerName}（{ticker}）**

- 持股：**{ownershipPercent}%**（{sharesOwned} 股）
- {if count > 1: {summary}}
- [SEC 文件]({primaryDocUrl})

## 严格规则

- 用 🚨 开头，不加 emoji 装饰
- 链接必须用 SEC primaryDocUrl
- 软上限超出时，附加 `📊 另 N 条 13D/G 详见 digest` 单行
