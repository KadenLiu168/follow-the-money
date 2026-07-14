## Why

`scripts/prepare-digest.js` 当前在 `renderContext.prompts.<name>` 只输出
`{ source, hash }`,把 prompt **正文丢弃**,再由 `SKILL.md` Step4 要求 LLM 按 `source`
去磁盘读文件、自己算 sha256 比对后再渲染。这一设计来自 change
`digest-output-self-describing`(2026-07-11)的**有意选择 O2**:该 change 以
`course/index.html`「把 LLM 读 prompts 渲染当特性」为由,明确**不**把 prompt 文本嵌入
JSON,只暴露来源 + 哈希。

与参考实现 Follow Builders 对比后,该选择暴露三个问题,现决定**反转回 O1(对齐 FB)**:

1. **sha256 是伪安全**。`hash` 只重新确认 `resolve.js` 同一时刻读的那个文件,无法捕捉跨
   版本漂移;且 `SKILL.md` 把比对写成 "confirm"(确认)而非硬闸门,真 mismatch 时 LLM 可能带着
   错误 prompt 继续渲染。它验证的不是完整性,只是微秒级文件未变。
2. **确定性工作被推到最不可靠的环节**。脚本已算出正确正文,却丢弃,逼 LLM 重新读文件 + 哈希
   —— 违反 single-source-of-truth,也违反「确定的事不需要 LLM 做」的原则。
3. **prompt 不新鲜**。当前优先级 `user > repo(clone)`,clone 是快照;中心在 GitHub 改了
   prompt,用户须手动 `git pull` 才生效。FB 用 `user > GitHub > local` 让中心改进自动传播。

推翻 O2 的理由:「把指令混进数据契约不安全」这一担忧不成立——prompt 是项目自写字段,feed
数据(`thirteenF`/`thirteenDG`)是独立字段,无注入面;指令在独立 `prompts` 命名空间内对 LLM
完全安全(FB 即如此)。

## What Changes

- `lib/prompts/resolve.js`:改为 `async`,三级优先级 `user > GitHub 远程 > repo(clone)`;
  返回 `{ source, text }`(**删除 `hash` 与 `hashContent`/`createHash`**)。远程拉取带 **5s
  超时 + AbortController**,失败/超时/**非 2xx 响应**/fetch 不可用均降级到 clone,且 resolver
  吞掉所有远程异常绝不抛出。`source` ∈ `user | remote | repo | missing`。
- `scripts/prepare-digest.js`:`await resolvePrompts(...)` 传入 `remoteBaseUrl`
  (`raw.githubusercontent.com/KadenLiu168/follow-the-money/main/prompts`);在
  `renderContext.prompts.<name>` 嵌入 `text`,去除 `hash` 字段。
- `SKILL.md` Step4:直接读 `renderContext.prompts.<name>.text` 套用;删除「按 source 读文件
  + 比对 sha256」整段。
- `tests/`:适配新 shape(`text` 非空、无 `hash`、`source` 可为 `remote`/`missing`;resolver
  现 async + 需 mock `fetch`/离线降级)。
- 修订 `digest-output` capability spec:推翻「SHALL NOT embed prompt text」,更新 prompt 项
  形状与优先级(含 GitHub 远程层 + 5s 超时)。

## Capabilities

### Modified Capabilities
- `digest-output`:prompt 契约部分——`renderContext.prompts.<name>` 形状由
  `{ source, hash }` 改为 `{ source, text }`;解析优先级由 `user > repo` 改为
  `user > GitHub 远程 > repo(clone)`;推翻「SHALL NOT embed prompt text」,改为
  「SHALL embed prompt text」。用户 config 状态字段(`lastAlertTimestamp`/`frequency` 等)
  仍 SHALL NOT 嵌入。

## Impact

- 代码:`lib/prompts/resolve.js`、`scripts/prepare-digest.js`、`SKILL.md`、相关测试。
- 契约:`renderContext.prompts.<name>` 形状变更(`hash` 移除、`text` 新增)。**对仅由 LLM/SKILL
  消费的字段属破坏性变更,但无外部 API 消费方**;同 change 内 SKILL.md 已同步改写。
- 文档:`SKILL.md` Step4 改写。`course/index.html`(教学「LLM 从磁盘读 prompts」)与
  `references/prompt-customization.md`(仍写「用户 > 仓库」两级优先级)将与新行为矛盾 ——
  **均列为后续 follow-up,不在本 change 范围**(本 change 只动运行时行为与 SKILL.md 操作说明)。
- 测试:`tests/lib/resolve-prompts.test.js`、`tests/scripts/prepare-digest.test.js` 适配。
