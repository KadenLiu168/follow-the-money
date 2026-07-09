## Context

`follow-the-money` 是一个零运行时依赖的纯 Node.js ESM 项目，当前**没有任何 lint/format 工具链**（审计 L4）。代码风格靠作者自觉，CI（`.github/workflows/aggregate.yml`）在 M5 之后只跑 `npm test`，风格回归无门禁。Node 版本仅靠 `package.json` 的 `engines >=20.19.0` 声明，本地无 `.nvmrc` 强制。

本 change 把"质量靠自觉"升级为"质量靠门禁"：补齐 ESLint + Prettier + `.nvmrc`，并把 lint/format 接入 CI 门禁（扩展既有 `ci-test-gate` 能力）。

## Goals / Non-Goals

**Goals:**
- 提供 ESLint 扁平配置 + `lint` 脚本，基于 `eslint:recommended`，并与 Prettier 集成避免规则冲突。
- 提供 Prettier 配置 + `format` / `format:check` 脚本，Prettier 独占格式化权威。
- 提供 `.nvmrc` 锁定 Node 主版本（22），与 `engines >=20.19.0` 一致。
- 将 `lint` + `format:check` 接入聚合工作流门禁。
- 首跑以"安全自动修复 + 显式标注"的策略落地，不打算大规模手工重写既有代码。

**Non-Goals:**
- 不引入 TypeScript 类型检查（项目为纯 JS，无 TS）。
- 不新增 `format` 自动提交动作（仅提供脚本，由开发者/CI 调用）。
- 不改动任何运行时行为、聚合逻辑或构建产物。
- 不统一/重构 `course/` 教学站点（其有独立构建，本 change 将其排除在 lint/format 范围外）。

## Decisions

1. **ESLint 扁平配置（`eslint.config.js`，ESLint 9）**
   - 理由：ESLint 9 默认扁平配置，且项目 Node ≥20.19 完整支持。
   - 备选：遗留 `.eslintrc` —— 否决（v9 已弃用，未来移除）。
2. **基于 `eslint:recommended` + `eslint-config-prettier`**
   - 理由：只做"正确性/潜在bug"检查（未使用变量、重复 case 等），把格式化完全交给 Prettier，避免双套规则打架；降低首跑噪音与风格争论。
   - 备选：直接采用 airbnb/standard 等强约束共享配置 —— 否决（既有代码已较一致，强约束会带来大量非必要的风格改写）。
3. **Node 全局变量用 `globals` 包声明**
   - 理由：ESM 下 `process`、`Buffer`、`__dirname`（经 import.meta）、`fetch` 等需显式声明，否则 `no-undef` 误报。
4. **Prettier 取值贴近现有风格**：`singleQuote: true`、`semi: true`、`printWidth: 100`、`trailingComma: 'all'`。
   - 理由：现有源码普遍使用单引号与分号（`const DETAIL_CAP = 8;`）。Prettier 为格式化唯一权威，最终以配置为准统一。
5. **`.nvmrc` 锁定 `22`**
   - 理由：LTS，满足 `engines >=20.19.0`，且覆盖 `with { type: 'json' }` 对 Node ≥20.19 的要求（L5 背景）。
6. **CI 接线：扩展 `aggregate.yml` 而非新建 `ci.yml`**
   - 在 `npm ci` 之后、`node scripts/aggregate.js` 之前依次加入 `npm run lint` 与 `npm run format:check`（保留 M5 的 `npm test` 在最前）。
   - 理由：与现有最小自动化保持一致，门禁集中在一条聚合流水线。
   - 备选：新建 `ci.yml` 在 PR/push 时跑 test+lint —— 留作未来选项，当前不引入以免范围扩散。
7. **lint/format 范围排除 `course/` 与 `node_modules`**
   - `eslint.config.js` 与 `.prettierignore` 显式忽略 `course/`、`node_modules/`、`coverage/`、`dist/` 及生成产物 `course/index.html`。

## Risks / Trade-offs

- **[Risk] 首次 `format` 会产生跨全量文件的巨大 diff** → 缓解：将其作为独立的"style: apply prettier"提交，与行为变更分离；Prettier 改写纯属空白/标点，不影响测试与运行时，先跑 `npm test` 验证绿灯。
- **[Risk] ESLint 首跑报出大量存量违规** → 缓解：仅启用 `eslint:recommended`（非风格类），对可自动修复项跑 `--fix`，其余手工处理，确有意为之的用针对性 `eslint-disable` 标注原因；把门槛压低，使门禁尽快转绿。
- **[Risk] `globals` 配置不当导致误报** → 缓解：显式引入 node 全局集合，先对单文件试跑确认无误。
- **[Risk] CI Node 版本与 `.nvmrc` 不一致** → 缓解：工作流 `actions/setup-node` 使用 `node-version-file: .nvmrc`，确保本地与 CI 一致。

## Migration Plan

1. `npm install -D eslint@^9 prettier@^3 eslint-config-prettier@^10 globals@^15`。
2. 新增 `eslint.config.js`、`.prettierrc`、`.prettierignore`、`.nvmrc`。
3. `package.json` 增加脚本：`lint`（`eslint .`）、`format`（`prettier --write .`）、`format:check`（`prettier --check .`）。
4. 单独提交一次 `npm run format`（纯风格，无行为变更）。
5. 跑 `npm run lint -- --fix`，手工处理剩余项并补 `eslint-disable` 注释。
6. 扩展 `aggregate.yml`：在 `npm test` 之后加入 `npm run lint` 与 `npm run format:check`。
7. 本地校验 `npm run lint`、`npm run format:check`、`npm test` 全绿；推送后确认 CI 门禁生效。
8. **回滚**：移除新增脚本/配置/步骤即可，无任何运行时影响。

## Open Questions

- Prettier 的 `semi`/`singleQuote` 精确取值是否要严格对齐现有文件？提案取值（单引号、分号、100 宽、全尾逗号）贴近现状；若执行 `format` 后仍有个别差异，以 Prettier 配置为权威统一即可。
- 是否值得后续拆出独立 `ci.yml` 在 PR 阶段拦截？当前并入 `aggregate.yml` 已满足门禁诉求，拆分可作为后续增强。
