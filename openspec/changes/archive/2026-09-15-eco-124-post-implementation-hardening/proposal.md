## Why

ECO-124 已实现 SEC 13F 与 CFTC COT semantic evidence，但其最关键的完整性、确定性与 fail-closed 边界需要由更直接的 post-implementation regression coverage 固化。当前 accepted contract 已明确这些行为，因此本 Change 只验证并加固实现，不扩大或改写产品能力。

## What Changes

- 为 SEC filing selection 增加明确回归覆盖：只接受 exact `13F-HR`，忽略更新的 `13F-HR/A`，仅有 amendment 时 fail closed，并证明输入排序不影响选择结果。
- 为 SEC complete Provider slice 增加端到端 snapshot regression：单家公司变化时仍发布全部 configured watched companies；任何 company acquisition 缺失都产生 partial/failed outcome 且禁止发布。
- 为 CFTC v2 acquisition 增加超过 100 markets、分页分组/交付顺序变化和缺页失败的回归覆盖，证明 current/previous report universe 完整、确定且不可截断。
- 仅在 regression test 暴露现有实现违约时，于 SEC selection/acquisition completeness 或 CFTC acquisition pagination 的责任层做最小修复。
- 明确禁止在 `snapshot.py` 增加 company-level merge，禁止 ECO-125 abstraction、editorial logic、ranking、Digest 改动或任何 LLM/analysis 能力。

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. 本 Change 固化并验证 accepted `feed-evidence-pipeline` requirements，不改变 externally observable contract；因此 `.openspec.yaml` 设置 `skip_specs: true`。

## Impact

- 主要测试：`tests/test_sec_13f.py`、新增 `tests/test_sec_snapshot_slice.py`、`tests/test_cftc_cot.py`，以及必要时现有 adapter/integration test support。
- 条件性生产修改仅限 `src/follow_the_money/providers/sec_13f.py`、`src/follow_the_money/providers/adapters.py` 或 SEC acquisition completeness 的既有 orchestration/validation seam；CFTC 修复限于现有 deterministic pagination seam。
- `src/follow_the_money/feed/snapshot.py` 的 whole-Provider-slice replacement contract 不变，不引入 per-company merge 或历史数据库语义。
- 无 schema、Feed domain、Provider set、public API、dependency、credential、Host-Agent 或 Digest contract 变化。
