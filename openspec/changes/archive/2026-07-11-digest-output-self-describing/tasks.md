## 1. 新增基础加载器

- [x] 1.1 新增 `lib/config/load-user-config.js`,导出 `loadUserConfig()`:读取
  `~/.follow-the-money/config.json`,缺失/不可读/解析失败时返回 `{ language: "en" }`,
  含 `language` 时原样返回。不抛异常。
- [x] 1.2 新增 `lib/prompts/resolve.js`,导出 `resolvePrompts({ names, userDir, repoDir })`:
  对每个 name 按 `user > repo` 优先级解析,返回 `{ <key>: { source, text?, hash } }`,
  `key` 为去 `.md`、连字符转下划线;`hash` 为内容 sha256 前 16 位(用 Node 内置 `crypto`)。

## 2. prepare-digest 输出改造

- [x] 2.1 在 `prepare-digest.js` 引入 `loadUserConfig()` 与 `resolvePrompts()`,解析
  `userDir = join(homedir(),'.follow-the-money','prompts')`、`repoDir = 仓库 prompts/`。
- [x] 2.2 收集 `validateManifest` 的 `v.warnings` 与 feed 读取失败到 `warnings: string[]`,
  保留 `console.warn`,同时写入 `out.warnings`。
- [x] 2.3 构建 `renderContext = { language, prompts }`(prompts 仅含 `source`/`hash`,不含 text),
  加入 `out`,保持 `JSON.stringify(out, null, 2)` 输出。

## 3. check-alerts 迁移

- [x] 3.1 将 `scripts/check-alerts.js` L13 的内联 `CONFIG_PATH` 替换为调用 `loadUserConfig()`,
  行为等价(路径与回退一致),删除重复路径构造。

## 4. 文档同步

- [x] 4.1 改写 `SKILL.md` Step4:渲染前先读 `renderContext`,按 `prompts.*.source`/`hash`
  选择并核实 prompt 版本,而非自行猜测 user>repo 优先级。
- [x] 4.2 更新 `references/prompt-customization.md`:说明优先级已由 `lib/prompts/resolve.js`
  代码强制,文档降为说明而非唯一依据。

## 5. 测试

- [x] 5.1 `tests/scripts/prepare-digest.test.js`:人为制造 manifest count mismatch,断言
  输出 `warnings` 非空且含该 mismatch 描述;year 文件缺失同理;干净运行 `warnings` 为 `[]`。
- [x] 5.2 同一测试文件:断言 `renderContext.language` 在 config 缺失时回退 `"en"`、存在时为
  实际值;`renderContext.prompts.format_13f.source` 在用户副本存在时为 `"user"`、仅仓库存在时为 `"repo"`。
- [x] 5.3 新增 `tests/lib/load-user-config.test.js`:缺失/损坏/无 language 均回退 `{ language: "en" }` 且不抛。
- [x] 5.4 新增 `tests/lib/resolve-prompts.test.js`:验证 user>repo 优先级与 hash 计算正确。
- [x] 5.5 运行 `npm test` 与 `npx openspec validate digest-output-self-describing` 全绿。
