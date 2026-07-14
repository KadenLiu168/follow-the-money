## 1. resolve.js:async 三级解析器

- [x] 1.1 改写 `lib/prompts/resolve.js` 为 `async resolvePrompts({ names, userDir, repoDir, remoteBaseUrl })`,
  返回 `{ <key>: { source, text } }`,`key` 为去 `.md`、连字符转下划线。`source` ∈ `user | remote | repo | missing`。
  单 name 算法:① `existsSync(join(userDir, name))` → `source:"user"`,读用户文件;
  ② 否则 `fetch(join(remoteBaseUrl, name), { signal })`(`remoteBaseUrl` 由调用方传入、**不带尾斜杠**,
  `join` 自动补分隔符)成功且 `res.ok` → `source:"remote"`,`text = await res.text()`;
  ③ 否则读 `join(repoDir, name)` → `source:"repo"`;④ 三层皆无 → `source:"missing", text:""`。
  远程层用 `AbortController` 设 **5s 超时**;**整个远程尝试包 try/catch,超时 / 网络错误 / 非 2xx /
  `fetch` 缺失均静默 fall through 到 clone 层,resolver 绝不抛错**(保证 `prepare-digest.js` 顶层
  `await` 不会 reject)。并发:用 `Promise.all` 解析全部 name,远程总耗时 ≤ 5s(不串行累积)。
- [x] 1.2 删除 `hashContent` 函数与 `createHash` 导入(resolver 不再产出 `hash`,避免孤儿代码);
  `import { createHash } from 'node:crypto'` 一并移除。

## 2. prepare-digest.js:嵌入正文,删 hash

- [x] 2.1 第 135 行改为 `const resolvedPrompts = await resolvePrompts({ names: PROMPT_NAMES, userDir: join(homedir(),'.follow-the-money','prompts'), repoDir: join(REPO,'prompts'), remoteBaseUrl: 'https://raw.githubusercontent.com/KadenLiu168/follow-the-money/main/prompts' });`(顶层 `await`,`package.json` 为 `"type":"module"` 且 `engines.node >=20.19`,合法)。
- [x] 2.2 第 141-144 行改为 `prompts[key] = { source: r.source, text: r.text }`(无 `hash`);
  保持 `renderContext = { language, prompts }` 入 `out`。

## 3. SKILL.md:直接消费 text

- [x] 3.1 改写 Step4:渲染前读 `renderContext`,对每 prompt 直接读 `renderContext.prompts.<name>.text`
  套用;删除「按 source 定位文件 + 比对 sha256」整段,以及任何读磁盘 prompt 的指示。明确 `source`
  仅作透明信息(`user|remote|repo|missing`),**不得**再写成「`remote` → 某文件路径」——`remote` 没有
  本地路径,LLM 只消费已嵌入的 `text`。

## 4. spec delta(digest-output)

- [x] 4.1 修订 `openspec/specs/digest-output/spec.md`(经本 change 的
  `specs/digest-output/spec.md`):推翻「SHALL NOT embed prompt text」,改为「SHALL embed prompt text」;
  `renderContext.prompts.<name>` 项形状改为 `{ source, text }`,`source` 枚举加 `remote`/`missing`;
  优先级要求改为 `user > GitHub 远程 > repo(clone)` 并写明 5s 超时 + 非 2xx/错误全降级;更新对应 Scenario
  (含「远程层非 2xx/超时/网络错误 → 降级 repo」「resolver 吞掉远程异常绝不抛出」)。
  (主 spec 在 archive 时由本 change 的 spec delta 自动同步,无需手工改 `openspec/specs/`。)

## 5. 测试

- [x] 5.1 **单测(in-process,可 mock 网络)** 更新 `tests/lib/resolve-prompts.test.js`:resolver 现 async,
  全部 `await`。用 `vi.stubGlobal('fetch', ...)` 或 `nock` 模拟 GitHub raw 响应,逐条断言:
  - `user` 副本存在 → `source:"user"` 且 `text` 为用户文件正文(优先级最高,无需网络);
  - 无 user、mock `fetch` 返回 2xx 正文 → `source:"remote"`、`text` 为该正文;
  - 无 user、mock `fetch` **超时/网络错误/返回 404(非 2xx)** → `source:"repo"`、`text` 为 repo 快照;
  - `userDir`/`repoDir` 皆空且 mock `fetch` 失败 → `source:"missing"`、`text:""`;
  - 任意命中 user/remote/repo 的 prompt,`text` 为非空字符串。
- [x] 5.2 **集成测(execSync 子进程,无法继承父进程 `vi.mock`)** 更新 `tests/scripts/prepare-digest.test.js`:
  - `renderContext.prompts.format_13f.text` 为真实非空正文;
  - 输出整体无 `.hash` 字段(任意位置,新增 `hasHashField` 递归校验);
  - 用户副本存在时(HOME 指向临时目录并写入 `~/.follow-the-money/prompts/format-13f.md`)→ `source:"user"`
    (该路径为同步判定,不依赖网络,可确定性 pin);
  - 无 user 覆盖时 `source` 断言为 **`"repo" | "remote"` 之一**(不 pin 具体值——子进程网络不可控);
  - `renderContext` 仅含 `language` 与 `prompts`(`source`/`text`),且不含 `lastAlertTimestamp`/`frequency`;
  - 这些用例务必 `HOME` 指向临时目录,避免真实 home 的 prompt 覆盖污染 `source`。
  - **确定性(time-seam)测试注意**:`produces identical output across runs` 等经 `execSync` 运行、未 mock
    `fetch`,远程层可能触达真实 GitHub。两连跑在「均离线→repo」或「均在线→remote(内容毫秒级稳定)」时
    一致;若 CI 出现 flake,应将相关断言改为 in-process 变体并 mock `fetch`(与 5.1 同机制),而非依赖实时网络。
- [x] 5.3 运行 `npm test` 与 `npx openspec validate 2026-07-13-prompt-contract-embed-text` 全绿(196/196 测试通过,lint 干净,change valid)。
