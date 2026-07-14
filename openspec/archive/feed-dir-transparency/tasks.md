## 1. 输出透明化(digest-output)

- [ ] 1.1 `scripts/prepare-digest.js`:在输出 JSON **顶层**新增 `feedDir` 字段,值为已求值的 `FEED_DIR` 绝对路径(`process.env.FOLLOW_THE_MONEY_FEED_DIR || process.cwd()`),输出 JSON 时写入(放顶层,不塞进 `diagnostics`)。
- [ ] 1.2 `scripts/check-alerts.js`:在其 JSON 输出**顶层**新增 `feedDir` 字段(语义同 prepare,取 `FEED_DIR = process.env.FOLLOW_THE_MONEY_FEED_DIR || process.cwd()`),写入输出(放顶层,与 `alerts`/`capped`/`summary` 同级)。

## 2. SKILL.md 去重(documentation-accuracy)

- [ ] 2.1 通读 `SKILL.md` Daily path 步骤 3 与步骤 6,将两段逐字重复的 `--print-dir` 内联 shell 收敛为文档中**只表达一次**的 feed-dir 桥接逻辑(保留「解析失败回退 cwd」分支),步骤 3/6 引用同一处。

## 3. 测试

- [ ] 3.1 `tests/scripts/feed-dir-propagation.test.js`:在既有 env 路径用例中追加断言——输出 JSON **顶层** `feedDir` 存在且等于 `FOLLOW_THE_MONEY_FEED_DIR` 设的目录。
- [ ] 3.2 `tests/scripts/prepare-digest.test.js`:在现有无-env 用例中追加断言——输出 JSON **顶层** `feedDir` 等于 `process.cwd()`(仓库根)。
- [ ] 3.3 运行 `npm test`(聚焦 `feed-dir-propagation` / `prepare-digest`),确认新增断言通过、既有用例不受影响。

## 4. 校验

- [ ] 4.1 `openspec validate feed-dir-transparency` 通过。
- [ ] 4.2 `npm run lint` 干净。
