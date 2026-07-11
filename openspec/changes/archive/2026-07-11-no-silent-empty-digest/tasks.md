## 1. 拆分 readFeedJson 语义（lib/store/feed-json.js）

- [x] 1.1 将 `readFeedJson` 重命名为 `readFeedJsonOrInit`，保留 `DEFAULTS()` 回退（缺失/损坏均返回空 feed），并更新文件内 export。
- [x] 1.2 新增 `readFeedJsonStrict(path)`：文件不存在 → 抛 `Error('feed-13f.json missing at <path>')`；`JSON.parse` 失败 → 抛 `Error('feed-13f.json corrupt at <path>: <msg>')`；成功 → 返回与现有一致的规范化对象（`...DEFAULTS()、...parsed、thirteenF、stats`）。
- [x] 1.3 `upsert13FFiling`（feed-json.js:75）内联的 `readFeedJson(path)` 改为 `readFeedJsonOrInit(path)`。

## 2. 更新 bootstrap 调用方

- [x] 2.1 `lib/aggregate/pipeline-a.js:10` 的 `readFeedJson(feedPath)` 改为 `readFeedJsonOrInit(feedPath)`（行为不变）。

## 3. prepare-digest 硬失败（scripts/prepare-digest.js）

- [x] 3.1 移除原 `const f13 = existsSync(FEED_13F) ? readFeedJson(FEED_13F) : { thirteenF: [] };`，改为 pre-flight：`!existsSync(FEED_13F)` 或 `!existsSync(FEED_13DG_DIR)` → `console.error('[prepare-digest] <源> missing — run fetch-feed.js or aggregate.js')` + `process.exit(1)`。
- [x] 3.2 `f13 = readFeedJsonStrict(FEED_13F)` 包 try/catch，捕获则 `console.error('[prepare-digest] ' + e.message)` + `process.exit(1)`。
- [x] 3.3 移除 `manifest` 的缺省 else 分支（目录已保证存在，`readManifest` 按现状处理目录内 manifest）；保留 `validateManifest` 的 warn。

## 4. 测试

- [x] 4.1 `tests/store/feed-json.test.js`：import 与用例中的 `readFeedJson` 引用改名 `readFeedJsonOrInit`；"returns defaults when missing" 用例保持；新增 `readFeedJsonStrict` 缺失抛错、损坏抛错两个用例。
- [x] 4.2 `tests/scripts/prepare-digest.test.js`：更新 "reads from envDir when set, even if envDir is empty"（约 :176）用例——改为断言 `execSync` 抛出、`err.status !== 0`、stderr 含 "missing"，保留"env var 不被静默忽略"的意图（从空 digest 转为硬失败）。
- [x] 4.3 新增 prepare 集成用例：分别构造（a）缺 `feed-13f.json`、（b）缺 `feed-13dg/`、（c）`feed-13f.json` 为非法 JSON 三种环境，均断言非零退出且 stdout 为空。

## 5. 文档与验证

- [x] 5.1 `SKILL.md` 错误处理段补充：prepare 现于源缺失/损坏时非零退出，agent 须上报 stderr 并停止，不再产出空 digest。
- [x] 5.2 验证：跑 `npm test`（vitest）全绿；手动 `rm -rf` 缓存目录后跑 `node scripts/prepare-digest.js` 确认非零退出且 stdout 为空；真实数据存在时正常出 digest、`exit 0`；确认非 filing 日的"源存在但无窗口内申报"仍 `exit 0` 出空数组 digest。
