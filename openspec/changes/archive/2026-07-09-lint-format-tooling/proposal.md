## Why

审计报告（2026-07-08，发现项 L4 §3.6）指出：本仓库**没有任何 lint / format 工具链**——没有 ESLint、没有 Prettier、没有 `.nvmrc`。代码风格完全靠作者自觉保持一致，Node 版本仅在 `package.json` 的 `engines` 里声明（L5 已改为 `>=20.19.0`），本地开发无强制锁定。

这带来两个实际风险：(1) 风格漂移无人察觉，贡献一致性差；(2) M5 已让 CI 跑了 `npm test`，但**仍未跑 lint**，风格回归不会被任何门禁拦下。补上工具链是把"质量靠自觉"升级为"质量靠门禁"的最后一环。

## What Changes

- 新增 **ESLint** 配置（`eslint.config.js` 扁平配置），采用 `eslint:recommended` + 与 Prettier 的集成，关闭与格式化冲突的规则。
- 新增 **Prettier** 配置（`.prettierrc`），统一缩进/引号/行宽等格式约定。
- 新增 `lint`、`format`、`format:check` 三个 npm 脚本。
- 新增 **`.nvmrc`**，锁定 Node 版本为 `22`（与 L5 的 `engines >=20.19.0` 一致，且满足 `with { type: 'json' }` 对 Node ≥20.19 的要求）。
- 将 `npm run lint`（及 `format:check`）**接入 CI 门禁**，扩展既有 `ci-test-gate` 能力的要求。
- 首跑策略：对安全可自动修复的违规执行 `--fix`；对需保留的风格差异以 `eslint-disable` 显式标注并说明原因，不在提案阶段大规模重写既有代码。

**不做的事**：不引入 TypeScript 类型检查（项目为纯 JS）；不新增 `format` 自动提交；不改动任何运行时行为；不触及 `course/` 与 `node_modules`。

## Capabilities

### New Capabilities
- `lint-format`：仓库提供 ESLint + Prettier 配置、`lint`/`format`/`format:check` 脚本及 `.nvmrc` Node 版本锁定。

### Modified Capabilities
- `ci-test-gate`：扩展其门禁要求，在聚合前除 `npm test` 外**还需通过 `npm run lint` 与 `format:check`**，使风格回归同样阻断发布。

## Impact

- **新增 devDependencies**：`eslint`、`prettier`、`eslint-config-prettier`（+ 可选 `globals` 以声明 Node 全局变量）。
- **新增文件**：`eslint.config.js`、`.prettierrc`、`.nvmrc`。
- **修改文件**：`package.json`（新增脚本）、`.github/workflows/aggregate.yml`（新增 lint 步骤）。
- **运行时影响**：无。`node_modules` 仅增长 devDependencies；构建产物与聚合逻辑不变。
- **CI 影响**：aggregate 工作流在聚合前多跑一步 lint；首跑若命中存量风格问题，需先 `--fix` 或标注后再合并。
