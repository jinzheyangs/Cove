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

接口文档：

- 在线试用：<http://localhost:8000/docs>
- 前端接口表：[docs/API.md](docs/API.md)
- OpenAPI JSON（可导入 Apifox / Postman）：[docs/openapi.json](docs/openapi.json)

重新生成：

```bash
uv run python scripts/generate_api_doc.py
```

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
| 上传 | `/api/v1/uploads` | 日记图片上传、删除 |
| AI 对话 | `/api/v1/agent` | 多轮人格对话、会话管理 |
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

## 图片上传

`POST /api/v1/uploads/diary-image`（multipart）上传日记图片，返回 `key` 和 `url`。

- 数据库存 **key**，展示时用服务端生成的 **url**
- 开发环境：`STORAGE_BACKEND=local`，文件落到 `./uploads`，通过 `/uploads` 访问
- 生产环境：`STORAGE_BACKEND=oss`，并安装 OSS 依赖：`uv sync --extra oss`
- 私有 OSS 桶返回的是带时效的签名 URL，**不要把它存进数据库**

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
- **字段加密**：秘密、日记、争吵、询问等私密内容 AES-256-GCM 加密存储
- **令牌生命周期**：access token 30 分钟，refresh token 可轮换、可吊销

运维细节见 [docs/OPERATIONS.md](docs/OPERATIONS.md)。

## 模拟TA 的 RAG

链路：

```
日记 / 复盘写入
    ↓ 事务提交后入队（ARQ）
切片 → embedding → Chroma
    ↓
用户提问 → embedding → Chroma top-k（按 couple_id + user_id 过滤）→ prompt → LLM
```

设计原则：

- **PG 是真相，Chroma 是可重建的索引**；`chunk_index` 表记录映射
- 内容没变不重新 embedding（`content_hash`）
- embedding 未配置或 Chroma 不可用时，自动退回「最近日记 + 复盘」
- 撤销模拟TA 授权、注销账号会删除对应向量
- 检索只读被模拟者自己的记录，不会混入用户自己的内容

配置（embedding 走 OpenAI 兼容接口，供应商可换）：

```env
RAG_ENABLED=true
CHROMA_HOST=chroma
CHROMA_PORT=8000
CHROMA_COLLECTION=cove_persona
RAG_TOP_K=5
RAG_CHUNK_SIZE=400
RAG_CHUNK_OVERLAP=50

EMBEDDING_API_KEY=...
EMBEDDING_BASE_URL=...
EMBEDDING_MODEL=...
```

重建某个用户的索引：

```bash
uv run python scripts/reindex_user.py <couple_id> <user_id>
```

## AI 多轮对话

模拟TA 的对话入口是 `/api/v1/agent`，不是单次问答：

```
POST /agent/conversations                        新建会话
POST /agent/conversations/{id}/messages/stream   发消息，SSE 流式返回
GET  /agent/conversations/{id}                   查看历史
DELETE /agent/conversations/{id}                 删除会话和消息
POST /agent/actions/{id}/confirm                 确认 Agent 提议的写操作
POST /agent/actions/{id}/cancel                  取消提议
```

只有一个对话接口，流式返回，工具调用也在同一个流里。

SSE 事件类型：

| event | 含义 |
|---|---|
| `delta` | 文本片段，直接追加到气泡 |
| `tool` | 工具状态：`running` / `done`，只含名称和可读标签 |
| `confirm` | 待确认的写操作：`action_id`、标题、分类、有效期 |
| `done` | 本轮结束 |
| `error` | 出错，带业务错误码 |

示例：

```
event: delta
data: {"delta":"我看看"}

event: tool
data: {"id":"call_1","name":"get_coin_balance","label":"正在查金币","status":"running"}

event: tool
data: {"id":"call_1","name":"get_coin_balance","status":"done"}

event: delta
data: {"delta":"你现在有 12 个金币"}

event: done
data: {"conversation_id":1}
```

每轮流程：

1. 读取最近 10 轮历史（服务端保存，或客户端自带）
2. 用当前问题做 RAG 检索
3. system prompt = 风格画像 + 典型发言 + 检索结果 + 规则
4. 调模型，回复约束成微信式短句

Agent 可以调用的只读工具：

| 工具 | 用途 |
|---|---|
| `search_memories` | 检索日记、复盘、聊天片段 |
| `get_couple_summary` | 在一起多少天、昵称 |
| `get_coin_balance` | 金币余额 |
| `list_mall_items` | 已上架商品 |
| `list_todos` | 未完成的共同清单 |
| `get_today_question` | 今日一问 |
| `propose_create_todo` | 提议添加共同清单（需用户确认） |

每轮最多 5 次工具调用，防止模型死循环。

### 写操作确认

Agent 不能直接写数据。它只能提出一个待确认动作：

```
模型调用 propose_create_todo
    ↓
服务端只创建 pending 动作，不写清单
    ↓
SSE 推 confirm 事件
    ↓
客户端展示确认卡片
    ↓
用户点确认 → POST /agent/actions/{id}/confirm
    ↓
这时才真正写入清单
```

规则：

- 只有发起动作的人能确认
- 重复确认是幂等的，不会写两条
- 10 分钟未确认自动过期
- 删除会话会一并删掉待确认动作

会话策略：

- 默认服务端保存，30 天过期，每次新消息顺延
- `persist=false` 时服务端不存消息，客户端每次带 `history`
- 删除会话会连同消息一起删
- worker 每天 04:07 清理过期会话

### 聊天记录导入

导入格式统一为 **JSONL**，每行一个消息对象：

```json
{"sender":"我","sent_at":"2024-05-01T20:13:00+08:00","content":"今天好累"}
{"sender":"TA","sent_at":"2024-05-01T20:14:00+08:00","content":"怎么啦"}
```

- `sender` 用上传时填的 `owner_name` 或 `partner_name`
- `sent_at` 支持 ISO 8601、常见日期格式、Unix 秒/毫秒
- `type` 可选，默认 `text`

导入接口：

```
POST /api/v1/agent/imports   (multipart)
  file=chat.jsonl
  owner_name=我
  partner_name=TA
```

规则：

- 双方都授权后才能导入
- 单次上限 20MB / 10 万条
- 同一条消息按哈希去重，重复导入不会翻倍
- 原始文件只在内存里解析，不落盘
- 导入后 worker 生成风格画像和向量索引
- 删除导入会清理消息、向量和画像

### 独立 AI 服务

`app/agent_main.py` 只挂载 agent 路由，可以单独部署：

```bash
uv run uvicorn app.agent_main:app --port 8100
```

docker compose 里有 `agent` 服务（8100）。生产环境用 nginx 把
`/api/v1/agent` 转发到它，业务接口仍留在 `api:8000`。
两个服务共享同一个 PostgreSQL、Redis、Chroma。

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
- [x] 日记图片上传（本地 / 阿里云 OSS）
- [ ] 日记导出（长图 / PDF / 短视频）
- [ ] 推送通知（厂商通道）
- [ ] 运营后台
- [ ] Chroma 向量检索
- [ ] 前端
