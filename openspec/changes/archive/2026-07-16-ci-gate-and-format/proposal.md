## Why

`format:check` 这道 gate 当前嵌在 `.github/workflows/aggregate.yml` 里——而那是**每日定时抓取 SEC filing 并 commit 喂料**的 cron job。最近三笔特性提交（`f38e22d` feedDir、`9f43d25` prompt 内嵌、`1282cf2` 13D HTML 解析）落地时没跑 `prettier --write`，导致 `prettier --check` 失败。由于该 gate 在 `node scripts/aggregate.js` **之前**执行且无 `continue-on-error`，job 直接 `exit 1`，聚合器从未运行——**喂料每次被 cron 触发都在静默停更**。同时仓库没有 PR 级 CI，唯一的格式化强制力就是这个 cron，恰恰是最糟的发现位置。

## What Changes

- **新增** `.github/workflows/ci.yml`：在 `push` 到 `main` 与 `pull_request` 指向 `main` 时，依次执行 `npm ci` → `npm test` → `npm run lint` → `npm run format:check`。这是 gate 的**新家**，在合并前拦截。
- **修改** `.github/workflows/aggregate.yml`：移除 `test` / `lint` / `format:check` 三个阻塞步骤，仅保留 `checkout` + `setup-node` + `npm ci` + `aggregate` + `commit`。cron 的职责是抓数据并提交，不负责代码质量警察。
- **修复格式**：对 3 个未格式化文件运行 `npm run format` 并提交（`scripts/check-alerts.js`、`tests/lib/resolve-prompts.test.js`、`tests/fixtures/13d-html-shape.html`），使 `ci.yml` 首次运行即绿。

## Capabilities

### New Capabilities
<!-- 无新增 capability -->

### Modified Capabilities
- `ci-test-gate`：现有 requirement 把 `test`/`lint`/`format:check` 这道 gate 写死在 `aggregate.yml` 内（且要求 gate 失败则禁止聚合）。改为：gate 移到独立的 `ci.yml` 在 push/PR 时执行；`aggregate.yml` 不再以代码质量 gate 阻塞喂料。

## Impact

- `.github/workflows/aggregate.yml` 失去代码质量 gate（test/lint/format）。**可接受的权衡**：`ci.yml` 在合并前守住 `main`，cron 信任 `main` 即可；这正是对当前故障根因的纠正。
- 3 个源文件 / fixture 被重新格式化（纯 cosmetic：行宽折行 + `<br>`→`<br/>`），13D 解析测试不受影响（`<br>` 与 `<br/>` 语义等价）。
- 不引入新依赖；`.nvmrc` 已固定 Node 版本，`setup-node` 的 `node-version-file` 可直接复用。
