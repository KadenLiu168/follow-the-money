# 操作手册（中文）

## 配置

```bash
uv sync --frozen --all-groups
cp .env.example .env   # 填入 OPENAI_API_KEY / OPENAI_MODEL
```

仓库只读取显式的 `--config` / `--output-root` 路径，绝不隐式读取
`~/.follow-the-money/config.json`。已配置的密钥必须至少 8 个 UTF-8 字节，
且绝不写入日志。

## Feed 生成

```bash
# 试运行（不发布）：
uv run follow-the-money feed --dry-run

# 真实运行，指定输出根：
uv run follow-the-money feed --output-root feeds
```

退出码：`0` = 健康或降级 Feed（警告在 stderr/status）；`1` = 生成/发布失败；
`2` = 用法/配置错误。不需要金融数据或 LLM 凭据。

## 完整 Brief

```bash
uv run follow-the-money brief \
  --feed feeds/latest.json \
  --output out.md \
  --status-file brief-status.json
```

需要一个 OpenAI 凭据与一个兼容模型。只有在原子 run bundle 提交后才进行
交付；bundle 内的 Markdown 是权威产物。

## 确定性降级报告

```bash
uv run follow-the-money brief --degraded-report --feed feeds/latest.json --output degraded.md
```

仅在显式请求时产出；绝不标记为正常《晨间资金简报》；无需 LLM。

## 重放（Replay）

```bash
uv run follow-the-money replay runs/<brief_run_id>/
```

完全离线，无网络/LLM 调用。任何构建/完整性/篡改/漂移不一致即退出 `1`。

## 测试

```bash
uv run pytest                 # 全量免凭据测试
uv run follow-the-money eval  # golden-day 数据集校验
```

## 评估

离线：`uv run follow-the-money eval --mode offline`（默认；fixture 无效或
门禁失败退出 1）。在线（需凭据、opt-in）：`--mode live`、重复次数、
`--max-cost-usd`；要求本地价格表；`incomplete` 退出 1。

## GitHub 部署

定时 Feed 工作流（`generate-feed.yml`）是模板。启用前：

1. 设置 `FOLLOW_THE_MONEY_FEED=true`（仓库/环境变量）。
2. 准备一台带 `follow-the-money-feed` 标签的专用 self-hosted runner。
3. 挂载持久化共享输出根（每次调用共享），其中包含部署持久化标记
   （`.follow-the-money-persistent`）与可写可读的持久速率状态路径。
4. 授予 `contents: write` 并确认分支策略（受保护分支拒绝会显式失败，
   输出以上传 artifact 保留）。

同一 provider/rate scope 的跨根并发使用不受支持：共享 provider scope 的
协作 CLI 进程必须共享同一输出根（应用级采集锁以输出根为根）。

## 持久输出根注册表（运维契约）

- 输出根包含 `rate-registry.json`（带版本）+ 每个 `scope_id` 一个状态文件，
  均在采集锁保护下通过同目录原子替换 + 文件/父目录 `fsync` 更新。
- 新 scope：可恢复的 `initializing -> 满容量状态 -> active` 首次使用序列。
  仅当验证无请求被受理后才能补完 `initializing` 条目。
- active scope 状态缺失/损坏/未知 schema，或已标记持久根注册表缺失/损坏，
  一律 fail closed。
- 策略变更使用显式零发送保守迁移（新指纹、零令牌、冷却不早于旧冷却与
  当前时间+新补满周期），绝不隐式重置。
- 墙钟回拨不发放令牌；补满只使用非负注入 UTC 流逝时间。
- 每次可能发送前持久扣减一枚令牌并安装 24 小时崩溃冷却；确认发送前失败
  可退款；受控终态保留扣减但按策略/`Retry-After` 对账。

## 外部调度

将外部投递计划与成功发布 Feed 对齐。在输入截止时间可用之前不要运行
Brief；v1 将超过 30 分钟的滞后标记为 stale，超过 2 小时拒绝正常模式。

## 已知限制

- 在线模型输出不确定；重复在线评估是证据而非发布门禁。
- 带版本的启发式分数对缺失数据有偏；已暴露组件覆盖率，且优先级分数
  绝非收益或投资建议。
- 语言审计由生成语言的同一模型执行：这是有界编辑检查，而非独立保证。
- 本仓库不是 Git checkout，且未经另行授权不包含已启用工作流或 license。
