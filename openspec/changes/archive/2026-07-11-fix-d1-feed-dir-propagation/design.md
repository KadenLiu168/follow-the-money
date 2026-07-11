# Design: fix-d1-feed-dir-propagation

## 根因复述

env var `FOLLOW_THE_MONEY_FEED_DIR` 同时承担"模式开关"角色：

| 状态 | 含义 | 谁负责设置 |
|---|---|---|
| 已设置 | skill mode：fetch 写缓存、consumer 读缓存 | **当前无人设置 → bug** |
| 未设置 | local mode：consumer 回落 `cwd` | aggregate.js 写 cwd，天然成立 |

`scripts/fetch-feed.js` 用 `defaultTargetDir()`（缓存目录）写数据，但 SKILL Step 2 只跑 `node scripts/fetch-feed.js`，**既不 export 也不把目录传给下游**。Step 3/6 的 `FOLLOW_THE_MONEY_FEED_DIR=$FOLLOW_THE_MONEY_FEED_DIR` 里 `$FOLLOW_THE_MONEY_FEED_DIR` 是空 shell 变量 → consumer 回落 `cwd` → 读 repo 里 CI 提交的旧 feed。

## 关键设计决策

### 决策 1：内联解析，而非 `export`
agent 运行时很可能把 SKILL 的每一步当成独立 shell 执行，`export` 不会跨步骤存活。因此用
`FOLLOW_THE_MONEY_FEED_DIR="$(node scripts/fetch-feed.js --print-dir)"` 在每个数据命令前**就地解析**，
每个命令自包含、无状态、跨 shell 稳健。`--print-dir` 复用已导出的 `defaultTargetDir()`，单一真相源、零逻辑重复。

### 决策 2：保留 `|| REPO` 回落（不动 prepare/check-alerts）
local mode 是文档承诺的能力（architecture.md: "Local deployments are unaffected ... read from cwd when unset"），
且 `tests/scripts/prepare-digest.test.js` / `check-alerts.test.js` 有专门用例 `falls back to cwd when FOLLOW_THE_MONEY_FEED_DIR is unset`。
删除 `|| REPO`（即 `docs/analysis-vs-follow-builders.md` 的 D1 方案）会同时破坏这两者 —— 除非与 D5（合并成 run-digest.js）绑定，否则单独落地是 regression。本 change 明确拒绝该变体。

### 决策 3：`if` 分支恢复 "fetch 失败 → cwd" 语义
原 SKILL 文字说 "On failure: fall through to local mode"，但当前实现因 env 永远空，其实**永远**走 cwd（连成功时也走）。
用 `if node scripts/fetch-feed.js --print-dir ...` 包裹，让：
- fetch 成功 → consumer 指向缓存目录（D1 修复）
- fetch 不可用 → consumer 无 env → 回落 cwd（恢复文档语义，且 local mode 不变）

### 决策 4：D3 不在本 change
本 change 只修"目录错配"。fetch 失败时回落到的 cwd 数据可能是陈旧/空的，而 prepare 仍会 `exit 0` 吐空 digest（D3）。
那道护栏不在本 change 范围，需另行处理，否则即使本 change 合入，silent 失败类仍未闭合。
