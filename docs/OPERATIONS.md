# 运维手册

## 备份

```bash
BACKUP_PASSPHRASE='你的口令' bash scripts/backup_db.sh backup
```

流程：`pg_dump` → `gzip` → AES-256 加密 → 写入 `backups/`，默认保留 30 天。

**备份必须加密。** 未加密的 dump 里是用户全部的秘密和日记。

把 `backups/` 定期同步到对象存储（OSS / COS），不要只留在同一台机器上。

## 恢复

```bash
BACKUP_PASSPHRASE='你的口令' bash scripts/backup_db.sh restore backups/cove-20260101-030000.sql.gz.enc
```

**每月至少演练一次恢复。** 没演练过的备份等于没有备份。

## 迁移

```bash
uv run alembic upgrade head       # 应用迁移
uv run alembic current            # 查看当前版本
uv run alembic downgrade -1       # 回退一步
```

上线顺序：**先备份 → 再迁移**。迁移前确认新代码与旧表结构兼容。

## 限流参数

| 变量 | 默认 | 说明 |
|---|---|---|
| `RATE_LIMIT_REQUESTS` | 120 | 每 IP 每分钟总请求数 |
| `AUTH_RATE_LIMIT_REQUESTS` | 10 | 认证接口每分钟 |
| `AI_RATE_LIMIT_REQUESTS` | 30 | AI 接口每分钟 |
| `LOGIN_MAX_ATTEMPTS` | 5 | 登录失败锁定阈值 |
| `LOGIN_LOCK_SECONDS` | 900 | 锁定时长 |

Redis 不可用时限流会放行（fail open），不会拖垮服务。

## 监控

- `GET /health`：进程存活
- `GET /health/db`：数据库连通
- `GET /metrics`：Prometheus 指标（建议只在内网暴露，可设 `METRICS_TOKEN`）

关键指标：

| 指标 | 说明 |
|---|---|
| `cove_http_requests_total` | 请求量，按方法/路径/状态码 |
| `cove_http_request_duration_seconds` | 延迟分布 |
| `cove_ai_calls_total` | AI 调用结果：success / failure / circuit_open |

建议告警：

- 5xx 比例 > 1%
- `cove_ai_calls_total{result="circuit_open"}` 持续增长
- worker 日志出现「金币对账不一致」

## 日志

- 生产环境是 JSON 行，直接接 Loki / ELK / 云日志服务
- 每条日志带 `request_id`，响应头 `X-Request-ID` 可以对应上
- 日志**不记录请求体**：秘密、日记、消息都不会落盘

排查顺序：请求 ID → 路径 → 状态码 → 耗时 → 异常栈。

## 对象存储

开发环境默认用本地目录：

```env
STORAGE_BACKEND=local
UPLOAD_DIR=./uploads
```

文件通过 `/uploads/{key}` 访问，只适合本地开发。

生产环境切到阿里云 OSS：

```bash
uv sync --extra oss
```

```env
STORAGE_BACKEND=oss
OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=your-bucket
OSS_ACCESS_KEY_ID=...
OSS_ACCESS_KEY_SECRET=...
# 私有桶，读取时生成签名 URL
OSS_PRIVATE=true
STORAGE_URL_EXPIRE_SECONDS=3600
```

要点：

- 数据库只存 object key，不存 URL
- 私有桶返回的是**有有效期的签名 URL**，不能入库
- 建议给 bucket 配置 CDN 和生命周期规则
- `scripts/generate_api_doc.py` 不用改，上传接口会自动出现在文档里

## 数据加密

```bash
openssl rand -base64 32    # 写入 DATA_ENCRYPTION_KEY
```

开启后以下字段在数据库里是密文（AES-256-GCM）：

- 秘密内容 `secrets.content`
- 日记标题与正文 `diaries.title/content`
- 争吵消息与复盘 `conflict_messages` / `conflict_reviews`
- 询问中心的问题、AI 分析、输入与补充 `inquiry_sessions` / `inquiry_inputs` / `inquiry_supplements`
- 每日一问回答 `daily_answers.answer`
- 账本备注 `bills.remark`

**没有加密**的：金币流水、商城、账单金额、通知。这些要么是双方共用的账目，
要么是结构化数据，加密收益低。

历史明文数据用一次性脚本转换：

```bash
uv run python scripts/encrypt_existing_data.py
```

注意：

- 换 `DATA_ENCRYPTION_KEY` 会导致旧数据无法解密，换之前必须先备份并重新加密
- 这是服务端加密，不是端到端加密；拿到服务器和密钥的人仍可解密
- 加密列不能做 `LIKE` / 全文检索

## 告警

```bash
docker compose --profile monitoring up -d
# Prometheus  http://localhost:9090
# Alertmanager http://localhost:9093
```

规则在 `deploy/prometheus/alerts.yml`：

| 告警 | 条件 |
|---|---|
| `CoveApiDown` | 指标抓取失败 2 分钟 |
| `CoveHigh5xxRate` | 5xx 比例 > 1%，持续 5 分钟 |
| `CoveHighLatency` | P95 > 1s，持续 10 分钟 |
| `CoveAiCircuitOpen` | AI 熔断器打开 1 分钟 |
| `CoveAiHighFailureRate` | AI 失败率 > 20%，持续 10 分钟 |
| `CoveCoinReconcileMismatch` | 对账不一致账户数 > 0 |

通知渠道在 `deploy/alertmanager/alertmanager.yml`。
**钉钉/飞书不能直接填机器人地址**，需要先部署一个格式转换服务（如
`prometheus-webhook-dingtalk`），否则收到的消息是乱格式。

如果设置了 `METRICS_TOKEN`，Prometheus 抓取会被 403 拒绝。
要么留空（依赖内网隔离），要么给 Prometheus 配上请求头。

## 链路追踪

默认关闭。开启后 FastAPI / SQLAlchemy / Redis / httpx 自动打点，
包括 OpenAI SDK 的模型调用，统一导出到 Jaeger。

```bash
# .env
OTEL_ENABLED=true
OTEL_EXPORTER_ENDPOINT=http://jaeger:4318/v1/traces
OTEL_SAMPLE_RATIO=1.0

docker compose up -d jaeger
# UI: http://localhost:16686
```

能看到一条请求里每个 SQL、Redis 操作、AI 调用的耗时瀑布图。

生产环境建议把 `OTEL_SAMPLE_RATIO` 降到 0.1 以下，避免追踪存储被打满。

## 上线检查清单

- [ ] `.env` 里的密钥不是默认值（`JWT_SECRET`、数据库密码、`BACKUP_PASSPHRASE`）
- [ ] `ENV=prod`，`DEBUG=false`
- [ ] HTTPS 已配置，`CORS_ORIGINS` 只放行真实域名
- [ ] `METRICS_TOKEN` 已设置，或 `/metrics` 不对公网开放
- [ ] 如开启链路追踪，`OTEL_SAMPLE_RATIO` 已按流量调低，Jaeger 端口不对公网开放
- [ ] 数据库端口没有映射到公网
- [ ] 备份任务已配置并跑通一次恢复
- [ ] `alembic upgrade head` 已执行
- [ ] worker 已启动（对账、燃尽清理依赖它）
- [ ] 隐私政策 / 用户协议 / 备案已完成
