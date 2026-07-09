## 1. M1 — 共享原子写 helper

- [x] 1.1 新建 `lib/store/atomic-write.js`，导出 `atomicWriteJSON(path, obj)`（`JSON.stringify(obj, null, 2)` → tmp + `writeFileSync` + `renameSync`）与 `atomicWriteText(path, str)`（原始字符串同策略）
- [x] 1.2 `lib/store/feed-json.js` 改用 `atomicWriteJSON`，删除内联 tmp+rename 与多余 `node:fs` import
- [x] 1.3 `lib/store/state-json.js` 改用 `atomicWriteJSON`，删除内联副本与多余 import
- [x] 1.4 `lib/store/manifest.js` 改用 `atomicWriteJSON`，删除内联副本与多余 import
- [x] 1.5 `lib/store/feed-ndjson.js` 移除 P1-2 后未使用的 `writeFileSync` / `renameSync` import
- [x] 1.6 `lib/store/state-ndjson.js` 移除 P1-2 后未使用的 `writeFileSync` / `renameSync` import

## 2. M2 — verify-edgar 复用 TokenBucket + http-client

- [x] 2.1 `scripts/verify-edgar.js` 删除内联 `bucket` 单例、`take()`、`fetchWithRetry` 及对应 `node:fs` 之外的多余 import
- [x] 2.2 引入 `TokenBucket`（构造 `new TokenBucket(10, 10)` 匹配旧速率/容量）与 `createHttpClient`
- [x] 2.3 `runVerify(ua)` 内构造 `client = createHttpClient({ userAgent: ua, bucket })` 并下传 `checkCik` / `check13DGSearch`；所有 `fetchWithRetry(url, ua)` 调用改为 `client.fetch(url)`
- [x] 2.4 确认 UA 经 `client` 绑定（不再逐调用传 `ua` 给 fetch 层），行为与旧版等价

## 3. M3 — EDGAR 归档 URL helper

- [x] 3.1 新建 `lib/edgar/archive-url.js`，导出 `edgarArchiveUrl(cik, accession)` 与 `edgarDocUrl(cik, accession, fileName)`
- [x] 3.2 `lib/edgar/fetch-thirteen-f-xml.js` 改用 `edgarArchiveUrl` / `edgarDocUrl` 构造 `index.json` 与 infoTable URL，删除内联 `cikNoPad` / `accNoDash` / `baseUrl`
- [x] 3.3 `lib/aggregate/pipeline-b.js` 改用 `edgarArchiveUrl` 取代内联 `baseUrl`，`edgarDocUrl(cik, accession, htmlName)` 构造最终文档 URL，删除内联构造

## 4. 测试

- [x] 4.1 新增 `tests/store/atomic-write.test.js`：内容等价（`=== JSON.stringify(obj, null, 2)`）、原子性（无残留 `.tmp`）、写入失败抛错
- [x] 4.2 新增 `tests/edgar/archive-url.test.js`：零填充/已去填充 CIK 归一、doc url 拼接
- [x] 4.3 运行现有 store / edgar / pipeline / verify 相关测试，确认无回归（`vitest run`）

## 5. 验证与收尾

- [x] 5.1 运行 `node --check` 校验所有改动 JS 文件语法
- [x] 5.2 运行 `vitest run` 全量测试通过
- [x] 5.3 运行 `openspec validate refactor-store-and-edgar-utils` 通过
- [x] 5.4 运行 `openspec validate --all` 通过
- [x] 5.5 （可选）手动 `node scripts/verify-edgar.js` 跑通一次，确认限流/请求路径无误

## Notes

- 纯重构，禁止改变既有行为/输出；不触碰 M4/M5/M6 或其它 review 项。
- M1 范围已据 P1-2 实况收窄：仅 `feed-json` / `state-json` / `manifest` 仍用 tmp+rename；`feed-ndjson` / `state-ndjson` 已用 `appendFileSync`，本次仅清理其未使用 import。
- `lib/fetch/fetch-feed.js` 的异步原子写不在本次范围（Non-Goal D1）。
