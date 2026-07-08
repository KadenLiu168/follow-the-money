## Context

`lib/enrich/normalize-value-units.js` 在文件头注释里说明 SEC 13F `<value>` 字段单位不一致（多数 filer 是美元、少数如 Baupost 是千美元），通过对 raw holdings 求和判定：sum < $1B → 当作千美元、×1000、标 `valueUnitAdjusted: true`；sum ≥ $1B → 当作美元、不动。

`scripts/prepare-digest.js` 在 line 42 对整份 feed 跑一次 `normalizeValueUnits` 形成 `normalizedFeed`；再在 line 49 把 `normalizedFeed` 喂给 `periodDiff`。`lib/enrich/period-diff.js` 在 line 33 对从 `normalizedFeed` 取出的 prior entry 再调一次 `normalizeValueUnits`，并以"函数幂等"为由认为这是 no-op。

但函数实际并不幂等：它只在输出侧写 `valueUnitAdjusted: true`，输入侧从不读这个字段。当 prior entry 的 raw sum < $1M 时，第一次调用把它乘到 raw × 1000，第二次调用看到的 sum 仍 < $1B，于是再次 ×1000，holistic 效果是 raw × 1,000,000。`period-diff.js:54` 用此 holdings 算 `priorTotalValueUsd`、`period-diff.js:55` 用它算 `deltaPct`，两值都被污染。

复现实测（ARK 2017-09-30 current vs 2017-06-30 prior）见 proposal.md 的"为什么"。`tests/enrich/period-diff.test.js:110` 的"idempotent"用例 prior sum 是 $1.1B，刚好踩 ≥$1B 短路分支，未覆盖 < $1M 区间，掩盖了 bug。

## Goals / Non-Goals

**Goals:**
- 让 `normalizeValueUnits` 的实现与其被声称的"幂等"契约一致。
- 把 `valueUnitAdjusted: true` 提升为有意义的"已归一化"标记，函数必须读它。
- 修掉 `period-diff.js:33` 的二次归一化路径产生的 ×1,000,000 污染。
- 在测试矩阵中显式覆盖 raw sum < $1M 的二次调用场景。
- 把幂等性和标记语义以 spec 形式落档，防止契约再次漂移。

**Non-Goals:**
- 不改 `normalizeValueUnits` 的公开签名。
- 不重构 13F 解析/单位检测逻辑（仍是 sum-vs-$1B 启发式）。
- 不改 `prepare-digest.js` / `period-diff.js` 的调用顺序（仍允许两处 normalize 调用，由幂等性保证正确）。
- 不修改 `feed-13f.json` 或任何已落档数据。
- 不引入新依赖。

## Decisions

### Decision 1: 守卫位置 = 函数顶部，输入侧读 `valueUnitAdjusted`

在 `normalizeValueUnits` 函数体第一行（`const entry = { ...filerEntry };` 之后、`explicitlySmall` 判定之前）加入：

```js
if (entry.valueUnitAdjusted === true) {
  return entry;
}
```

**理由**：修根因。`valueUnitAdjusted` 字段已经存在且语义正好就是"我已被归一化"，但函数从未读过它。把它从"输出标记"提升为"输入也认的标记"，代价是单行 if。

**替代方案考虑**：
- 仅在 `thousands` 分支末尾加守卫（`if (entry.valueUnitAdjusted) return entry;`）→ 较窄，但要求 `dollars` 分支天然幂等（已成立，因为 sum ≥ $1B 时 holdings 不变）；首选这种**位置更靠后**的写法，避免对 small-fund 路径产生意外短路。
- 删除 `period-diff.js:33` 的防御调用 → 改症状，破坏 `period-diff` 对 raw prior 的独立可用性，并使 `tests/enrich/period-diff.test.js:86` 的"normalizes prior entry units"用例失效。
- 给 `normalizeValueUnits` 加 `options.alreadyNormalized` 入参 → API 噪音更大，且 caller 都得改；违背"非破坏"约束。

最终选**只在 `thousands` 分支末尾加守卫**——保留对 `dollars` 分支"自然幂等"的依赖（已经成立），但**显式**记录 `valueUnitAdjusted: true` 输入的早退路径：

```js
// Heuristic:
if (explicitlySmall) return { ...entry, valueUnit: 'unknown' };

// Idempotency guard: prior entry already passed through this function.
if (entry.valueUnitAdjusted === true) return entry;

const sum = ...;
if (sum === 0 || sum >= ONE_BILLION) return { ...entry, valueUnit: 'dollars' };

return {
  ...entry,
  valueUnit: 'thousands',
  valueUnitAdjusted: true,
  holdings: (entry.holdings || []).map((h) => ({ ...h, valueUsd: (Number(h.valueUsd) || 0) * 1000 })),
};
```

放在 `explicitlySmall` 之后，避免对 `style: 'small-fund'` 的 prior 短路（small-fund 路径不写 `valueUnitAdjusted`，所以即便我们先检查 `valueUnitAdjusted`，也不会拦到 small-fund）。

### Decision 2: 注释同步更新策略

- `lib/enrich/normalize-value-units.js` 文件头：扩 Heuristic 列表，加上"幂等：已归一化 entry 重复调用是 no-op"。
- `lib/enrich/period-diff.js:8-13`：把"normalizeValueUnits is idempotent"改为"normalizeValueUnits 是幂等的（见 openspec/specs/value-units-normalization），因此防御调用对已归一化 prior 是 no-op"。
- `scripts/prepare-digest.js:47-48`：把"Idempotent for already-normalized entries"改同上引用。

避免单纯"加注释不改代码"或"改代码不改注释"的半截——两者一起做才能让契约与实现闭合。

### Decision 3: 测试矩阵补全

`tests/enrich/normalize-value-units.test.js` 新增 1 个用例：

```
'keeps already-normalized entry unchanged (idempotency on raw_sum<$1M)'
```

- 构造一个 raw sum < $1M 的 entry，先调一次得到 `valueUnitAdjusted: true` 的 entry，再对它调一次。
- 断言：第二次返回的 `valueUsd` 与第一次完全相等（不再次 ×1000），且 `valueUnit` 仍为 `'thousands'`、`valueUnitAdjusted` 仍为 `true`。

可选：再加 1 个 end-to-end 用例，复用 ARK 2017-06-30 / 2017-09-30 的真实数据形状，跑 `periodDiff` 全流程，断言 `priorTotalValueUsd` 与 `deltaPct` 在合理范围。

### Decision 4: Spec 落档形式

新增 `openspec/changes/.../specs/value-units-normalization/spec.md`，包含：

1. **`normalizeValueUnits` 是幂等的**——对同一 entry 多次调用结果数值一致。
2. **`valueUnitAdjusted: true` 是"已归一化"标记**——输入侧必须被识别。
3. **`valueUnit` 三态合法值**——`dollars` / `thousands` / `unknown`，互斥。
4. **单位检测启发式保持 sum ≥ $1B → dollars、< $1B → thousands**——保留现有算法。
5. **`style: 'small-fund'` 优先于单位启发式**——返回 `valueUnit: 'unknown'`，不写 `valueUnitAdjusted`。

## Risks / Trade-offs

- **`valueUnitAdjusted` 字段语义被强化为契约** → 若未来代码外部直接构造带 `valueUnitAdjusted: true` 但实际 holdings 仍为 raw 的 entry（例如手写 fixture、第三方工具导入），会被误判为已归一化。**Mitigation**：在 spec 中明确"该字段只能由 `normalizeValueUnits` 自身写入"，并在测试中覆盖"未归一化 entry 不会被守卫短路"。
- **守卫只读 `valueUnitAdjusted`，不读 `valueUnit`** → 历史上若有人手工给 entry 写 `valueUnit: 'dollars'` 但 holdings 没动过，函数仍会按 sum 走 dollars 路径（事实上等价正确）。但反之：`valueUnit: 'thousands'` 手工写、holdings 未 ×1000 的 entry 仍会被乘，函数只信 `valueUnitAdjusted`。**Mitigation**：明确 spec 中 `valueUnit` 是诊断输出而非守卫依据。
- **现有 `idempotent` 测试（period-diff.test.js:110）现在更"有意义"** → 它原本测的是 ≥$1B 自然短路，修复后它测的是 ≥$1B 自然短路 + <$1M 守卫共同生效。语义不变、断言不变，**无需修改**。
- **未触发 caller 数据回填** → 旧运行产出的 digest JSON 中受影响 filer 的 `priorTotalValueUsd` / `deltaPct` 仍是错值，但本 fix 不重算历史产物；下一次运行即正确。**Mitigation**：在 tasks 中加一条"重跑 prepare-digest 验证 ARK 早期 deltaPct 恢复到合理量级"。

## Migration Plan

部署 = 单函数改动 + 单测试新增 + 注释更新。无需数据迁移、无需版本号变更（schema 仍 v1）。

回滚：revert 单个 commit，行为回到修复前。

## Open Questions

- 是否要把 `valueUnitAdjusted` 的命名改为 `valueUnitNormalized`，使其语义自解释？目前 `Adjusted` 一词较隐晦，spec 中已写明"已归一化"，但代码层 grep 友好性较差。本 fix 内不动命名，避免破坏 caller；若想改可另立 change。
- spec 是否要下沉到 `openspec/specs/value-units-normalization/`（永久目录）而非 change 内？当前 change 完成 archive 后，spec 会进 archive；按 OpenSpec 工作流这是标准做法，**确认走 archive 流程**。