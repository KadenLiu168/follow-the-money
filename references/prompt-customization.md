# 自定义 Prompt

> **优先级已由代码强制。** 用户副本优先于仓库副本这一规则，现在唯一实现在
> `lib/prompts/resolve.js`（被 `scripts/prepare-digest.js` 调用），并通过输出的
> `renderContext.prompts.<name>.source` 显式声明。本文件是操作说明，不再是优先级
> 的唯一依据——渲染工具应读取 `renderContext` 而非再次猜测顺序。

## 步骤

1. 在用户目录创建 `~/.follow-the-money/prompts/`（如果不存在）
2. 拷贝你想修改的 prompt：
   - macOS / Linux:
     ```bash
     mkdir -p ~/.follow-the-money/prompts
     cp $FTM_SKILL_DIR/prompts/format-13f.md ~/.follow-the-money/prompts/format-13f.md
     ```
   - Windows (PowerShell):
     ```powershell
     New-Item -ItemType Directory -Force -Path $env:USERPROFILE\.follow-the-money\prompts
     Copy-Item $env:FTM_SKILL_DIR\prompts\format-13f.md $env:USERPROFILE\.follow-the-money\prompts\format-13f.md
     ```
3. 编辑用户副本
4. 下次运行 digest 时，`prepare-digest.js` 解析到用户副本，`renderContext.prompts.format_13f.source` 会变为 `"user"`，渲染工具据此使用你的版本

> **注意：** `FTM_SKILL_DIR` 必须是绝对路径指向本仓库根目录。
> 加载顺序（代码强制，唯一实现在 `lib/prompts/resolve.js`）：用户 `~/.follow-the-money/prompts/<file>.md` > 仓库 `prompts/<file>.md`。
