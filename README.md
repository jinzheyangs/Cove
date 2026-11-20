# Cove

两个人之间，慢慢长出来的一段关系。

面向情侣的关系经营 App：日记、共同清单、恋爱账本、纪念日、金币、秘密树、每日一问、模拟 TA。
仓库包含后端服务、Vue 3 前端，以及 iOS / Android 打包工程。

| 层 | 选型 |
|---|---|
| 语言 / 框架 | Python 3.12 + FastAPI |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| 数据库 | PostgreSQL 16 |
| 缓存 / 队列 | Redis 7 + ARQ |
| 向量检索 | Chroma（模拟 TA 的 RAG，可重建） |
| 前端 | Vue 3 + Vite，WebGL 液态玻璃，Capacitor 打包 iOS / Android |
| 部署 | Docker Compose + Caddy（HTTPS 与反代） |
| 包管理 | uv |

## 目录

```
app/                     后端
├─ main.py               业务入口（/api/v1），同时托管前端 dist
├─ agent_main.py         独立 AI 服务入口（/api/v1/agent，:8100）
├─ worker.py             ARQ 后台任务（对账、燃尽、清理、索引重建）
├─ core/                 配置、数据库、Redis、中间件、加密、限流、指标
└─ modules/<name>/       router → service → repository → models / schemas

migrations/               Alembic 迁移
scripts/                  运维与开发脚本
tests/                    后端测试（150 项）
frontend/                 Vue 3 前端（含 android / ios 工程）
deploy/                   Caddyfile、Prometheus、Alertmanager 配置
docs/                     BACKEND.md、openapi.json、design/（设计稿，不进镜像）
```

## 本地开发

### 一键起（Windows）

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

起后端 `:8000`（同时托管 `frontend/dist`）与前端热更新 `:5173`（`/api`、`/uploads` 代理到 8000）。

### 手动起

```powershell
# 1. 依赖
uv sync

# 2. 配置（只需一次）
Copy-Item .env.example .env

# 3. 基础设施（PostgreSQL / Redis / Chroma 只绑本机端口）
docker compose up -d postgres redis chroma

# 4. 迁移
uv run alembic upgrade head

# 5. 后端（改代码需要重启，默认不带 --reload）
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

# 6. 前端热更新
cd frontend; npm install; npm run dev
```

本机端口映射：PostgreSQL `55432`、Redis `56379`、Chroma `58000`（避开默认端口，避免和本机已有服务冲突）。

后台任务（对账、燃尽清理、索引重建）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_worker.ps1
# 或者：uv run arq app.worker.WorkerSettings
```

自检：

```powershell
curl http://localhost:8000/health        # 进程存活，不查库
curl http://localhost:8000/health/db     # 数据库连通
```

接口文档：<http://localhost:8000/docs>（OpenAPI JSON 见 `docs/openapi.json`，重新生成用 `uv run python scripts/generate_api_doc.py`）。

### 前端

| 命令 | 作用 |
|---|---|
| `npm run dev` | Vite dev server `:5173`，`/api` 与 `/uploads` 代理到 `:8000` |
| `npm run build` | 打包到 `frontend/dist`，后端 `FRONTEND_DIST` 默认就指向它 |
| `npm run cap:sync` | build + 同步进 `android` / `ios` |
| `npm run cap:android` | build + sync + 打开 Android Studio |
| `npm run cap:ios` | build + sync + 打开 Xcode（需 macOS） |

调试参数（加在 URL 上）：`?view=today|diary|tree|me`、`?sheet=<面板名>`、`?static`（跳过入场动画）、`?welcome`（显示登录页）。

### 测试

```powershell
uv run pytest          # 150 项；会自动建 cove_test 库，不碰开发库
uv run ruff check app tests scripts
```

## 生产部署

### 1. 服务器准备

- 一台 Linux 主机（2C2G 起步），装 Docker 与 Compose v2
- 放行 80 / 443（Caddy 申请证书要用 80 做 HTTP-01 验证）
- 有域名的话先解析到这台机器；**中国大陆服务器对外提供网站服务需要 ICP 备案**，备案下来前 80/443 会被拦，可先用非 80 端口或境外机器联调

### 2. `.env`（必改）

复制 `.env.example` 为 `.env`，然后逐项确认：

| 项 | 线上值 | 不改的后果 |
|---|---|---|
| `ENV` | `prod` | HSTS 不生效、密钥校验被跳过 |
| `DEBUG` | `false` | SQL 全量打印，日志爆量且泄露数据 |
| `JWT_SECRET` | `openssl rand -hex 32` | 任何人可自己签发 token 冒充用户（`prod` 下填默认值会拒绝启动） |
| `DATA_ENCRYPTION_KEY` | `openssl rand -base64 32` | `prod` 下为空会拒绝启动；见下面的「密钥迁移」 |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | 强密码 | 数据库弱口令 |
| `DOMAIN` | `cove.example.com`；内网试跑写 `:80` | Caddy 不知道签哪个域名的证书 |
| `LLM_API_KEY` | 你的模型 key | 模拟 TA 不可用 |
| `STORAGE_BACKEND` | 单机部署留 `local`；要多机/换机不留图再切 `oss` | 图片落在容器卷之外会丢 |
| `CORS_ORIGINS` | 前端域名（同源托管可留空） | Web 端跨域失败 |

`TRUST_PROXY_HEADERS=true` 已由 `docker-compose.prod.yml` 注入，不用手写——它让限流按 `X-Forwarded-For` 里的真实客户端 IP 记账，否则所有用户会共用 Caddy 那一个桶。

#### 密钥迁移：把现有数据带上生产

开发环境没有配 `DATA_ENCRYPTION_KEY` 时，字段加密用的是 `SHA256(JWT_SECRET)`。所以**如果要把开发库里已有的秘密、日记带过去**，生产 `.env` 的 `DATA_ENCRYPTION_KEY` 必须填成开发 `.env` 里 `JWT_SECRET` 的**原值**，密钥才一致；随便生成一个新的，旧数据会解不开（`InvalidTag`）。

全新空库部署则直接用新生成的随机值，不受影响。

### 3. 启动

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

`migrate` 是一次性服务：先 `alembic upgrade head`，成功退出后 api / agent / worker 才启动，首次上库不会出现「表不存在」。以后再升版本，同样跑这条命令即可，迁移会自动执行。

### 4. 对外入口

| 端口 | 服务 | 说明 |
|---|---|---|
| 80 / 443 | caddy | 唯一对外入口，HTTPS 由它负责 |
| 127.0.0.1:8000 | api | 只给 Caddy 用 |
| 127.0.0.1:8100 | agent | 同上 |
| 127.0.0.1:55432 / 56379 / 58000 | pg / redis / chroma | 不对外暴露 |

`deploy/Caddyfile` 的路由：

- `/uploads/*` → Caddy 直接从 `./uploads` 读盘
- `/api/v1/agent*` → `agent:8100`
- 其余 → `api:8000`（前端静态文件、业务接口、`/docs`）

证书与 Caddy 状态存在命名卷 `cove_caddy_data`，容器重建不会重签。

### 5. 上线自检

```bash
curl -I https://cove.example.com/            # 200，返回 index.html
curl https://cove.example.com/health         # {"code":0,...}
curl https://cove.example.com/health/db      # {"data":{"db":"ok"}}
curl https://cove.example.com/api/v1/users/me   # 需要登录的接口，应返回 401
```

再打开 App 走一遍：注册 → 邀请码绑定 → 写一篇日记带图 → 记账 → 模拟 TA 发一句话。

### 6. 备份

```bash
BACKUP_PASSPHRASE=xxx bash scripts/backup_db.sh backup
BACKUP_PASSPHRASE=xxx bash scripts/backup_db.sh restore backups/cove-xxx.sql.gz.enc
```

备份加密口令就是 `.env` 里的 `BACKUP_PASSPHRASE`，默认保留 30 天。`uploads/` 是用户图片，需要单独做快照或对象存储同步。

## 接口一览

所有业务接口前缀 `/api/v1`：

| 模块 | 前缀 | 说明 |
|---|---|---|
| 认证 | `/auth` | 手机号 + 密码、JWT、改密码 |
| 用户 | `/users` | 当前用户、资料 |
| 情侣 | `/couples` | 邀请码绑定、解绑、在一起日期 |
| 金币 | `/coins` | 余额、流水、赠与 |
| 金币申请 | `/coin-applies` | 申请、审批 |
| 秘密树 | `/secrets` | 发布、摘取、燃尽、销毁 |
| 商城 | `/mall` | 上架、购买、核销 |
| 日记 | `/diaries` | 个人 / 共同视角，左滑删除在客户端 |
| 清单 | `/todos` | 共同 / 单人，完成生成纪念卡 |
| 账本 | `/bills` | 金钱与非金钱付出、统计 |
| 每日一问 | `/daily` | 固定题库，每天一题 |
| 纪念日 | `/anniversaries` | 在一起 / 生日 / 自定义倒计时 |
| 模拟TA | `/sim-ta` | 授权开关、状态 |
| AI 对话 | `/agent` | 多轮人格对话、SSE 流式、待确认动作 |
| 上传 | `/uploads` | 日记图片、头像 |
| 通知 | `/notifications` | 站内通知、未读数 |
| 隐私 | `/privacy` | 注销账号 |

## 关键设计

- **依赖方向固定** `router → service → repository`，SQL 只出现在 repository。
- **金币消费 = 销毁，赠与 = 系统发行**；余额是缓存，流水是真相，worker 每天 03:17 对账。
- **扣币加行锁**（按 `user_id` 升序），并发下余额不会为负。
- **写操作幂等**：日记、清单、账单、下单都接受 `idempotency_key`，重复提交只生效一次。
- **阅后即焚**：读后 24 小时内可再看，之后由 worker 清空内容。
- **账本不提供个人对比**，只输出共同视角汇总。
- **模拟 TA 必须先获得对方授权**，撤销即停用。
- **字段加密**：秘密、日记等私密内容 AES-256-GCM 存库；密钥缺失时生产直接拒绝启动。
- **令牌**：access 30 分钟，refresh 30 天、可轮换、可吊销。
- **限流三档**（全局 / 认证 / AI），Redis 故障时放行；登录另有按手机号的失败锁定。
- **AI 熔断**：连续失败 5 次开 60 秒，半开时放一个请求试探。

## 模拟 TA

### 对话链路

```
POST /agent/conversations                        新建会话
POST /agent/conversations/{id}/messages/stream   发消息，SSE 流式
GET  /agent/conversations/{id}                   历史
POST /agent/conversations/{id}/memorize          把最近几轮切成记忆块写入向量库
POST /agent/actions/{id}/confirm|cancel           确认 / 取消待执行的写操作
```

SSE 事件：`delta`（文本片段）、`tool`（工具运行状态）、`confirm`（待确认动作）、`done`、`error`。

每轮：取最近 10 轮历史 → 用问题做 RAG 检索 → system prompt = 记忆片段 + 检索结果 + 规则 → 调模型。
每轮最多 5 次工具调用，防止死循环。

### 工具

只读：`search_memories`、`get_couple_summary`、`get_coin_balance`、`list_mall_items`、`list_todos`、`get_today_question`。
写：`propose_create_todo`、`propose_create_diary`、`propose_buy_mall_item` —— 一律只创建 `pending` 动作，用户点确认才真正写库，10 分钟未确认自动过期，重复确认幂等。

### RAG

```
日记 / 对话记忆写入 → 事务提交后入队（ARQ）→ 切片 → embedding → Chroma
用户提问 → embedding → Chroma top-k（按 couple_id + user_id 过滤）→ prompt → LLM
```

- **PG 是真相，Chroma 是可重建的索引**；`chunk_index` 表记录映射，内容没变不重复 embedding（`content_hash`）
- embedding 未配置或 Chroma 不可用时，自动退回「最近日记」
- 撤销授权、注销账号会删除对应向量
- 每小时对账一次：缺的按源重建、孤儿删掉

重建单个用户索引：

```bash
uv run python scripts/reindex_user.py <couple_id> <user_id>
```

## 运维脚本

| 脚本 | 用途 |
|---|---|
| `scripts/dev.ps1` | 一键起本地后端 + 前端（`-NoFrontend` 只起后端） |
| `scripts/run_worker.ps1` | 前台跑 ARQ worker |
| `scripts/backup_db.sh` | 加密备份 / 恢复数据库 |
| `scripts/encrypt_existing_data.py` | 把历史明文列加密成 `v1:` 格式（先备份） |
| `scripts/reindex_user.py` | 重建某用户向量索引 |
| `scripts/generate_api_doc.py` | 重新生成 `docs/openapi.json` |
| `scripts/grant_welcome_coins.py` | 给存量用户补发新人金币 |
| `scripts/seed_daily_questions.py` | 灌每日一问题库 |
| `scripts/dev_issue_tokens.py` | 本地签发测试 token（仅开发） |

## 常见问题

**上线后不停 429 / 提示请求太频繁**
限流按 IP 记账。直连（本地开发）看 socket 对端；走反代必须让 `TRUST_PROXY_HEADERS=true`（prod compose 已设），否则所有用户共用 Caddy 一个桶。确认 `deploy/Caddyfile` 没把 `X-Forwarded-For` 去掉。

**老数据报 `InvalidTag` / 解不开密文**
加密密钥换了。开发环境用 `SHA256(JWT_SECRET)` 派生，生产用 `DATA_ENCRYPTION_KEY`；把 `DATA_ENCRYPTION_KEY` 填成旧 `JWT_SECRET` 的原值即可，或先 `scripts/backup_db.sh` 备份后用 `scripts/encrypt_existing_data.py` 重加密。

**部署起来全是 500，日志里 `relation "..." does not exist`**
迁移没跑。用上面的生产命令启动，`migrate` 服务会自动执行 `alembic upgrade head`；手动补可 `docker compose exec api uv run alembic upgrade head`。

**图片 404 / 重建容器后图片没了**
`uploads/` 通过卷挂在宿主机（`./uploads:/app/uploads`，Caddy 只读挂 `/srv/uploads`），别改成容器内部路径；换机器时记得一起搬走。

**前端打开是白屏**
`frontend/dist` 不存在。`cd frontend && npm run build`，或直接走 Docker 构建（镜像里会自己打包）。

**模拟 TA 想不起说过的话**
Chroma 的 HNSW 段偶尔不落盘，表现为 `count` 有、`get` 拿不到。写入后会立刻读回校验，worker 每小时对账修复；急用时 `scripts/reindex_user.py`。

## 开发进度

- [x] 骨架与三层架构、CI、限流、审计、指标
- [x] 注册登录 / 情侣绑定 / 解绑 / 注销
- [x] 金币、申请审批、商城
- [x] 秘密树、日记、共同清单、账本
- [x] 每日一问、纪念日、站内通知
- [x] 模拟 TA（授权、RAG、多轮对话、工具确认）
- [x] 图片上传（本地 / 阿里云 OSS）
- [x] 前端（四视图 + 液态玻璃引擎 + Capacitor 工程）
- [ ] 推送通知（厂商通道）
- [ ] 运营后台
- [ ] 日记导出（长图 / PDF）
