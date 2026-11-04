# Cove

两个人之间，慢慢长出来的一段关系。

Cove 是一个面向情侣的关系经营 App。这个仓库是**后端服务**的源码。

> 状态：开发中，尚未发布。

## 技术栈

| 层 | 选型 |
|---|---|
| 语言 / 框架 | Python 3.12 + FastAPI |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| 数据库 | PostgreSQL 16 |
| 缓存 / 队列 | Redis 7 + ARQ |
| 向量检索 | Chroma |
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

> 本地映射的是 **55432** 端口（避开机器上可能已有的 5432）。

验证：

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

接口文档：<http://localhost:8000/docs>

## 测试

```bash
uv run pytest
```

测试会自动创建 `cove_test` 数据库，不影响开发库。

## 架构

经典三层。每个模块：

```
app/modules/<name>/
├── router.py       # 接口层：HTTP 参数、校验、返回
├── service.py      # 业务层：规则、事务边界
├── repository.py   # 数据访问层：所有 SQL 只出现在这里
├── models.py       # 表结构
└── schemas.py      # 请求 / 响应结构
```

依赖方向永远是 `router → service → repository`，不许反向。

```
app/
├── main.py
├── worker.py       # ARQ 后台任务（含每日金币对账）
├── core/           # 配置、数据库、鉴权、错误处理
└── modules/
    ├── users/
    ├── couples/
    └── coins/
migrations/
tests/
```

## 已实现接口

### 认证

| 方法 | 路径 |
|---|---|
| POST | `/api/v1/auth/register` |
| POST | `/api/v1/auth/login` |
| GET | `/api/v1/users/me` |

### 情侣绑定

| 方法 | 路径 |
|---|---|
| POST | `/api/v1/couples/invite` |
| POST | `/api/v1/couples/bind` |
| GET | `/api/v1/couples/me` |

### 金币

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/coins/balance` | 当前余额 |
| GET | `/api/v1/coins/transactions` | 流水（分页） |
| POST | `/api/v1/coins/gift` | 赠与对方金币 |

金币规则：

- **赠与 = 系统发行**，不扣赠与方余额
- **消费 = 销毁**，流水的 `to_user_id` 为 NULL
- 余额是缓存，流水是真相；worker 每天 03:17 自动对账
- 所有写操作靠 `idempotency_key` 唯一索引兜底，重复提交只生效一次
- 扣减时对 `coin_accounts` 行加锁，并发下余额不会为负

## 开发进度

- [x] 项目骨架
- [x] 用户注册登录 / 情侣绑定
- [x] 金币账本（余额、流水、赠与、消费、对账）
- [ ] 金币申请与审批
- [ ] 秘密树
- [ ] 商城
- [ ] 恋爱日记
