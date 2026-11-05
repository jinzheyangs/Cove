# Cove

两个人之间，慢慢长出来的一段关系。

Cove 是一个面向情侣的关系经营 App。这个仓库是**后端服务**的源码。

> 状态：功能开发中，尚未发布。

## 技术栈

| 层 | 选型 |
|---|---|
| 语言 / 框架 | Python 3.12 + FastAPI |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| 数据库 | PostgreSQL 16 |
| 缓存 / 队列 | Redis 7 + ARQ |
| 部署 | Docker Compose + uvicorn |
| 包管理 | uv |

## 本地运行

```bash
cp .env.example .env
uv sync
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

> 本地数据库映射到 **55432** 端口，避开机器上可能已有的 5432。

验证：

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

接口文档：<http://localhost:8000/docs>

后台任务（对账、燃尽清理）：

```bash
uv run arq app.worker.WorkerSettings
```

## 测试

```bash
uv run pytest
```

测试会自动创建 `cove_test` 数据库，不影响开发库。

## 架构

经典三层，依赖方向固定为 `router → service → repository`，不许反向。

```
app/modules/<name>/
├── router.py       # 接口层：HTTP 参数、校验、返回
├── service.py      # 业务层：规则、事务边界
├── repository.py   # 数据访问层：所有 SQL 只出现在这里
├── models.py       # 表结构
└── schemas.py      # 请求 / 响应结构
```

跨模块的事务组合：`coins.service` 提供 `mint_locked` / `spend_locked`，
它们不提交事务，调用方把「扣币 + 业务写入」放进同一个事务。

## 模块

| 模块 | 前缀 | 说明 |
|---|---|---|
| 认证 | `/api/v1/auth` | 手机号 + 密码，JWT |
| 用户 | `/api/v1/users` | 当前用户 |
| 情侣 | `/api/v1/couples` | 邀请码绑定、解绑 |
| 金币 | `/api/v1/coins` | 余额、流水、赠与 |
| 金币申请 | `/api/v1/coin-applies` | 申请、审批、拒绝 |
| 秘密树 | `/api/v1/secrets` | 发布、摘取、燃尽、销毁 |
| 商城 | `/api/v1/mall` | 上架审批、购买、核销 |
| 日记 | `/api/v1/diaries` | 共同编辑 / 各自视角 |
| 清单 | `/api/v1/todos` | 共同 / 单人，完成生成纪念卡 |
| 账本 | `/api/v1/bills` | 金钱与非金钱付出、隐私、统计 |
| 争吵 | `/api/v1/conflicts` | 消息、伤害提示、强制复盘 |
| 询问中心 | `/api/v1/inquiries` | 匿名输入、AI 汇总、补充、关闭 |
| 每日一问 | `/api/v1/daily` | 固定题库，每天一题 |
| 模拟TA | `/api/v1/sim-ta` | 授权、忠实度、对话 |
| 审计 | `/api/v1/audit` | 敏感操作记录 |
| 通知 | `/api/v1/notifications` | 站内通知、未读数、已读 |
| 隐私 | `/api/v1/privacy` | 注销账号、导出个人数据 |

## 关键设计决策

- **金币消费 = 销毁**，赠与 = 系统发行。金币是消耗品，不是货币。
- **余额是缓存，流水是真相**，worker 每天 03:17 对账。
- **扣币加行锁**，按 `user_id` 升序，并发下余额不会为负。
- **所有金币写操作有 `idempotency_key` 唯一索引。**
- **阅后即焚**：读后 24 小时内可再看，之后由后台任务清空内容。
- **一键销毁只销毁自己发布的秘密**，不触碰对方的。
- **账本不提供个人对比**，只输出共同视角的汇总。
- **争吵熔断只提示不阻断**，不判定谁对谁错。
- **模拟TA 必须先获得对方授权**，撤销即停用；理想化模式禁止替对方做承诺。

## 可观测性与容错

- **结构化日志**：开发环境彩色输出，生产环境 JSON；每条日志带 `request_id`
- **请求 ID**：读取或生成 `X-Request-ID`，响应头返回，前端报错时可上报
- **日志脱敏**：不记录请求体。秘密、日记、争吵消息只记录 ID
- **审计日志**：销毁秘密、解绑、注销、撤销授权等敏感操作留痕
- **AI 熔断**：连续失败 5 次打开 60 秒，到期半开放一个请求试探
- **AI 重试**：超时 30 秒，失败重试 1 次
- **降级**：AI 不可用时，询问中心保留双方输入并提示稍后再试；
  模拟TA 返回温和提示，不把技术错误甩给用户
- **限流**：按 IP 三档（全局 / 认证 / AI），Redis 故障时放行
- **登录防爆破**：连续失败 5 次锁定 15 分钟
- **指标**：`/metrics` 暴露 Prometheus 指标，可用 `METRICS_TOKEN` 保护
- **链路追踪**：OpenTelemetry + Jaeger，默认关闭；开启后可见 SQL / Redis / AI 调用的耗时瀑布图

运维细节见 [docs/OPERATIONS.md](docs/OPERATIONS.md)。

## 关于检索与模拟TA

`app/modules/ai/retrieval.py` 当前用 PostgreSQL 里的日记与复盘作为上下文，
接口已经隔离，替换成 Chroma + embedding 时业务层不用改。

接入 Chroma 还差一步：需要先确定 embedding 模型
（DeepSeek 不提供 embedding 接口，可选通义 / 智谱 / 本地 BGE）。

## 开发进度

- [x] 项目骨架与三层架构
- [x] 用户注册登录 / 情侣绑定
- [x] 金币账本与申请审批
- [x] 秘密树
- [x] 商城
- [x] 恋爱日记 / 共同清单 / 恋爱账本
- [x] 争吵模式 / 询问中心 / 每日一问
- [x] 模拟TA（授权 + 设置 + 对话）
- [x] 解绑、注销账号、数据导出
- [x] CI/CD、限流、审计、站内通知、指标
- [x] 备份脚本与运维手册
- [ ] 日记导出（长图 / PDF / 短视频）
- [ ] 推送通知（厂商通道）
- [ ] 运营后台
- [ ] Chroma 向量检索
- [ ] 前端
