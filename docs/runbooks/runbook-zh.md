# 操作手册（中文）

## 配置

```bash
uv sync --frozen --all-groups
```

确定性引擎完全免凭据：任何情况下都不需要 API key 或模型。仓库只读取显式
的 `--config`、`--output-root` 与 `--runtime-state-root` 路径，绝不隐式读取
`~/.follow-the-money/config.json`。

## Feed 生成

```bash
# 试运行（不发布）：
uv run python -m follow_the_money.feed.cli --dry-run
# 或：scripts/feed/follow-the-money-feed --dry-run

# 使用仓库输出根进行本地真实运行：
uv run python -m follow_the_money.feed.cli --output-root feeds \
  --runtime-state-root .feed-state \
  --status-file feed-status.json
```

退出码：`0` = 健康或降级 Feed（警告在 stderr/status）；`1` = 生成/发布失败；
`2` = 用法/配置错误。不需要任何凭据。

## GitHub 部署

`generate-feed.yml` 已在 GitHub-hosted `ubuntu-latest` 上启用，按
`20 0 * * *`（Asia/Shanghai 08:20）运行，也支持 `workflow_dispatch`。工作流使用
`feeds/` 保存 Feed product，`.feed-state/` 保存仓库内 RateRegistry、lease、lock
与 checkpoint；运行开始后才捕获实际 cutoff，08:20 只是调度时刻。

在宣称部署可运行前，必须验证仓库 Actions `contents: write` 权限，以及分支策略允许
工作流身份向 `main` 执行普通 fast-forward commit。

### 首次 bootstrap 与恢复

1. 首次 bootstrap 前停用旧的 external 调度器；不要导入无法验证的状态。
2. 手动 dispatch `generate-feed.yml`。工作流先静态解析配置、resolved Provider
   contract 与双根 layout。完整 legacy layout 会在不请求 Provider 的情况下迁移；
   干净仓库创建 RateRegistry marker、registry、精确 scope 文件、显式 null checkpoint
   和 `bootstrap` lease。两种路径都通过普通 fast-forward commit 发布，并在 migration/
   bootstrap 后结束，不进入 collection。
3. 读取 `.feed-state/feed-run-lease.json`，等待 `recovery_not_before`。边界之前的运行会
   fail closed，不会重置状态。
4. 再次 dispatch。Feed 执行前先发布 `in_progress` 及所需状态，受控完成后再发布终态
   精确状态。若 runner 或最终发布失败，远端 `in_progress` 继续作为恢复信号。

工作流绝不 force-push 或 destructive reset。arming 阶段发生普通 fast-forward 冲突时，
Provider 工作尚未开始；Provider 工作之后的最终发布冲突则保留远端 `in_progress`。

### 生成状态 allowlist 与回滚

部署 helper 只能发布以下路径：

- `.feed-state/.follow-the-money-persistent`
- `.feed-state/rate-registry.json`
- bootstrap/migration 与 success finalization 才纳入的 `.feed-state/feed-checkpoint.json`
- registry 指名的精确 `.feed-state/scope-<digest>.json`
- `.feed-state/feed-run-lease.json`
- `feeds/latest.json`（唯一的成功 Feed product）

锁、status、staging、临时文件、bundle、legacy product 文件、debug/failure workspace
均在 allowlist 之外，绝不 staging。回滚使用 GitHub 原生 workflow-disable，保留最后远端
lease 与速率状态；不要
reset 生成状态，也不要从不确定运行状态重启外部调度器。

## 测试

```bash
uv run pytest
uv run python scripts/quality_gate.py
```

quality gate 包含 workflow validator、CI 中的 actionlint、lint、format、type-check、
免凭据测试套件与离线 wheel 构建。

## 持久 runtime-state 注册表

同一 Provider/rate scope 的跨根并发使用不受支持：共享 scope 的协作进程必须共享同一
runtime-state 根。

- runtime-state 根包含带版本的 `rate-registry.json` 与每个 `scope_id` 的状态文件，均在采集锁
  下通过同目录原子替换及文件/父目录 `fsync` 更新。
- 新 scope 使用可恢复的 `initializing -> 满容量状态 -> active` 首次使用序列；只有
  验证没有请求被受理时才能补完 `initializing` 条目。
- active scope 状态缺失、损坏、未知 schema，或已标记持久根的 registry 缺失/损坏，
  一律 fail closed。
- 墙钟回拨不发放令牌；补满只使用非负注入 UTC 流逝时间。
- 每次可能发送前持久扣减一枚令牌并安装 24 小时临时崩溃冷却；确认发送前失败可退款；
  受控终态保留扣减并按策略/`Retry-After` 对账。

## 已知限制

- 带版本的启发式分数对缺失数据有偏；已暴露组件覆盖率，优先级分数绝非收益或投资建议。
- 保留的 scoring/selection 规则与 `ClaimAuditor` 目前没有生产调用者；结构化 Agent
  交付契约留待未来 Change。
