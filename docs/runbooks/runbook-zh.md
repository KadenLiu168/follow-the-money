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

## 恢复运行

当生产 runtime state 被污染（例如 registry 的 `root_identity` 来自非 Runner
机器）时，恢复走 git 层 restore commit：`.feed-state/` 从受信基线 commit
原样恢复、无效的 `feeds/` product 直接删除——绝不就地手工编辑，也绝不删除
重建 bootstrap。其后一次手动 workflow dispatch 即为正常 armed run
（`prepare` → `collect` → `finalize`）：窗口规划从恢复的 checkpoint 出发，
checkpoint 间隔超过配置上限时采用 bounded 72h bootstrap 回看，并把未覆盖
区间作为显式 coverage gap 记录。

## Consumer 边界

Skill 使用 `scripts/skill/prepare-feed` 获取并校验 canonical manifest 及其五个
artifact，然后只在 stdout 输出一个绑定当前 Feed 的、非持久化 `DigestContext`
version `2`：它只包含准备好的 current updates、compact domain status 和封闭的
material limitations。它不是发布 artifact、checkpoint、cache 或独立 evidence
schema；不会调用 Provider、读取本地 state，或 fallback 到 stale/partial product。
