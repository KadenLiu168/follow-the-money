## Why

`lib/parsers/thirteen-dg.js` 的 `parseThirteenDG` 对 **HTML 形态**的 13D/G filing（现代 EDGAR 主流形态）输出完全失真：`ownershipPercent` 恒为 `0`、`sharesOwned` 恒为 `1`。这两个字段是 13D/G 告警与 digest 的核心信号（"谁举牌、占比多少、持多少股"），失真会让下游数据彻底错误，而 pipeline 不报错、现有单测也拦不住——因为 fixture 全是 SGML 形态，从未覆盖 HTML 路径。这是 `docs/analysis-vs-follow-builders.md` 中的 **D7**（高严重度）。

## What Changes

- 修复 `pickFirst` 内 SGML 正则的零宽前瞻 bug：当 `stopLabels` 为空时，终止符拼接会退化出始终成立的空分支 `(?:)\b` / `()`，导致懒惰捕获组在第一个数字后即停。改为**仅当 `stopLabels` 非空时才拼入该终止分支**。
- 新增 `toNumber(raw)` 数值清洗 helper，仅用于 `ownershipPercent` 与 `sharesOwned`：剥离 `%`、逗号、尾随文本等非数字字符，取第一个数字 token。解决百分比带 `%` 后缀（`Number("6.8%")` = NaN → 0）的问题，并对 HTML 后续文本过度捕获做兜底。
- 新增一个 **HTML 形态** fixture（`tests/fixtures/13d-html-shape.html`）与对应单元测试，确定性地断言 `ownershipPercent === 6.8 && sharesOwned === 1234567`，补上长期缺失的测试护栏。

## Capabilities

### New Capabilities
- `thirteen-dg-parsing`: `parseThirteenDG` 对 SGML 与 HTML 两种 EDGAR 形态的 13D/G filing，都必须正确解析出 `issuerName`、`issuerTicker`、`ownershipPercent`、`sharesOwned`、`intent`。

### Modified Capabilities
<!-- 无既有 capability 的需求变更 -->

## Impact

- 代码：`lib/parsers/thirteen-dg.js`（`pickFirst` 正则构造 + 新增 `toNumber` + 两处数值字段改用 `toNumber`）。
- 测试：`tests/parsers/thirteen-dg.test.js` 新增 HTML 形态用例；新增 `tests/fixtures/13d-html-shape.html`。
- 依赖/API：无。`parseThirteenDG` 的函数签名与返回结构不变，仅修正错误值。现有 SGML fixture 断言不受影响（非空 `stopLabels` 调用行为不变；AGGREGATE 调用从错误 `"1"` 修正为正确数值）。
