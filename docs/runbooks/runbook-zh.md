# Feed 生产运行手册

定时工作流生成当前五域 Evidence Feed，不需要 API key 或付费数据凭据。

## 正常路径

1. `prepare` 刷新 `main`，校验配置和 Provider manifest，检查分离的
   `.feed-state/`，并 arm deployment lease。
2. `collect` 校验 lease，捕获固定 cutoff，运行八个启用 Provider，校验
   provenance/freshness/coverage，并在 `feeds/` 写入候选 product。
3. `finalize` 校验 status 与 checkpoint，持久化 terminal lease，只 stage
   manifest、五个 active artifact 和 durable runtime state。
4. 工作流以普通 fast-forward commit/push 到 `main`。

Active entry 是 `feeds/feed-manifest.json`，inventory 必须恰好包含
`news`、`macro_release`、`policy`、`positioning`、`filing`。

## 失败处理

required Provider 的 failed/incomplete 结果会产生 typed failure，不会静默
用 prior evidence 替代。符合 coverage 语义的 HTTP 401/403 blocked Provider
可以生成 accepted degraded Feed；failed Feed 不得发布。

不要手工编辑 Feed identity、artifact hash、checkpoint、rate state 或 lease。
上一版八域 product 必须先经过显式 bounded migration；mixed generation 无效。

## Consumer 边界

Skill 使用 `scripts/skill/prepare-feed`，只获取 canonical manifest 及其五个
artifact；不会调用 Provider、读取本地 state，或 fallback 到 stale/partial
product。
