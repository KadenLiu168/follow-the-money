## 1. 依赖与配置文件

- [x] 1.1 安装 devDependencies：`npm install -D eslint@^9 prettier@^3 eslint-config-prettier@^10 globals@^15`
- [x] 1.2 新增 `eslint.config.js`（扁平配置）：基于 `eslint:recommended` + `eslint-config-prettier`，用 `globals` 声明 node 全局变量，并 `ignores` 掉 `course/`、`node_modules/`、`coverage/`、`dist/`、`course/index.html`
- [x] 1.3 新增 `.prettierrc`：`singleQuote: true`、`semi: true`、`printWidth: 100`、`trailingComma: 'all'`
- [x] 1.4 新增 `.prettierignore`：忽略 `course/`、`node_modules/`、`coverage/`、`dist/`、`course/index.html`
- [x] 1.5 新增 `.nvmrc`，内容 `22`

## 2. package.json 脚本

- [x] 2.1 在 `package.json` 的 `scripts` 中新增 `lint`（`eslint .`）、`format`（`prettier --write .`）、`format:check`（`prettier --check .`）

## 3. 首次格式化与存量清理

- [x] 3.1 运行 `npm run format`，将改动作为独立的"style: apply prettier"提交（纯空白/标点，无行为变更）
- [x] 3.2 运行 `npm run lint -- --fix`，自动修复可修复项
- [x] 3.3 手工处理 `lint` 剩余的 `eslint:recommended` 违规，确有意为之的以针对性 `eslint-disable` 标注并写原因
- [x] 3.4 运行 `npm test` 确认格式化与 lint 修复后测试仍全绿

## 4. CI 门禁接线

- [x] 4.1 在 `.github/workflows/aggregate.yml` 的 `npm ci` 之后、`node scripts/aggregate.js` 之前，依次加入步骤：`npm test`、`npm run lint`、`npm run format:check`
- [x] 4.2 将 `actions/setup-node` 配置为 `node-version-file: .nvmrc`，确保 CI Node 版本与本地一致

## 5. 校验

- [x] 5.1 本地依次运行 `npm run lint`、`npm run format:check`、`npm test`，确认三者均绿灯
- [x] 5.2 推送后在 CI 确认门禁生效（lint/format 违规会阻断聚合）
