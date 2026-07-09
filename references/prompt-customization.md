# 自定义 Prompt

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
4. 下次运行 digest 时会自动优先用用户版本

> **注意：** `FTM_SKILL_DIR` 必须是绝对路径指向本仓库根目录。
> 加载顺序：用户 `~/.follow-the-money/prompts/<file>.md` > 仓库 `prompts/<file>.md`。
