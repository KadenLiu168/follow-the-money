## 1. M6 — pipeline-a 单次落盘（代码重构，行为保持）

- [x] 1.1 在 `lib/store/feed-json.js` 抽出纯函数 `merge13FFiling(feed, entry)`：承接现 `upsert13FFiling` 内部逻辑（盖 `valueUnit:'thousands'` + 按 `accessionNumber` 去重合并 `history` + `computeStats`），返回新 feed，不读写磁盘
- [x] 1.2 将 `upsert13FFiling` 改为 `writeFeedJson(path, merge13FFiling(readFeedJson(path), entry))` 薄封装，保留 API / 测试兼容
- [x] 1.3 `lib/aggregate/pipeline-a.js`：循环内改为 `feed = merge13FFiling(feed, entry)` 累积（保留 `seenFilings` 标记与内存 feed 同步），删除循环内 `upsert13FFiling` 的磁盘写；循环结束后 `writeFeedJson(feedPath, feed)` 一次性落盘
- [x] 1.4 更新 `tests/store/feed-json.test.js` 覆盖 `merge13FFiling`（盖戳 + history 合并 + stats）；确保 `tests/aggregate/pipeline-a.test.js` 断言末次单次写盘、端到端行为不变

## 2. M4 — README 🅱️ 输出澄清（文档）

- [x] 2.1 修改 `README.md` step 4（约 L165）：说明 🅱️ 本地模式输出 digest JSON（`print.js` 仅回显 JSON），markdown 渲染是 🅰️ agent 模式的事；删除"你会看到一份 markdown 摘要"不实承诺

## 3. M5 — CI 测试门禁（配置）

- [x] 3.1 在 `.github/workflows/aggregate.yml` 的 `npm ci` 之后、`node scripts/aggregate.js` 之前插入 `npm test` 步骤

## 4. 校验

- [x] 4.1 `node --check` 改动 JS；`npm test` 全绿；`openspec validate medium-followups` + `openspec validate --all` 通过
