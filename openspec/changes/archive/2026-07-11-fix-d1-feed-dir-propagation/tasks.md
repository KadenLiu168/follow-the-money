## 1. Add `--print-dir` to `scripts/fetch-feed.js`
→ 验证: `node scripts/fetch-feed.js --print-dir` 打印 `defaultTargetDir()` 结果并 exit 0，且不发起任何网络请求（stub `fetch` 断言未被调用）。`defaultTargetDir()` 仍被导出，现有 `tests/scripts/fetch-feed.test.js` 全绿。

## 2. 改写 `SKILL.md` Daily path（Step 2/3/6）
→ 验证: 在干净 clone 中跑 SKILL 的 daily-path shell 块，fetch 成功时 `prepare-digest.js` 的 `FEED_DIR` 等于 `fetch-feed.js --print-dir` 的输出（即缓存目录）；digest 的 `stats.thirteenFFilings` > 0（上游有数据时），证明读到了新鲜数据而非 repo 旧文件。fetch 失败时回落到无 env 的 cwd 分支。

## 3. 新增 flow 测试（fetch → prepare 一致性）
→ 验证: 用空临时目录 `TMP`（设 `FOLLOW_THE_MONEY_FEED_DIR=$TMP`）跑 `fetch-feed.js` 写入 `feed-13f.json`；再以 `FOLLOW_THE_MONEY_FEED_DIR=$TMP` 跑 `prepare-digest.js`，断言其读到的 `thirteenF` 条数与 fetch 写入一致。对照组：env 取消时 prepare 读 `cwd`。测试在 `tests/` 下新增。

## 4. `openspec validate fix-d1-feed-dir-propagation`
→ 验证: `openspec validate` 通过（proposal / tasks / spec 结构合法）。
