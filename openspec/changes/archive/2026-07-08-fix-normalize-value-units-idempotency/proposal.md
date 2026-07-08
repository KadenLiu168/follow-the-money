## Why

`normalizeValueUnits` 的注释与多个 caller 都声称它是幂等的，但实际行为并非如此：函数在输入端不读自己输出的 `valueUnitAdjusted` 标记，对原始合计 < $1M 的 filer 第二次调用会再次进入 `sum < $1B` 分支，把每条 holding 的 `valueUsd` 再乘 1000。`prepare-digest.js` 先对整份 feed 归一化一次，又把已归一化的 prior entry 喂给 `periodDiff`，后者在 `period-diff.js:33` 触发第二次归一化。

真实数据复现：ARK 2017-06-30 prior（raw sum $513,594）经两次归一化后 prior 总值从 $513,594,000 膨胀到 $513,594,000,000；与 2017-09-30 current ($819,306,000) 配对后真实 `deltaPct` 为 +59.52%，污染后为 -99.84%（符号翻）。该 bug 在默认 `--lookback 90` 下因近期 filer raw sum 都 ≥ $1B 而不显式触发，但 `valueUnitAdjusted` 标记长期形同虚设、`normalizeValueUnits` 契约与实现不一致，下一个新增的小 filer 或拉长 lookback 都会重新暴露。

## What Changes

- 让 `normalizeValueUnits` 真正幂等：在函数顶部加守卫，输入 `valueUnitAdjusted === true` 时直接返回，不再重新进入 `sum < $1B` 分支。
- 在 `tests/enrich/normalize-value-units.test.js` 新增一个 raw sum < $1M 的二次调用回归测试，覆盖当前测试矩阵的盲区。
- 同步更新 `lib/enrich/normalize-value-units.js` 文件头注释，把"幂等"与"已归一化标记"的契约写明；`period-diff.js` 与 `prepare-digest.js` 的 caller 侧注释里"idempotent, so this is a no-op"的描述改为引用新 spec，使文档与实现不再脱节。
- 新增 spec `value-units-normalization`，把幂等性、`valueUnitAdjusted` 标记语义、`valueUnit` 三态（`dollars` / `thousands` / `unknown`）作为正式需求落档。

## Capabilities

### New Capabilities

- `value-units-normalization`: SEC 13F feed valueUsd 单位归一化契约——明确 `normalizeValueUnits` 的输入/输出契约、幂等性、`valueUnitAdjusted` 作为"已归一化"标记的语义，以及 `valueUnit` 的三种合法取值。

### Modified Capabilities

（无。现存 `delivery` spec 与本议题无关。）

## Impact

- 受影响代码：
  - `lib/enrich/normalize-value-units.js`（加守卫、扩注释）
  - `lib/enrich/period-diff.js`（注释引用新 spec，行为不变）
  - `scripts/prepare-digest.js`（注释引用新 spec，行为不变）
  - `tests/enrich/normalize-value-units.test.js`（新增 raw < $1M 回归测试）
- 不影响：
  - 13DG feed 路径、`compute13FSummary`、聚合/告警脚本
  - 公开 API（`normalizeValueUnits` 与 `periodDiff` 签名不变；新增 spec 是新增而非变更）
  - `feed-13f.json`（不修改数据）
- 回滚策略：单一函数顶部守卫，revert 该行即恢复旧行为。