## Context

`prepare-digest.js` 输出 `renderContext.prompts.<name>` 当前为 `{ source, hash }`,prompt
正文被 `prepare-digest.js` L141-144 刻意 strip,由 LLM 依 `source` 读文件 + 比对 sha256 后渲染。
这是 change `digest-output-self-describing`(2026-07-11)的 O2 决定:尊重项目「LLM 读 prompts
渲染」的设计(`course/index.html` L574-575),故不嵌入文本。

现决定反转该决定,对齐 Follow Builders(O1):脚本完整解析 prompt 并把正文嵌入 JSON,LLM 只消费
`text`。约束与前提:

- 用户已确认原则:确定的事不需要 LLM 做,脚本执行即可。
- 已确认:优先级 `user > GitHub 远程 > repo(clone)`;远程 fetch **5s 超时**;本次范围**仅**
  Prompt 契约一项,不动 feed 目录(#2)/deliver.js(#3)/config schema(#4)/status 契约(#5)。

## Goals / Non-Goals

**Goals:**
- 脚本(`lib/prompts/resolve.js`)拥有完整 prompt 解析:`user > GitHub > clone`,把正文嵌入
  `renderContext.prompts.<name>.text`。
- LLM 直接消费 `text`,不读磁盘、不哈希校验。
- 中心 prompt 改进自动传播(无需 git pull);离线降级到 clone,🅱️ 模式无回归。
- 远程 fetch 受 5s 超时约束,digest 生成不因慢 GitHub 卡住。

**Non-Goals:**
- 不改 `user` 覆盖层(仍为最高优先级)。
- 不嵌入用户 config 状态字段(`lastAlertTimestamp`/`frequency` 等),仍排除。
- 不动 feed 目录耦合、deliver.js、config schema、status 契约(各自独立 change)。
- 不新增服务端渲染脚本(LLM 仍在渲染环,只是不再负责定位/校验 prompt)。

## Decisions

### D1:嵌入完整 prompt 文本,彻底删除 `hash`
`resolvePrompts` 返回 `{ source, text }`,`prepare-digest.js` 把 `text` 写入
`renderContext.prompts.<name>`。删除 `hashContent` 与 `createHash` 导入(改动后成孤儿代码,按
「删因改动而冗余的代码」原则移除)。
- 备选:保留 `hash` 作诊断指纹。否决——它是伪安全(见 Why),且增加 LLM 误用空间;若需指纹,
  可在调试时单独计算,不进契约。

### D2:三级解析 `user > GitHub 远程 > repo(clone)`,resolver 改 async
`resolve.js` 现 `async resolvePrompts({ names, userDir, repoDir, remoteBaseUrl })`,对**每个 name**
执行单名算法:① 用户目录文件存在 → `source:"user"`,读用户文件;② 否则 `fetch(请求地址)`
(见 D3,带 5s 超时)成功且响应 2xx → `source:"remote"`,用响应体;③ 否则回退仓库 `prompts/`
→ `source:"repo"`,读 clone 文件;三层皆无 → `source:"missing"`,`text:""`。
`source` ∈ `user | remote | repo | missing`。**clone 降为离线兜底而非默认**——这是启用「新鲜度」
的必要行为变更(否则 clone 恒在,远程层永不被问)。

- **URL 构造**:`prepare-digest.js` 传入 `remoteBaseUrl`(**不带尾斜杠**,见 tasks 2.1),
  `resolve.js` 用 `join(remoteBaseUrl, name)`(node:path)拼出 `.../prompts/<name>.md`,消除尾斜杠歧义。
- **并发**:resolver 用 `Promise.all` 并发解析所有 name,故无论 prompt 数量多少,远程层总耗时 ≤ 5s,
  不会累积(5 个 prompt 串行最坏 25s 是必须避免的反模式)。
- 备选:保留 `user > repo`、不接 GitHub。否决——那只是「嵌入正文」,不解决新鲜度,与 FB 不对齐。

### D3:远程 fetch 5s 超时 + 全错降级(含非 2xx 与 fetch 不可用)
远程拉取用 `AbortController` 设 5s 超时;`fetch` 在 Node ≥20.19(本仓库 `engines`)为全局可用,
无需 import。以下任一情况 → 静默 fall through 到 clone 层;且 resolver **永不抛错**
(每个 name 的远程尝试包在 try/catch,异常被吞掉,保证 `prepare-digest.js` 的顶层 `await`
不会因网络问题 reject,否则脚本将以非零码崩溃且可能产出部分输出,违背铁律):

- 超时(>5s,AbortError);
- 网络错误(DNS / 连接失败 / 证书等);
- HTTP 非 2xx(典型 404:prompt 已从 main 删除但 clone 仍有快照)——**必须**判 `res.ok`,
  否则会把 "404: Not Found" 当成正文、`source` 误判为 `remote`;
- `fetch` 全局不存在(异常运行环境兜底)。

🅱️ 离线模式:clone 必存在(仓库已 checkout),故始终可降级,无回归。
- 备选:无限等待 / 更短超时。否决——5s 是用户已确认值,平衡「新鲜度」与「不卡 digest」。

### D4:保留 `source` 字段作透明信息(且 Step4 须明确它只是信息,不是路径选择器)
`{ source, text }` 仍含 `source`(命中哪层),便于排查与用户感知覆盖生效。非必需但低成本、无害。
**关键约束(SKILL.md Step4 改写必须遵守)**:`source` 枚举现含 `remote`,但 `remote` 没有对应
本地文件路径;LLM **不得**再把 `source` 映射成「去哪个目录读文件」。Step4 必须改为「直接读
`renderContext.prompts.<name>.text` 套用」,`source` 仅作透明信息展示;旧 Step4 的
「按 source 定位文件 + 比对 sha256」整段删除,且不得保留任何「remote → 某路径」的暗示。

### D5:`missing`(三层皆空)返回 `{ source: "missing", text: "" }`
prompt 文件随仓库提交,clone 层几乎必有,实际不可达;不作硬闸门,prepare 照常继续
(空 text 时无指令可用,属配置错误而非运行时错误)。`missing` 属已知不可达边界,不在
「text 必为非空」不变量内(见 spec ADDED 的对应 Scenario 限定)。

## Risks / Trade-offs

- [Risk] prepare 在 skill 模式新增一次网络调用 → digest 生成依赖 GitHub 可达性。
  → Mitigation:5s 超时 + 非 2xx/网络错误全降级到 clone;clone 恒在,离线仍可用;且 resolver 吞掉
  所有远程异常,绝不抛错,故顶层 `await` 不会 reject、不会触发部分输出。
- [Risk] `renderContext.prompts.*.hash` 破坏性移除,任何依赖方(agent/SKILL)断。
  → Mitigation:本 change 同改 SKILL.md Step4;已 grep 确认 `scripts/`、`lib/` 中无其他代码消费
  `.hash`,无外部 API 消费方。
- [Risk] 反转了 `digest-output-self-describing` 的有意 O2 决定;教学/说明文档现矛盾。
  → Mitigation:列 follow-up doc 更新(出本 change 范围):`course/index.html`(教学「LLM 从磁盘读
  prompts」)与 `references/prompt-customization.md`(仍写「用户 > 仓库」两级优先级)。运行时行为已正确。
- [Trade-off] vs O2:失去「LLM 从磁盘读 prompts」的教学特性,换得简洁、确定性、新鲜度。用户已接受。

## Migration Plan

- 非纯增量:`hash` 移除、`text` 新增;SKILL.md 同 change 改写;测试适配(单测 in-process mock `fetch`,
  集成测 execSync 不 pin 远程层具体 source)。
- 回滚:还原 `resolve.js`/`prepare-digest.js`/`SKILL.md`/测试 + 本 spec delta 即可,不影响数据管线。

## Open Questions

- 无阻塞项。`course/index.html` 与 `references/prompt-customization.md` 的文档漂移为后续 follow-up
  (本 change 只动运行时行为与 SKILL.md 操作说明)。
