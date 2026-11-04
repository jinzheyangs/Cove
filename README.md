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
cp .env.example .env      # 填入数据库密码等
uv sync                   # 安装依赖
docker compose up --build
```

验证：

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

## 目录结构

```
app/
├── main.py            # FastAPI 入口
├── worker.py          # ARQ 后台任务
├── core/              # 配置、数据库、鉴权、错误处理
└── modules/           # 业务模块，每个模块 4 个文件
    └── <name>/
        ├── models.py    # SQLAlchemy 模型
        ├── schemas.py   # Pydantic 模型
        ├── service.py   # 业务逻辑
        └── router.py    # HTTP 层（只管参数和返回）
migrations/            # Alembic 迁移
```

约定：**router 只处理 HTTP，业务逻辑全部放在 service。**
