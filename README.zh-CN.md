# Follow the Money（追踪资金）

面向 Host Agent 的确定性、免凭据五域 Evidence Feed，也是证据驱动信息摘要 Skill 的仓库边界。仓库负责证据采集、规范化、校验、身份、来源与发布；Skill 将当前 validated Feed 准备为一个非持久化的 `DigestContext` version `2`，Host Agent 消费其中准备好的 current updates 并生成 evidence-preserving information digest。

## 能力边界

仓库只有一个能力：Evidence Feed。它负责 Provider 契约、固定 cutoff/window、provenance、freshness、coverage、degradation、deterministic identity、canonical serialization、原子发布和 canonical current-Feed consumption。

```text
validated Feed -> DigestContext -> Host Agent -> evidence-preserving Digest
```

Feed 不包含金融解释、重要性、ranking、regime、market impact、prediction、recommendation 或交易结论。Host Agent 可以为了可读性对准备好的 current updates 进行 grouping、heading、ordering、consolidation 和 compression，但必须保持 claim 级别的语义支持，且不得重新分类 Feed evidence 或对每个 Feed item 做 omission accounting。

## 当前 Feed 契约

新 bundle 使用 logical Feed schema major **5**、manifest major **5**、artifact major **2**。保留（retained）的 evidence artifact 顺序为：

```text
news
macro_release
policy
positioning
filing
```

五个 artifact 始终存在，即使为空。八个必需且免凭据的 Provider 是 Federal Reserve、BLS、PBOC、NBS、SSE、SZSE、SEC EDGAR 和 CFTC。CFTC 是 minimum-one 的必需 weekly positioning coverage member。

SEC EDGAR v4 的 filing item 区分完整的 `form13f` current-state evidence、有界 current-window `form4`/`4/A` ownership evidence，以及有界结构化 `SCHEDULE 13D`/`13G` beneficial-ownership evidence。Form 4 保留 issuer、reporting owner、transaction/holding、post-state 和 footnote 数据；beneficial-ownership 保留来源支持的 issuer/class identity、reporting positions、typed ownership facts 和保守 comparison states。Form 4 和 beneficial-ownership evidence 都不推断 delta、amendment lineage、intent、control 或 market impact，并继续保留 SEC v1-v3 的有界读取兼容。

新采集或替换的 `news`、`macro_release` 和 `policy` item 携带闭合的 item-level `semantic_context`。它只表达来源支持的 subject、event/document facts、有界 numeric observations、macro period/revision 以及 policy date/affected scope；不表达 ranking、sentiment、market impact、prediction 或 recommendation。`filing` 和 `positioning` 不携带该字段。当前 consumer 仍接受结构有效的 previous-major legacy omission；无 context 的旧 slice 只有在已有 carry-forward proof 时才能按原 bytes carry-forward，而新采集或替换的受影响 item 必须有有效 context。

`news`、`macro_release` 和 `policy` item 还可以携带闭合的 `source_content` 字段：单份官方文档的有界 NFC 纯文本（最多 12,000 个 Unicode code point）、其 `format`、`truncated` 状态，以及被采纳原始响应字节的 SHA-256。Federal Reserve、PBOC、SSE、SZSE 的 v2 provider 契约要求其本次采集的每个 current-window item 都携带该字段，因此必需详情文档缺失、不受支持、不安全、超限或无法抽取时，provider 保持不完整，而不会产出看似健康的仅标题 item。有界文本绝不用于重建缺失的结构化语义字段，DigestContext 只暴露 `text`、`format` 和 `truncated`，抽取方法与文档摘要仅作为 Feed 的溯源信息保留。

上一 major 的五域 bundle 只能进入显式 bounded migration path；正常加载和远程消费拒绝上一 major 之外的所有更旧 major，也不会把 removed-domain artifact 当作当前证据。

## 目录结构

```text
config/                    Feed 配置与 Provider activation
providers/                 已验证 Provider manifest 与 deterministic fixtures
schemas/                   Feed、manifest、artifact JSON Schema
src/follow_the_money/feed  Feed producer、validation、publication、consumption
src/follow_the_money/digest.py  非持久化、确定性的 DigestContext v2 preparation
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

Producer 不需要 API key 或付费数据凭据。Normal Skill consumer 从 canonical `main` 获取 `feeds/feed-manifest.json`，再只获取 manifest 声明的五个 artifact，并在 stdout 输出一个 canonical `DigestContext` version `2`；该 context 非持久化、不替代 Feed authority，也不是独立 evidence schema。失败时不使用本地（local）、stale、partial、historical 或未校验 fallback。

## 退出码

- `0` — healthy 或接受的 degraded Feed
- `1` — Feed generation、publication、schema 或 integrity failure
- `2` — usage、configuration 或 startup-capability failure

## 定时生产

GitHub Actions 按配置 schedule 或 `workflow_dispatch` 执行 Feed producer。`.feed-state/` 保存 collection state，`feeds/` 保存 active product。固定 cutoff/window、Provider freshness/provenance、required coverage、bounded blocked-Provider degradation、原子 manifest activation、checkpoint continuity 和 durable rate safety 均保持 fail-closed。

详见 [`docs/feed-contract.md`](docs/feed-contract.md)、[`docs/configuration.md`](docs/configuration.md) 和 [`docs/architecture.md`](docs/architecture.md)。
