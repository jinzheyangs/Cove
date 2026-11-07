# Cove 后端功能文档

> 版本：1.0  
> 更新日期：2026-11-08  
> 适用分支：`main`  
> 状态：后端功能已完成，前端开发中

Cove 是一款面向情侣的关系应用。后端提供秘密树、金币、恋爱日记、共同清单、恋爱账本、商城、每日一问、纪念日、模拟 TA、AI Agent 等能力。

---

## 1. 项目概览

### 1.1 技术栈

| 层次 | 选型 |
|---|---|
| 语言 | Python 3.12 |
| Web 框架 | FastAPI + Pydantic v2 |
| ORM | SQLAlchemy 2.0 async + asyncpg |
| 数据库 | PostgreSQL 16 |
| 缓存 / 队列 | Redis 7 + ARQ |
| 向量库 | Chroma |
| 迁移 | Alembic |
| 部署 | Docker Compose |
| 可观测性 | structlog + Prometheus + OpenTelemetry / Jaeger |

### 1.2 三层架构

```text
HTTP 请求
   │
   ▼
router.py       只做参数接收、依赖注入、响应包装
   │
   ▼
service.py      业务规则、权限判断、事务边界
   │
   ▼
repository.py   纯数据访问，不 commit
   │
   ▼
PostgreSQL / Redis / Chroma / 对象存储
```

模块目录统一为：

```text
app/modules/<module>/
  models.py       表结构
  schemas.py      请求 / 响应结构
  repository.py   数据访问
  service.py      业务逻辑
  router.py       HTTP 接口
```

### 1.3 统一约定

- 业务接口前缀：`/api/v1`
- 认证方式：`Authorization: Bearer <access_token>`
- 响应外壳：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

- 业务错误使用非 0 `code`，同时给出对应 HTTP 状态码。
- 每个响应带 `X-Request-ID`；调用方也可以主动传，便于排查。
- 日期口径统一为 **Asia/Shanghai**，避免 UTC 导致早上 8 点才换日。
- 主键统一使用 `BIGINT` 自增。
- 敏感字段使用 AES-256-GCM 加密，密文带 `v1:` 前缀。

---

## 2. 功能模块

### 2.1 账号与认证

手机号 + 密码登录，不接短信验证；手机号本质上是用户名。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/auth/register` | 注册并直接返回登录态 |
| POST | `/api/v1/auth/login` | 登录 |
| POST | `/api/v1/auth/refresh` | 刷新令牌，旧 refresh token 立即失效 |
| POST | `/api/v1/auth/logout` | 登出当前设备 |
| POST | `/api/v1/auth/logout-all` | 退出所有设备 |
| POST | `/api/v1/auth/change-password` | 修改密码并吊销全部旧会话 |

规则：

- 手机号格式：中国大陆手机号 `1[3-9]xxxxxxxxx`。
- 密码长度 6–64，使用 Argon2 哈希。
- access token：JWT，默认 30 分钟。
- refresh token：随机串，数据库只存 SHA-256；默认 30 天；每次刷新轮换。
- 连续登录失败 5 次锁定 15 分钟。
- 修改密码后所有 refresh token 作废，当前设备拿到新令牌。
- 已注销账号不能登录或刷新。

表：`users`、`refresh_tokens`

### 2.2 用户资料

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/users/me` | 当前用户资料 |
| PUT | `/api/v1/users/me` | 修改昵称、头像、生日 |

规则：

- 头像传对象存储 key，不传完整 URL。
- 头像 key 必须位于 `couples/{couple_id}/avatars/{user_id}/` 下，防止填别人的地址。
- 生日不能是未来日期；传 `null` 可清除。
- 返回的 `avatar_url` 由当前存储配置生成；私有 OSS 返回带有效期的签名 URL。

表：`users`

### 2.3 情侣关系

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/couples/invite` | 生成邀请码，24 小时有效 |
| POST | `/api/v1/couples/bind` | 用邀请码绑定 |
| GET | `/api/v1/couples/me` | 查询当前关系，未绑定返回 `null` |
| POST | `/api/v1/couples/unbind` | 解除绑定，必须显式传 `confirm=true` |

规则：

- `user1_id < user2_id`，同一段关系只有一种存法。
- 每个用户同时只能有一段 `active` 关系，由部分唯一索引保证。
- 绑定过程使用行锁，避免邀请码被并发使用。
- 解绑只改状态，不删除历史日记、秘密、账目等数据。
- 情侣内业务统一依赖 `CurrentCouple`；未绑定时返回业务码 `3001`（HTTP 409）。

表：`couples`、`couple_invites`

### 2.4 金币

金币是关系内的消耗品：消费即销毁，赠与即发行。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/coins/balance` | 当前余额 |
| POST | `/api/v1/coins/gift` | 给伴侣赠币 |
| GET | `/api/v1/coins/transactions` | 流水（分页） |

规则：

- 账户余额是缓存值，真实账目以 `coin_transactions` 流水为准。
- 每日赠与上限默认 500 币，按北京时间切天。
- 不能给自己赠币，只能赠给当前伴侣。
- 余额有数据库 `CHECK (balance >= 0)`，扣币使用行锁。
- 每天 03:17 由 worker 对账：从流水重算余额，不一致写入 Prometheus 指标。
- 消费类型包括：摘秘密、买商城商品。

表：`coin_accounts`、`coin_transactions`

### 2.5 金币申请

一方申请金币，另一方审批后发行。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/coin-applies` | 发起申请 |
| GET | `/api/v1/coin-applies` | 我发起的申请 |
| GET | `/api/v1/coin-applies/pending` | 待我审批的申请 |
| POST | `/api/v1/coin-applies/{id}/approve` | 通过并发行金币 |
| POST | `/api/v1/coin-applies/{id}/reject` | 拒绝 |

规则：

- 不能审批自己发起的申请。
- 审批通过时，发行金币、更新申请状态、发通知在同一个事务里完成。
- 拒绝需要给出原因，原因会展示给申请人。

表：`coin_applies`

### 2.6 秘密树

一方发布秘密，另一方花金币摘取。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/secrets` | 发布秘密 |
| GET | `/api/v1/secrets` | 伴侣发布的、可摘取的秘密列表 |
| GET | `/api/v1/secrets/mine` | 我发布的秘密，含已燃尽 / 已销毁 |
| POST | `/api/v1/secrets/{id}/unlock` | 花金币摘取 |
| DELETE | `/api/v1/secrets/{id}` | 销毁自己发布的一条 |
| DELETE | `/api/v1/secrets` | 销毁自己发布的全部 |

规则：

- 等级 `normal` 默认 10 币，`deep` 默认 30 币；也可以自定义 1–1000 币。
- 发布时只返回列表信息，正文不会随列表泄漏。
- 不能摘自己的秘密；已燃尽 / 已销毁的不能再摘。
- 非阅后即焚的秘密，被看过一次后再次查看不再扣费。
- 阅后即焚只标记 `burned`，正文保留 24 小时；之后由 worker 清空，防止响应丢失导致内容永久丢失。
- 扣币、标记已读、燃尽、通知在同一个事务里完成。
- 正文加密存储。

表：`secrets`

### 2.7 恋爱日记

支持共同编辑和「各自视角」。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/diaries` | 新建 |
| GET | `/api/v1/diaries` | 列表，支持 `mode`、`event_id`、分页 |
| GET | `/api/v1/diaries/{id}` | 详情 |
| PUT | `/api/v1/diaries/{id}` | 部分更新 |
| DELETE | `/api/v1/diaries/{id}` | 删除 |

规则：

- `mode=personal`：各自视角，只有作者能改 / 删；双方都能看。
- `mode=shared`：共同日记，双方都能改 / 删。
- 同一件事的两种视角传同一个 `event_id`，查询时可按它取回两篇。
- 标题、正文加密；情绪标签、地点、图片列表明文存储。
- 图片只存对象 key，返回时生成可访问 URL。
- 创建支持 `idempotency_key`。
- 创建 / 更新 / 删除后会异步同步向量索引，供 RAG 检索。

表：`diaries`

### 2.8 共同清单

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/todos` | 新建 |
| GET | `/api/v1/todos` | 列表，支持类型 / 分类 / 状态过滤 |
| PUT | `/api/v1/todos/{id}` | 部分更新 |
| POST | `/api/v1/todos/{id}/complete` | 完成并生成纪念卡片 |
| DELETE | `/api/v1/todos/{id}` | 删除 |

规则：

- `type=shared`：双方都能改、能完成。
- `type=personal`：只有创建者能改、能完成。
- 重复完成返回 409，避免同一件事生成多张卡片。
- 完成接口返回更新后的清单项 + 一张文案卡片。
- 创建支持 `idempotency_key`。

表：`todo_items`

### 2.9 恋爱账本

记录金钱支出和非金钱付出，并提供共同视角统计。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/bills` | 新增 |
| GET | `/api/v1/bills` | 列表，支持类型 / 范围过滤 |
| GET | `/api/v1/bills/stats` | 统计 |
| PUT | `/api/v1/bills/{id}` | 整体更新 |
| DELETE | `/api/v1/bills/{id}` | 删除 |

规则：

- `type=money` 必须填金额；`time` / `energy` / `emotion` 不允许填金额，避免把陪伴和情绪劳动数字化。
- `scope=shared|personal`，配合 `is_private` 控制可见性。
- 只能修改 / 删除自己记的账。
- 统计只给共同视角的总额、分类合计和非金钱付出次数，**不输出“谁付了多少”**，避免变成算账工具。
- 备注加密；创建支持 `idempotency_key`。

表：`bills`

### 2.10 商城

伴侣之间用金币兑换“体验 / 行动”类商品。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/mall/items` | 上架商品，进入待审批 |
| GET | `/api/v1/mall/items` | 已上架商品 |
| GET | `/api/v1/mall/items/mine` | 我上架的，含待审批 / 被拒绝 |
| POST | `/api/v1/mall/items/{id}/approve` | 审批通过并确定最终价 |
| POST | `/api/v1/mall/items/{id}/reject` | 拒绝上架 |
| POST | `/api/v1/mall/items/{id}/offline` | 下架 |
| POST | `/api/v1/mall/orders` | 购买 |
| GET | `/api/v1/mall/orders` | 关系内全部订单 |
| POST | `/api/v1/mall/orders/{id}/complete` | 服务方确认完成 |

规则：

- 不能审批、购买自己上架的商品。
- 创建者只给建议价，最终价格由对方审批时确定。
- 支持 `max_orders` 限量；库存检查在商品行锁内完成，避免超卖。
- 购买时锁商品行、检查状态 / 库存、扣币、建订单、发通知，统一提交。
- 订单保存成交价快照，后续改价不影响历史订单。
- 购买支持 `idempotency_key`，防止网络重试重复扣币。
- 只有商品创建者能确认订单完成。
- 状态：商品 `pending / approved / rejected / offline`；订单 `pending / completed / cancelled`。

表：`mall_items`、`mall_orders`

### 2.11 每日一问

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/daily` | 今日问题 + 双方回答 |
| POST | `/api/v1/daily` | 提交 / 修改今日回答 |

规则：

- 固定题库 24 题，按日期确定性取题，零 AI 成本。
- 同一天双方拿到同一题。
- 对方答案只在自己回答后才返回，避免互相影响。
- 按北京时间切天。

表：`daily_answers`

### 2.12 纪念日倒计时

统一管理「在一起」、双方生日和自定义纪念日。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/anniversaries` | 全部倒计时，按剩余天数排序 |
| POST | `/api/v1/anniversaries` | 新建自定义纪念日 |
| PUT | `/api/v1/anniversaries/{id}` | 修改自定义纪念日 |
| DELETE | `/api/v1/anniversaries/{id}` | 删除自定义纪念日 |

三类条目：

| source | 来源 | 是否可编辑 |
|---|---|---|
| `relationship` | `couples.bind_at` 自动计算「在一起」 | 否 |
| `birthday` | `users.birthday`，双方各填自己的 | 通过资料接口修改 |
| `custom` | `anniversaries` 表 | 双方都能改 / 删 |

返回示例：

```json
{
  "id": 3,
  "source": "custom",
  "title": "第一次旅行",
  "date": "2024-06-01",
  "next_date": "2027-06-01",
  "days_left": 206,
  "years": 3,
  "is_today": false,
  "passed": false,
  "repeat_yearly": true,
  "owner_id": 1,
  "editable": true
}
```

字段说明：

- `date`：原始日期，即第一次发生的那天 / 出生日期。
- `next_date`：下一次发生的日期。
- `days_left`：距离 `next_date` 还有多少天；今天为 `0`。
- `years`：到下一次时是第几周年；生日场景即下一次生日时的年龄；一次性事件为 `null`。
- `is_today`：今天就是纪念日。
- `passed`：一次性事件已经过去，`days_left` 为负数。
- `repeat_yearly`：是否每年重复。
- `owner_id`：生日所属用户或自定义纪念日创建者。

规则：

- 「在一起」不用手动录入，直接取绑定日期。
- 生日在 `PUT /users/me` 里设置，例如 `{"birthday": "1998-05-20"}`。
- 自定义纪念日支持每年重复（`repeat_yearly=true`）或一次性事件（`false`）。
- 2 月 29 日在平年按 2 月 28 日计算。
- 第一次发生日在未来时，下一次就是该日期本身，不会倒推到今年。
- 排序：未来事件由近到远；已经过去的一次性事件排在最后，最近的在前。
- 自定义纪念日支持 `idempotency_key`。
- 注销账号会删除该用户创建的纪念日并清空生日；数据导出包含纪念日。

表：`anniversaries`；`users` 增加 `birthday` 字段

### 2.13 模拟 TA

基于历史记录模拟伴侣的说话方式。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/sim-ta` | 当前授权与忠实度状态 |
| PUT | `/api/v1/sim-ta/consent` | 开启 / 撤销授权 |
| PUT | `/api/v1/sim-ta/settings` | 切换忠实度 |
| POST | `/api/v1/sim-ta/chat` | 和对方的分身对话（一次性返回） |

规则：

- 使用某人的数据前，必须本人授权；未授权时对话返回 403。
- 撤销授权立即停用：删除派生画像和向量索引，并写审计日志。
- 两种模式：
  - `faithful`：只基于真实记录，不确定就说不知道，不编造。
  - `idealized`：更温柔，但禁止替真人做承诺。
- 每次回复都带免责声明：这是模拟，不是本人。
- 检索优先走 Chroma 向量相似度；未配置 embedding 时退回最近日记。
- AI 不可用时返回温和提示，而不是技术错误。

表：`persona_consents`、`persona_settings`、`persona_profiles`

### 2.14 AI Agent

多轮对话，支持读取业务数据和“提议写操作”。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/agent/conversations` | 新建会话 |
| GET | `/api/v1/agent/conversations` | 会话列表 |
| GET | `/api/v1/agent/conversations/{id}` | 会话详情 |
| DELETE | `/api/v1/agent/conversations/{id}` | 删除会话 |
| POST | `/api/v1/agent/conversations/{id}/messages/stream` | 流式对话（SSE） |
| POST | `/api/v1/agent/actions/{id}/confirm` | 确认写操作 |
| POST | `/api/v1/agent/actions/{id}/cancel` | 取消写操作 |

规则：

- 只保留流式接口，不再提供一次性返回。
- SSE 事件类型：`delta`、`tool`、`confirm`、`done`、`error`。
- 只读工具直接执行；写操作只能生成 `pending` 动作，必须用户确认后才执行。
- 支持的写操作：
  - `create_todo`：添加到共同清单
  - `create_diary`：写一篇个人日记
  - `buy_mall_item`：兑换商城商品（会扣金币）
- 待确认动作有效期 10 分钟，超时标记 `expired`。
- 每个动作执行时带固定幂等键 `agent-action-{id}`，状态提交失败后重试不会重复写入 / 重复扣币。
- 会话默认保留 30 天；每次新消息顺延；过期由 worker 清理。
- 服务端最多带最近 10 轮历史；单次最多 5 轮工具调用。

表：`agent_conversations`、`agent_messages`、`agent_actions`

### 2.15 聊天记录导入

把历史聊天记录导入，用于生成说话风格画像和向量索引。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/agent/imports` | 上传并解析聊天记录 |
| GET | `/api/v1/agent/imports` | 导入记录列表 |
| GET | `/api/v1/agent/imports/{id}` | 单次导入详情 |
| DELETE | `/api/v1/agent/imports/{id}` | 删除导入及其消息、画像、向量 |

规则：

- 支持 JSONL / JSON，单文件最大 20 MB、10 万条消息。
- 必须双方都授权后才能导入。
- 需要指定双方在文件里的昵称，服务端把发送人映射到用户。
- 只识别到一方消息时拒绝导入，避免昵称填错导致口吻错位。
- 以 `(couple_id, source_hash)` 去重，同一份文件重复导入不会产生重复消息。
- 解析出的消息加密存储；原始文件不落盘。
- 画像和向量索引由 worker 异步生成。
- 注销账号时：本人上传的导入整条删除；对方导入中删除本人发言并重建索引。

表：`chat_imports`、`chat_messages`

### 2.16 通知

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/notifications` | 我的通知，分页 |
| GET | `/api/v1/notifications/unread-count` | 未读数 |
| POST | `/api/v1/notifications/{id}/read` | 标记单条已读 |
| POST | `/api/v1/notifications/read-all` | 全部已读 |

规则：

- 站内通知，目前没有接厂商推送通道。
- 业务动作会触发通知，例如秘密被摘取、金币申请通过 / 被拒绝、商品被兑换、订单完成。

表：`notifications`

### 2.17 审计

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/audit` | 我的敏感操作记录 |

记录范围包括：修改密码、撤销模拟 TA 授权、确认 / 取消 Agent 写操作、注销账号等。

表：`audit_logs`

### 2.18 上传

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/uploads/avatar` | 上传头像 |
| POST | `/api/v1/uploads/diary-image` | 上传日记图片 |
| DELETE | `/api/v1/uploads/{key}` | 删除自己关系内的文件 |

规则：

- 只支持 JPEG / PNG / WebP。
- 同时校验 MIME、文件头和大小，单文件最大 10 MB。
- 本地存储写入 `uploads/`；生产可切阿里云 OSS。
- 私有 OSS 返回带有效期的签名 URL。
- 删除时校验 key 属于当前关系，防止删除别人的文件。
- 图片 key 格式：`couples/{couple_id}/{purpose}/{user_id}/{uuid}.{ext}`。

### 2.19 隐私

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/privacy/export` | 导出个人数据（JSON） |
| POST | `/api/v1/privacy/delete` | 注销账号 |

导出范围：资料、关系、日记、秘密、账本、清单、每日一问、纪念日、金币流水。

注销流程：

1. 重新校验密码。
2. 解除当前关系。
3. 删除个人内容：秘密、日记、账本、清单、每日一问、纪念日、模拟 TA 授权与画像、通知、审计、Agent 会话、聊天导入。
4. 清理向量库索引；对方导入中删除本人发言并重建索引。
5. 匿名化用户行：手机号改为 `deleted-{id}`、密码随机化、昵称改为“已注销”、清空头像和生日、写入 `deleted_at`。
6. 保留金币流水和商城订单，避免对方账目对不上。

---

## 3. 数据模型

当前共 26 张业务表（数据库另有 1 张 `alembic_version`）。

| 模块 | 表 |
|---|---|
| 用户 | `users`、`refresh_tokens` |
| 情侣 | `couples`、`couple_invites` |
| 金币 | `coin_accounts`、`coin_transactions`、`coin_applies` |
| 秘密树 | `secrets` |
| 日记 | `diaries` |
| 清单 | `todo_items` |
| 账本 | `bills` |
| 商城 | `mall_items`、`mall_orders` |
| 每日一问 | `daily_answers` |
| 纪念日 | `anniversaries` |
| 模拟 TA | `persona_consents`、`persona_settings`、`persona_profiles` |
| Agent | `agent_conversations`、`agent_messages`、`agent_actions`、`chat_imports`、`chat_messages` |
| 向量索引 | `chunk_index` |
| 通知 | `notifications` |
| 审计 | `audit_logs` |

关键约束：

- 金币余额 `CHECK (balance >= 0)`。
- 情侣 `user1_id < user2_id`；active 关系上双方各有部分唯一索引。
- 幂等键在关系内唯一，且只约束非 NULL 值。
- 已注销用户不物理删除，避免破坏金币流水和订单外键。

---

## 4. 横切机制

### 4.1 字段加密

- 算法：AES-256-GCM。
- 密文格式：`v1:<base64>`。
- 通过 SQLAlchemy `TypeDecorator` 自动加解密，业务代码无感知。
- 覆盖字段：秘密正文、日记标题 / 正文、账本备注、每日一问答案、Agent 标题 / 消息 / 动作参数与结果、聊天消息、画像摘要与样例等。

### 4.2 幂等

写接口支持客户端传 `idempotency_key`：

- 日记、清单、账本、商城购买、纪念日创建。
- 数据库部分唯一索引兜底并发重复提交。
- 冲突时返回第一次成功的结果，不重复写入。
- Agent 写操作使用固定的 `agent-action-{id}` 作为幂等键。

### 4.3 并发控制

- 金币扣减、秘密摘取、商城购买、邀请码绑定使用行锁。
- 库存检查在商品行锁内完成。
- 扣币和业务状态更新在同一个事务里提交。
- 余额和库存都有数据库层约束，不只依赖代码判断。

### 4.4 限流

- Redis ZSET + Lua 实现滑动窗口，原子完成“检查 + 计数”。
- 默认三档：
  - 全局：120 次 / 分钟
  - 认证接口：10 次 / 分钟
  - AI 接口（`/sim-ta`、`/agent`）：30 次 / 分钟
- Redis 不可用时 fail open，避免限流组件故障拖垮业务。
- 登录失败另有独立计数和锁定。

### 4.5 异步任务与定时任务

ARQ worker 负责：

| 任务 | 说明 |
|---|---|
| `index_diary` | 重建日记向量索引 |
| `delete_diary_vectors` | 删除日记向量 |
| `delete_user_vectors` | 删除用户全部向量 |
| `delete_chat_import_vectors` | 删除单次导入的向量 |
| `process_chat_import` | 生成画像并建立聊天窗口索引 |

定时任务：

| 时间 | 任务 |
|---|---|
| 每天 03:17 | 金币对账 |
| 每天 03:41 | 清理燃尽期已过的秘密正文 |
| 每天 04:07 | 清理过期 Agent 会话 |
| 每天 04:17 | 过期未确认的 Agent 动作 |

### 4.6 RAG 与向量检索

- Chroma 作为向量库，PostgreSQL 是唯一真相，向量可重建。
- 日记按字符切片，默认 400 字、重叠 50 字。
- 聊天记录按对话窗口切片，每个窗口最多 4 条消息，且必须包含目标用户本人的发言。
- 检索强制按 `couple_id + user_id` 过滤，避免拿错人的数据。
- 内容未变化时按 hash 跳过 embedding，节省调用成本。
- 未配置 embedding 时自动退回最近日记，不影响业务可用性。

### 4.7 AI 调用

- 模型和 embedding 均通过 OpenAI 兼容接口配置，不硬编码厂商。
- 支持超时、重试、熔断（closed / open / half-open）和降级。
- AI 不可用时，模拟 TA 返回温和提示，Agent 返回错误事件。
- 调用次数、耗时、失败率写入 Prometheus 指标。

### 4.8 可观测性

- structlog 结构化日志，自动携带 `request_id`、`user_id`、路径、耗时。
- 日志不打印手机号、正文等隐私内容。
- Prometheus 指标 + 告警规则。
- OpenTelemetry 链路追踪，可接 Jaeger。
- `/health`、`/health/db`、`/metrics` 运维接口。

### 4.9 对象存储

- `STORAGE_BACKEND=local`：写本地目录，开发环境直接通过 `/uploads` 访问。
- `STORAGE_BACKEND=oss`：阿里云 OSS，私有桶返回签名 URL。
- 上传前校验 MIME、文件头和大小。

---

## 5. 错误码

| 范围 | 模块 |
|---|---|
| 1001–1009 | 注册、登录、资料、密码 |
| 2001–2008 | 情侣绑定、邀请码、解绑 |
| 3001 | 尚未绑定伴侣 |
| 4001–4004 | 金币余额、赠与、每日上限 |
| 5001–5004 | 秘密树 |
| 6001–6004 | 金币申请 |
| 7001–7011 | 商城 |
| 8001–8003 | 日记 |
| 9001–9003 | 清单 |
| 10001–10004 | 账本 |
| 11001–11003 | AI 调用不可用 |
| 14001–14002 | 模拟 TA |
| 15001 | 注销账号密码错误 |
| 16001–16004 | 上传 |
| 17001–17013 | Agent / 聊天导入 |
| 18001 | 纪念日不存在 |

完整的接口参数和响应结构以 FastAPI 自动生成的 `/docs`、`/openapi.json` 为准。

---

## 6. 运行与部署

### 6.1 本地开发

```bash
# 安装依赖
uv sync

# 启动依赖服务
docker compose up -d postgres redis chroma

# 执行迁移
uv run alembic upgrade head

# 启动 API
uv run uvicorn app.main:app --reload

# 启动 worker
uv run arq app.worker.WorkerSettings
```

### 6.2 Docker Compose

`docker-compose.yml` 包含：

- `api`：主 API 服务
- `agent`：独立 Agent 服务（8100）
- `worker`：ARQ 任务进程
- `postgres`：PostgreSQL 16
- `redis`：Redis 7
- `chroma`：向量库
- `jaeger`：链路追踪
- `prometheus` / `alertmanager`：监控（monitoring profile）

### 6.3 关键环境变量

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | PostgreSQL 连接串 |
| `REDIS_URL` | Redis 连接串 |
| `JWT_SECRET` | JWT 签名密钥，生产必须修改 |
| `DATA_ENCRYPTION_KEY` | 字段加密密钥 |
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | 对话模型 |
| `EMBEDDING_*` | Embedding 服务 |
| `CHROMA_*` | 向量库连接 |
| `STORAGE_BACKEND` | `local` 或 `oss` |
| `OSS_*` | 阿里云 OSS 配置 |
| `QUEUE_ENABLED` | 是否启用异步任务 |

---

## 7. 已知限制

- access token 是无状态 JWT，修改密码后旧 access token 在过期前（最长 30 分钟）仍然有效；refresh token 已全部吊销。
- AI 熔断器是单进程的，多实例部署时各实例独立计数。
- worker 的 cron 任务在每个实例都会运行，多实例部署时应拆成单独进程。
- 聊天记录在请求内同步解析，超大文件会占用一个 API worker。
- 备份目前只有脚本，没有定时执行和恢复演练。
- 推送通知、内容审核、运营后台、CD 自动化尚未实现。
- 争吵模式和询问中心已下线，相关表、接口、迁移和文档均已清理。

---

## 8. 测试

```bash
uv run pytest
```

当前共 146 个测试，覆盖认证、金币、秘密、日记、清单、账本、商城、每日一问、纪念日、模拟 TA、Agent、聊天导入、隐私、限流、幂等、加密、上传等模块。
