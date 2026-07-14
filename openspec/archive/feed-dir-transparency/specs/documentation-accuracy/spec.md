## ADDED Requirements

### Requirement: SKILL.md SHALL express the feed-dir bridge once, not per step
`SKILL.md` Daily path SHALL 在文档中**只表达一次**「把 `fetch-feed.js` 解析出的 feed 目录桥接给
`prepare-digest.js` / `check-alerts.js`」的逻辑,供步骤 3(prepare)与步骤 6(check-alerts)共同引用;
SHALL NOT 在两处冗余地各自内联完整的 `--print-dir` 解析 + `FOLLOW_THE_MONEY_FEED_DIR` 赋值逻辑。

#### Scenario: feed-dir bridge not redundantly expressed across steps
- **WHEN** 读者检查 `SKILL.md` Daily path 的步骤 3 与步骤 6
- **THEN** 不得在两处各自完整内联「`node scripts/fetch-feed.js --print-dir` 并重新赋值
  `FOLLOW_THE_MONEY_FEED_DIR`」的桥接逻辑(无论两段是否字节级相同)
- **AND** 步骤 3 与步骤 6 对 feed 目录的解析/传递 SHALL 引用同一处定义(或等价地各自简短调用同一封装)

#### Scenario: fallback-to-cwd branch preserved in the single expression
- **WHEN** 文档描述 fetch 不可用时的本地回退
- **THEN** 那段唯一的 feed-dir 桥接逻辑 SHALL 仍包含「解析失败则回退 `node ... prepare-digest.js`(即 `|| cwd`)」的分支
- **AND** 不得因去重而删除该回退分支(否则破坏 `fetch-feed.js` 缺失时的韧性)
