## Context

当前 `.github/workflows/aggregate.yml` 是一个每日双触发（UTC 12:00 / 00:00）+ `workflow_dispatch` 的 cron job，负责抓取 SEC 13F / 13D/G filing 并把喂料 commit 回仓库。它的步骤顺序是：`checkout` → `setup-node` → `npm ci` → `npm test` → `npm run lint` → `npm run format:check` → `node scripts/aggregate.js` → `git commit/push`。

问题：后三个 gate 没有 `continue-on-error`，任一非零退出就让 job 中止，`aggregate.js` 永远跑不到。最近三笔提交（`f38e22d` / `9f43d25` / `1282cf2`）落地了未格式化的文件，`prettier --check` 因此失败，于是**喂料从那笔提交起每天都在静默停更**。同时仓库没有 PR 级 CI，唯一的格式强制力就是这个 cron——在凌晨、无人值守、还顺带卡死数据管道的最糟位置发现格式问题。

约束：prettier 走 `package-lock.json` 锁版本（`npm ci` 装到的与本地一致），`.nvmrc` 已固定 Node，`.prettierrc` 配置（`printWidth:100`、自闭合 void 元素等）保持不变。

## Goals / Non-Goals

**Goals:**
- 把代码质量 gate（test / lint / format:check）移到独立的 `ci.yml`，在 push / PR 时、合并前拦截。
- 让 `aggregate.yml` 只干抓数据 + commit 的活，不再被格式问题阻塞。
- 把 3 个未格式化文件格式化并提交，使 `ci.yml` 首次运行即绿，并立即恢复喂料。

**Non-Goals:**
- 不引入 pre-commit hook（husky / lint-staged）——可后续独立 change，本次不动。
- 不改 prettier / eslint 配置、不新增依赖。
- 不动 `lint-format` capability 的 requirement（脚本已存在且可作为 gate，本次只是把它接进 `ci.yml`，归属由 `ci-test-gate` 描述）。

## Decisions

**D1：新增 `ci.yml`，触发 `push` 到 `main` 与 `pull_request` 指向 `main`。**
理由：格式 / lint / 测试问题应在合并前、每次 PR 就被拦下，这是标准位置。
备选：仅在 `aggregate.yml` 给 gate 加 `continue-on-error` → 否决。这会让未格式化代码照样合进 `main`，且 gate 仍每天才跑一次，PR 阶段毫无保护，等于没修根因。

**D2：从 `aggregate.yml` 移除全部三个 gate（test / lint / format:check），而非只移 format:check。**
理由：代码质量完全交给 `ci.yml` 拥有，`aggregate.yml` 信任 `main` 即可。若只移 format:check 而保留 test/lint，main 上一旦有破测试仍会卡死喂料，不彻底。
权衡：有人绕过 PR 直接 force-push 到 `main` 时，cron 不再自查 → 接受，这是业界标准信任模型；`ci.yml` 的 push 触发器仍会在推送后立刻标红。

**D3：`aggregate.yml` 保留 `checkout` + `setup-node`(复用 `node-version-file: .nvmrc`) + `npm ci` + `aggregate` + `commit`。** 这些是跑聚合器与写回喂料必需的，与代码质量 gate 无关。

**D4：`tests/fixtures/13d-html-shape.html` 仍留在 prettier 管辖内，不加入 `.prettierignore`。**
理由：本次 prettier 对该 fixture 的唯一改动是 `<br>`→`<br/>`，HTML 语义完全等价，`thirteen-dg.test.js` 读原始 HTML 解析，测试不受影响。加入 ignore 属于掩盖问题且会引入不一致的规则。
备选：把 `tests/fixtures/` 整体 ignore → 否决，当前无必要；若将来某个 fixture 故意保留"脏" HTML 再单独处理。

**D5：格式修复先行于 gate 上线。** 先 `npm run format` 并提交 3 个文件，再引入 `ci.yml` + 改 `aggregate.yml`，保证 `ci.yml` 第一次触发就是绿的，且喂料在 PR 合并的同时恢复。

## Risks / Trade-offs

- **[aggregate.yml 不再自查代码质量]** → `ci.yml` 在 push/PR 时已守门；可接受。若团队不放心，未来可把 `npm test` 以非阻塞（`continue-on-error: true`）形式留在 cron 作告警，但本次为简洁整体迁出。
- **[ci.yml 首次运行若格式修复未先合入会红]** → 任务顺序保证格式提交先于 gate 生效；且 PR 不绿不能合，天然防呆。
- **[prettier 版本漂移导致本地/Ci 判定不同]** → `package-lock.json` 锁死版本 + `npm ci` 保证 CI 与本地完全一致，不存在漂移。

## Migration Plan

1. 提交 3 个文件的格式修复（`scripts/check-alerts.js`、`tests/lib/resolve-prompts.test.js`、`tests/fixtures/13d-html-shape.html`）。
2. 新增 `.github/workflows/ci.yml`，删除 `aggregate.yml` 中三个 gate 步骤。
3. 推送，观察 `ci.yml`（push 触发）与下一次 `aggregate.yml`（cron / dispatch）均绿，喂料恢复更新。
4. 回滚：对两个 workflow 文件 `git revert` 即恢复旧行为；格式修复提交可单独保留或一并回退。

## Open Questions

无阻塞性疑问。可选后续（不在本次范围）：是否加 pre-commit hook 让格式问题根本到不了 PR。
