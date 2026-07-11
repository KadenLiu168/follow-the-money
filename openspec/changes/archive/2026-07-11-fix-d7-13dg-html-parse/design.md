## Context

`parseThirteenDG(html, { formType })` 解析 EDGAR 13D/G 主文档（已抓取为 HTML 字符串）。EDGAR 上此类文档有两种形态：

- **SGML 形态**（旧/部分）：`<PERCENT OF CLASS>6.8</PERCENT OF CLASS>` —— 值夹在开闭标签间。
- **HTML 形态**（现代主流）：`<p>Percent of Class<br>6.8%</p><p>Aggregate Amount Beneficially Owned<br>1,234,567</p>` —— 标签 + 文本，无 SGML 闭合标签。

`stripTags` 把两种都拍平成纯文本后，`pickFirst` 用一套正则去抓"标签后、直到终止符"的值。当前实现有两个缺陷，只在对 HTML 形态解析时暴露：

1. `parseThirteenDG` 对百分比直接 `Number(pickFirst(...) || '0')`。HTML 形态下 `pickFirst` 的捕获类不含 `%`，且 `%` 卡在数值与 stop label 之间，导致 SGML 匹配失败返回 `null` → `Number(null || '0')` = `0`（持股比例失真）。
2. `pickFirst` 的 SGML 正则把 `stopLabels` 直接 `join('|')` 拼进前瞻；当 `stopLabels` 为空数组时，该分支退化成 `(?:)\b`（空非捕获组 + 单词边界），这是**永远成立**的零宽匹配。懒惰捕获组在拿到第一个字符后前瞻即满足，于是 `"1,234,567"` 只抓出 `"1"`。AGGREGATE 调用恰好没传 `stopLabels`，因此受害。

现有测试（SGML fixture + 依赖网络的真实 HTML 测试）从未覆盖"HTML 形态 + 断言数值"，故 D7 长期漏网。

## Goals / Non-Goals

**Goals:**
- HTML 形态 13D/G 的 `ownershipPercent`、`sharesOwned` 解析正确。
- `pickFirst` 正则对任意 `stopLabels`（含空）都不产生零宽退化分支。
- 补一个确定性 HTML 形态测试护栏，使 D7 无法复发。

**Non-Goals:**
- 不重构 `parseThirteenDG` 的整体解析架构（SGML/HTML 双路径保留）。
- 不改动 `issuerName` / `issuerTicker` 等文本字段的返回逻辑。
- 不联动 D8（告警去重）、D9（pipeline-a 前一期基准）。
- 不改 `parseThirteenDG` 的函数签名或返回结构。

## Decisions

**D1 — 两处修复必须成对，缺一不可**
- *为什么*：仅加 `toNumber` 不够——`pickFirst` 因零宽 bug 返回的是 `"1"`，`toNumber("1")` 仍为 `1`，救不回 `"1,234,567"`。必须先修正则让 `pickFirst` 至少返回完整数字 token，再用 `toNumber` 兜底 `%` 与尾随文本。
- *为什么还要改捕获类*：百分比值形如 `"6.8%"`，`%` 不在原捕获类 `[A-Za-z0-9.,'\-\s]` 中，导致 `pickFirst` 抓到 `"6.8"` 后前瞻被 `%` 挡住、够不到后续的 stop label（如 `AGGREGATE AMOUNT BENEFICIALLY OWNED`），整条 SGML 匹配失败、返回 `null`，`toNumber(null)` 仍得 `0`。因此捕获类须接纳 `%`（`[A-Za-z0-9.,'%\-...]`），让 `pickFirst` 能返回 `"6.8%"`，再由 `toNumber` 提取 `6.8`。文本字段值不含 `%`，此改动无副作用。
- 正则修法：把终止符候选按条件拼装，空 `stopLabels` 时直接不拼该分支，避免留下空的 `(?:)` / `()`：
  ```js
  const alts = [
    `\\s*/\\s*(?:${closeLabels.join('|')})\\b`, // 闭合标签终止（SGML）
    `\\s*\\(`,                                   // 括号终止
    stopLabels.length ? `\\s*(?:${stopLabels.join('|')})\\b` : null, // 仅非空
    `$`,
  ].filter(Boolean);
  const sgmlRe = new RegExp(`\\b${label}\\b[:.,;()\\-\\s]+([A-Za-z0-9.,'%\\-\\s]+?)(?=${alts.join('|')})`, 'i');
  ```
- `toNumber` 取第一个数字 token，同时处理 `%` / 逗号 / 尾随文本：
  ```js
  function toNumber(raw) {
    const m = String(raw ?? '').match(/[\d,]+(?:\.\d+)?/);
    if (!m) return 0;
    const n = Number(m[0].replace(/,/g, ''));
    return Number.isFinite(n) ? n : 0;
  }
  ```

**D2 — 影响面收敛到单调用点**
- 当前只有 AGGREGATE 这一处传了空 `stopLabels`；其余调用（issuerName / ticker / percent）都有显式 stop，正则改动对它们**零行为变化**。SGML fixture 现有断言全部保留。
- `toNumber` 仅用于 `ownershipPercent` 与 `sharesOwned` 两处，文本字段仍返回 `pickFirst` 原始字符串。

**D3 — 用合成 HTML fixture 而非依赖网络**
- 真实 EDGAR 网络测试（L43）在 SEC 不可达时 skip，不可靠。新增 `tests/fixtures/13d-html-shape.html`（结构对齐真实 Newegg 样本），断言确定性，瞬间跑完，作为主护栏。
- 网络测试保留为 best-effort，不依赖它兜底。

## Risks / Trade-offs

- [Risk] `toNumber` 对极端值 `<1%` 会取 `1` → Mitigation：罕见边缘，本 change 不特殊处理；如后续需要可在 `toNumber` 内加 `<` 解析，但当前属过度工程。
- [Risk] 正则改动无意影响其他 `pickFirst` 调用 → Mitigation：仅空 `stopLabels` 行为改变，而唯一空 `stopLabels` 调用正是要修的 AGGREGATE；非空调用拼接结果与改动前逐字符一致。
- [Risk] HTML 形态文档在持股数后还跟 "Shared Voting Power..." 等字段 → Mitigation：`toNumber` 只抽第一个数字 token，过度捕获被兜底。
