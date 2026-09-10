# Follow the Money（追踪资金）

面向 Host Agent 的确定性、免凭据五域 Evidence Feed，也是证据驱动信息摘要 Skill 的仓库边界。仓库负责证据采集、规范化、校验、身份、来源与发布；Host Agent 只消费当前 Feed，并生成 evidence-preserving information digest。

## 能力边界

仓库只有一个能力：Evidence Feed。它负责 Provider 契约、固定 cutoff/window、provenance、freshness、coverage、degradation、deterministic identity、canonical serialization、原子发布和 canonical current-Feed consumption。

```text
published Feed -> validation -> Host Agent summarization/formatting -> information digest
```

Feed 不包含金融解释、重要性、ranking、regime、market impact、prediction、recommendation 或交易结论。Host Agent 可以为了可读性进行 grouping、heading、ordering、consolidation 和 compression，但必须保持语义支持并披露 omission。

## 当前 Feed 契约

新 bundle 使用 logical Feed schema major **4**、manifest major **4**、artifact major **2**。保留（retained）的 evidence artifact 顺序为：

```text
news
macro_release
policy
positioning
filing
```

五个 artifact 始终存在，即使为空。八个必需且免凭据的 Provider 是 Federal Reserve、BLS、PBOC、NBS、SSE、SZSE、SEC EDGAR 和 CFTC。CFTC 是 minimum-one 的必需 weekly positioning coverage member。

上一版八域 bundle 只能进入显式 bounded migration path；正常加载和远程消费拒绝上一 major，也不会把 removed-domain artifact 当作当前证据。

## 目录结构

```text
config/                    Feed 配置与 Provider activation
providers/                 已验证 Provider manifest 与 deterministic fixtures
schemas/                   Feed、manifest、artifact JSON Schema
src/follow_the_money/feed  Feed producer、validation、publication、consumption
scripts/feed/              内部 deterministic producer 入口
scripts/skill/             canonical published-Feed consumer 入口
feeds/                     当前 manifest-led Feed product
.feed-state/               lock、rate registry、lease、checkpoint
tests/                     免凭据测试
docs/                      当前 Feed 契约与 runbook
.github/workflows/         CI 与定时 Feed 生产
```

## 快速开始

```bash
uv sync --frozen --all-groups
uv run pytest
scripts/skill/prepare-feed
scripts/feed/follow-the-money-feed --dry-run
```

Producer 不需要 API key 或付费数据凭据。Normal Skill consumer 从 canonical `main` 获取 `feeds/feed-manifest.json`，再只获取 manifest 声明的五个 artifact；失败时不使用本地（local）、stale、partial、historical 或未校验 fallback。

## 退出码

- `0` — healthy 或接受的 degraded Feed
- `1` — Feed generation、publication、schema 或 integrity failure
- `2` — usage、configuration 或 startup-capability failure

## 定时生产

GitHub Actions 按配置 schedule 或 `workflow_dispatch` 执行 Feed producer。`.feed-state/` 保存 collection state，`feeds/` 保存 active product。固定 cutoff/window、Provider freshness/provenance、required coverage、bounded blocked-Provider degradation、原子 manifest activation、checkpoint continuity 和 durable rate safety 均保持 fail-closed。

详见 [`docs/feed-contract.md`](docs/feed-contract.md)、[`docs/configuration.md`](docs/configuration.md) 和 [`docs/architecture.md`](docs/architecture.md)。
