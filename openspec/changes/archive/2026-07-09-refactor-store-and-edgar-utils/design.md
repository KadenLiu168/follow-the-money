## Context

`docs/code-quality-review-2026-07-08.md` 标记了三处中优先级重复代码（M1/M2/M3）。现状已核验：

- **M1**：原子写模板 `tmp = ${path}.${pid}.${Date.now()}.tmp` + `writeFileSync` + `renameSync` 当前仍内联于 `lib/store/feed-json.js:24-26`、`state-json.js:18-20`、`manifest.js:21-23`（三者均用 `JSON.stringify(x, null, 2)`）。`feed-ndjson.js` / `state-ndjson.js` 因 P1-2 已改用 `appendFileSync`，不再使用该模板，但其 import 行仍残留未使用的 `writeFileSync` / `renameSync`。
- **M2**：`scripts/verify-edgar.js:11-21` 手写了模块级单例桶 + `take()`，`fetchWithRetry` 未走 `lib/http-client.js` 的统一封装；而 `lib/token-bucket.js` 的 `TokenBucket` 与 `lib/http-client.js` 的 `createHttpClient` 已是项目规范实现（pipeline-a/b 在用）。
- **M3**：`lib/edgar/fetch-thirteen-f-xml.js:11-13` 与 `lib/aggregate/pipeline-b.js:29-31` 各自内联了 `cikNoPad` / `accNoDash` / `baseUrl` 构造。

约束：纯重构，**禁止改变既有行为/输出**；所有现有测试须仍全绿；不触碰 M4/M5/M6 等其它项。

## Goals / Non-Goals

**Goals:**
- 抽出共享的原子写 helper（M1）与 EDGAR 归档 URL helper（M3），消除重复。
- 让 `verify-edgar.js` 复用既有 `TokenBucket` + `http-client`（M2），消除第二套限流实现。
- 清理 P1-2 遗留的未使用 import。

**Non-Goals:**
- 不统一 `lib/fetch/fetch-feed.js` 的异步（`fs/promises`）原子写路径——它属 `lib/fetch/` 模块、使用 promise API，与同步 `atomicWriteJSON` 不同源，混用会引入 async/sync 混乱，不在本次范围。
- 不改动 `TokenBucket` / `http-client` 自身实现，不新增配置项。
- 不做任何行为增强（如加锁、校验和、权限位）——原样保留 tmp+rename 语义。

## Decisions

### D1 — M1：单模块导出 `atomicWriteJSON` / `atomicWriteText`
新建 `lib/store/atomic-write.js`，导出两个同步函数，内部严格沿用现有 `tmp+writeFileSync+renameSync` 实现（`JSON.stringify(obj, null, 2)` 与原 writer 完全一致）。三个 JSON writer 改为调用 helper，删除各自内联副本与重复的 `node:fs` import 行。
- **替代方案**：用 `fs/promises` 异步版统一——否决，会引入 async 化扩散，且需改 writer 调用方为 await，超出"纯重构"边界。
- **副作用清理**：`feed-ndjson.js` / `state-ndjson.js` 移除未使用的 `writeFileSync` / `renameSync` import（P1-2 后其写路径仅用 `appendFileSync`）。

### D2 — M2：`verify-edgar.js` 复用 `TokenBucket(10,10)` + `createHttpClient`
用 `new TokenBucket(10, 10)` 精确匹配旧 `bucket = { tokens: 10, rate: 10 }` 的初值与速率；`createHttpClient({ userAgent: ua, bucket })` 返回的 `client.fetch` 已包含 `bucket.take()` + 强制 UA + 429/Retry-After + 3 次重试 + 网络错误指数退避，是旧 `fetchWithRetry` 的超集。删除内联 `bucket` / `take()` / `fetchWithRetry`，`runVerify(ua)` 内构造 `client` 并下传 `checkCik` / `check13DGSearch`，与 pipeline-a/b 的 `httpClient` 传参风格一致。
- **被丢弃的 `Accept-Encoding: gzip, deflate`**：`globalThis.fetch` 默认即对 gzip 自动解码，无需显式声明，删除无行为影响。
- **权衡**：`createHttpClient` 在网络错误时改用指数退避（旧版是 token 等待固定 50ms 自旋），但 token 等待由 `TokenBucket` 控制而非 fetch 层；整体限流/重试语义等价且更稳健。

### D3 — M3：抽出 `edgarArchiveUrl` / `edgarDocUrl`
新建 `lib/edgar/archive-url.js`：
- `edgarArchiveUrl(cik, accession)` = `https://www.sec.gov/Archives/edgar/data/${String(parseInt(cik,10))}/${accession.replace(/-/g,'')}`
- `edgarDocUrl(cik, accession, fileName)` = `${edgarArchiveUrl(cik, accession)}/${fileName}`
`fetch-thirteen-f-xml.js` 改用 `edgarDocUrl(cik, acc, 'index.json')` 与 `edgarDocUrl(cik, acc, infoTableFile)`；`pipeline-b.js` 用 `edgarArchiveUrl` 取代内联 `baseUrl`，用 `edgarDocUrl(cik, acc, htmlName)` 构造最终文档 URL。输出字符串与重构前逐字符一致。

## Risks / Trade-offs

- **[M1] JSON 输出格式漂移** → 现有三处均用 `JSON.stringify(x, null, 2)`，helper 严格沿用；新增单测断言"写出内容 === 原内联写出内容"，确保零差异。
- **[M2] 限流初值/语义偏差** → `TokenBucket(10, 10)` 初值 `tokens=10`、速率 `10` 与旧桶一致；现有 `verify-edgar` 无单测，作为补偿在 tasks 中加一个轻量"构造 client + 一次 throttled fetch"的集成冒烟（用 nock 或本地 server 可选），或至少手动 `node scripts/verify-edgar.js` 跑通。
- **[M3] CIK 解析边界** → `String(parseInt(cik,10))` 与原 `cikNoPad` 完全一致（零填充 CIK 也能正确去填充）；单测覆盖"零填充 CIK / 已去填充 CIK"两种输入，断言 URL 相等。
- **[通用] 行为回归** → 全量 `vitest run` + `openspec validate` 作为硬性门禁；任何失败即回退。

## Migration Plan

纯重构，无数据迁移、无配置变更。
- 部署：随普通 commit 合入 `main`。
- 回滚：若出问题 `git revert <commit>` 即可，不影响数据文件与运行产物。

## Open Questions

无。所有决策均可在现有代码约束内确定，无需用户额外输入。
