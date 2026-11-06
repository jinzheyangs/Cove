# Cove 接口文档

> 由 `scripts/generate_api_doc.py` 从代码自动生成，请勿手改。

## 基础约定

```
Base URL: https://<你的域名>/api/v1
鉴权:     Authorization: Bearer <access_token>
编码:     application/json; charset=utf-8
```

### 统一响应结构

```json
{ "code": 0, "message": "success", "data": {} }
```

- `code = 0` 表示成功；非 0 时看 `message`
- HTTP 状态码和 `code` 是两套体系：HTTP 表示传输层结果，`code` 是业务错误码

### 认证流程

1. `POST /auth/register` 或 `POST /auth/login` 拿到 `access_token` 和 `refresh_token`
2. 之后每个请求带 `Authorization: Bearer <access_token>`
3. `access_token` 默认 30 分钟过期，用 `POST /auth/refresh` 换新的一对令牌
4. 刷新会轮换 `refresh_token`：旧值立即失效，客户端必须保存新值
5. `POST /auth/logout` 吊销当前 refresh token；`POST /auth/logout-all` 吊销全部设备

### 分页

列表接口统一使用 `limit` + `offset`：

- `limit` 默认 20 或 50，最大 100
- `offset` 从 0 开始
- 返回 `data` 是数组，没有额外的 total 字段

### 权限

- 除 `/auth/*` 外，全部接口都需要登录
- 带「情侣」的接口还要求已绑定伴侣，否则返回 `code=3001`
- 所有资源都会校验是否属于当前关系，跨关系访问返回 404

### 业务错误码

| code | HTTP | 含义 |
|---:|---:|---|
| 401 | 401 | 未登录 / 用户不存在 / 登录已失效，请重新登录 |
| 1001 | 409 | 该手机号已注册 |
| 1002 | 401 | 手机号或密码错误 |
| 1003 | 429 | 尝试次数过多，请稍后再试 |
| 1005 | 401 | 登录已失效，请重新登录 |
| 1006 | 401 | 账号不存在 |
| 2001 | 409 | 你已经绑定过伴侣了 |
| 2002 | 500 | 邀请码生成失败，请重试 |
| 2003 | 404 | 邀请码无效 |
| 2004 | 410 | 邀请码已过期 |
| 2005 | 400 | 不能绑定自己 |
| 2006 | 409 | 对方已经绑定过伴侣了 |
| 2007 | 409 | 绑定失败，请重试 |
| 2008 | 400 | 请确认解除绑定 |
| 3001 | 409 | 还没有绑定伴侣 |
| 4001 | 409 | 金币不足 |
| 4002 | 400 | 金币数量不合法 |
| 4003 | 500 | 金币账户异常 |
| 5001 | 404 | 秘密不存在 |
| 5002 | 400 | 不能摘取自己的秘密 |
| 5003 | 409 | 这个秘密已经不可摘取了 |
| 5004 | 403 | 只能销毁自己发布的秘密 |
| 6001 | 409 | 待审批的申请太多了 |
| 6002 | 404 | 申请不存在 |
| 6003 | 403 | 不能审批自己的申请 |
| 6004 | 409 | 这条申请已经处理过了 |
| 7001 | 404 | 商品不存在 |
| 7002 | 403 | 不能审批自己上架的商品 |
| 7003 | 409 | 这个商品已经处理过了 |
| 7004 | 403 | 只能下架自己上架的商品 |
| 7005 | 409 | 只有已上架的商品可以下架 |
| 7006 | 409 | 这个商品还没上架 |
| 7007 | 400 | 不能购买自己上架的商品 |
| 7008 | 404 | 订单不存在 |
| 7009 | 409 | 这个订单已经处理过了 |
| 7010 | 403 | 只有提供服务的一方可以确认完成 |
| 7011 | 409 | 这件商品已经兑换完了 |
| 8001 | 404 | 日记不存在 |
| 8002 | 403 | 只能修改自己的日记 |
| 8003 | 403 | 只能删除自己的日记 |
| 9001 | 404 | 清单项不存在 |
| 9002 | 403 | 只能修改自己的清单 |
| 9003 | 409 | 这件事已经完成过了 |
| 10001 | 400 | 金额类支出必须填写金额 |
| 10002 | 400 | 非金钱付出不需要填写金额 |
| 10003 | 404 | 记录不存在 |
| 10004 | 403 | 只能修改自己记的账 |
| 11001 | 503 | AI 服务尚未配置 |
| 11003 | 503 | AI 服务暂时不可用 |
| 11004 | 503 | embedding 尚未配置 |
| 12001 | 409 | 已经有一个进行中的对话 |
| 12002 | 404 | 对话不存在 |
| 12003 | 409 | 这段对话已经不在交流阶段了 |
| 12004 | 409 | 只有进行中的对话可以进入冷静期 |
| 12005 | 409 | 当前状态不能结束对话 |
| 12006 | 409 | 现在还不能复盘，请先结束这段对话 |
| 13001 | 409 | 已经进入下一阶段，不能修改了 |
| 13002 | 409 | 这个询问已经生成过了 |
| 13003 | 409 | 双方都写完之后才能生成 |
| 13004 | 409 | 现在还不能补充意见 |
| 13005 | 409 | 当前状态不能关闭 |
| 13006 | 404 | 询问不存在 |
| 13007 | 503 | AI 分析暂时不可用，双方的想法已经保存，稍后再试 |
| 14001 | 403 | 对方还没有授权把 TA 的数据用于模拟 |
| 14002 | 503 | TA 的数字分身暂时连不上。真人一直在。 |
| 15001 | 403 | 密码错误 |
| 16001 | 400 | 只支持 JPEG / PNG / WebP 图片 / 文件内容与类型不符 |
| 16002 | 413 | 图片太大了 |
| 16003 | 400 | 文件为空 |
| 16004 | 403 | 无权删除这个文件 |
| 17001 | 404 | 会话不存在 |
| 17002 | 403 | 双方都授权后才能导入聊天记录 |
| 17003 | 413 | 单次导入的消息太多了，请拆分文件 |
| 17004 | 413 | 文件太大 |
| 17005 | 400 | 只支持 jsonl / json 格式 |
| 17006 | 404 | 伴侣不存在 |
| 17007 | 404 | 导入记录不存在 |
| 17008 | 400 | 只识别到一方的消息，请检查 owner_name / partner_name 是否和文件里的名字一致 |
| 17009 | 400 | 没有可导入的消息 |

> `429` 为限流；`500` 为未捕获异常，前端统一提示稍后重试。

## 接口总览

| 模块 | 方法 | 路径 | 说明 | 鉴权 |
|---|---|---|---|---|
| agent | GET | `/api/v1/agent/conversations` | 我发起过的会话，按最近活动排序。 | 是 |
| agent | POST | `/api/v1/agent/conversations` | 新建会话，被模拟对象固定为伴侣。 | 是 |
| agent | GET | `/api/v1/agent/conversations/{conversation_id}` | 会话详情，包含消息记录。 | 是 |
| agent | DELETE | `/api/v1/agent/conversations/{conversation_id}` | 删除会话及其全部消息。 | 是 |
| agent | POST | `/api/v1/agent/conversations/{conversation_id}/messages/stream` | 流式对话（SSE），工具调用也在流里。 | 是 |
| agent | GET | `/api/v1/agent/imports` | 查看历史导入记录和状态。 | 是 |
| agent | POST | `/api/v1/agent/imports` | 导入聊天记录。 | 是 |
| agent | GET | `/api/v1/agent/imports/{import_id}` | 查看单次导入的状态和计数。 | 是 |
| agent | DELETE | `/api/v1/agent/imports/{import_id}` | 删除一次导入：消息、向量、画像一起清理。 | 是 |
| audit | GET | `/api/v1/audit` | 查看自己发起过的敏感操作，时间倒序。 | 是 |
| auth | POST | `/api/v1/auth/login` | 手机号 + 密码登录。 | 否 |
| auth | POST | `/api/v1/auth/logout` | 登出当前设备：吊销传入的 refresh token。 | 否 |
| auth | POST | `/api/v1/auth/logout-all` | 退出所有设备：吊销该用户全部 refresh token。 | 是 |
| auth | POST | `/api/v1/auth/refresh` | 用 refresh token 换新的一对令牌。 | 否 |
| auth | POST | `/api/v1/auth/register` | 注册并直接返回登录态，省掉客户端再登录一次。 | 否 |
| bills | GET | `/api/v1/bills` | 列出可见账目，可按类型和共同/个人过滤。 | 是 |
| bills | POST | `/api/v1/bills` | 记一笔支出或付出。 | 是 |
| bills | GET | `/api/v1/bills/stats` | 统计汇总。只给共同视角，不提供个人对比。 | 是 |
| bills | PUT | `/api/v1/bills/{bill_id}` | 更新自己记的账。 | 是 |
| bills | DELETE | `/api/v1/bills/{bill_id}` | 删除自己记的账。 | 是 |
| coin-applies | GET | `/api/v1/coin-applies` | 我发起过的申请（所有状态）。 | 是 |
| coin-applies | POST | `/api/v1/coin-applies` | 发起申请。对方会在 /pending 里看到。 | 是 |
| coin-applies | GET | `/api/v1/coin-applies/pending` | 对方发起的、等我审批的申请。 | 是 |
| coin-applies | POST | `/api/v1/coin-applies/{apply_id}/approve` | 通过申请，可附带调整后的金额。 | 是 |
| coin-applies | POST | `/api/v1/coin-applies/{apply_id}/reject` | 拒绝申请，可附理由。 | 是 |
| coins | GET | `/api/v1/coins/balance` | 查询自己的金币余额。没绑定伴侣也可以查。 | 是 |
| coins | POST | `/api/v1/coins/gift` | 给对方赠币。 | 是 |
| coins | GET | `/api/v1/coins/transactions` | 分页查询自己的流水。 | 是 |
| conflicts | POST | `/api/v1/conflicts` | 发起会话。同一时间只能有一个未关闭的会话。 | 是 |
| conflicts | GET | `/api/v1/conflicts/{session_id}` | 查看会话详情：消息和复盘。 | 是 |
| conflicts | POST | `/api/v1/conflicts/{session_id}/cool` | 进入冷静期。 | 是 |
| conflicts | POST | `/api/v1/conflicts/{session_id}/end` | 结束交流，进入复盘阶段。 | 是 |
| conflicts | POST | `/api/v1/conflicts/{session_id}/messages` | 发送消息。 | 是 |
| conflicts | POST | `/api/v1/conflicts/{session_id}/review` | 提交复盘。 | 是 |
| couples | POST | `/api/v1/couples/bind` | 用对方的邀请码完成绑定。 | 是 |
| couples | POST | `/api/v1/couples/invite` | 生成邀请码，交给对方输入。24 小时内有效。 | 是 |
| couples | GET | `/api/v1/couples/me` | 查询当前关系。没绑定时 data 为 null，不是报错。 | 是 |
| couples | POST | `/api/v1/couples/unbind` | 解除绑定。必须显式传 confirm=true。 | 是 |
| daily | GET | `/api/v1/daily` | 今日问题与回答。没回答过时 my_answer 为 null。 | 是 |
| daily | POST | `/api/v1/daily` | 提交或修改今天的回答，返回更新后的视图。 | 是 |
| diaries | GET | `/api/v1/diaries` | 列出日记。 | 是 |
| diaries | POST | `/api/v1/diaries` | 新建日记。写同一件事时两个人传同一个 event_id。 | 是 |
| diaries | GET | `/api/v1/diaries/{diary_id}` | 读取单篇。只能读到本关系内的日记。 | 是 |
| diaries | PUT | `/api/v1/diaries/{diary_id}` | 部分更新。个人视角只有作者能改。 | 是 |
| diaries | DELETE | `/api/v1/diaries/{diary_id}` | 删除。个人视角只有作者能删。 | 是 |
| inquiries | POST | `/api/v1/inquiries` | 发起询问。返回精简信息，完整内容走详情接口。 | 是 |
| inquiries | GET | `/api/v1/inquiries/{session_id}` | 查看详情。双方都提交之前看不到彼此的内容。 | 是 |
| inquiries | POST | `/api/v1/inquiries/{session_id}/close` | 关闭询问，形成共同记录。 | 是 |
| inquiries | POST | `/api/v1/inquiries/{session_id}/generate` | 触发 AI 汇总。双方都提交后才允许。 | 是 |
| inquiries | POST | `/api/v1/inquiries/{session_id}/input` | 提交自己的真实想法。collecting 阶段可反复修改。 | 是 |
| inquiries | POST | `/api/v1/inquiries/{session_id}/supplement` | 在 AI 回复后追加补充意见。 | 是 |
| mall | GET | `/api/v1/mall/items` | 已上架商品列表（双方都能看到同一份）。 | 是 |
| mall | POST | `/api/v1/mall/items` | 上架商品，等待对方审批价格。 | 是 |
| mall | GET | `/api/v1/mall/items/mine` | 我上架的商品，包含待审批 / 被拒绝 / 已下架。 | 是 |
| mall | POST | `/api/v1/mall/items/{item_id}/approve` | 审批通过，可修改最终价格。 | 是 |
| mall | POST | `/api/v1/mall/items/{item_id}/offline` | 下架自己上架的商品。 | 是 |
| mall | POST | `/api/v1/mall/items/{item_id}/reject` | 拒绝上架。 | 是 |
| mall | GET | `/api/v1/mall/orders` | 关系内的全部订单。 | 是 |
| mall | POST | `/api/v1/mall/orders` | 购买商品：扣币并生成待兑现订单。 | 是 |
| mall | POST | `/api/v1/mall/orders/{order_id}/complete` | 服务提供方确认订单已完成。 | 是 |
| notifications | GET | `/api/v1/notifications` | 列出通知。unread_only=true 时只返回未读。 | 是 |
| notifications | POST | `/api/v1/notifications/read-all` | 全部标记已读。 | 是 |
| notifications | GET | `/api/v1/notifications/unread-count` | 未读数，用于红点。 | 是 |
| notifications | POST | `/api/v1/notifications/{notification_id}/read` | 标记单条已读。不是自己的通知不会更新。 | 是 |
| privacy | POST | `/api/v1/privacy/delete` | 注销账号。 | 是 |
| privacy | GET | `/api/v1/privacy/export` | 导出自己的全部个人数据（JSON）。 | 是 |
| secrets | GET | `/api/v1/secrets` | 对方发布、我还能摘的秘密。列表里没有内容。 | 是 |
| secrets | POST | `/api/v1/secrets` | 发布一条秘密。返回列表项，不回显内容。 | 是 |
| secrets | DELETE | `/api/v1/secrets` | 一键销毁自己发布的全部秘密，不碰对方的。 | 是 |
| secrets | GET | `/api/v1/secrets/mine` | 我发布的秘密，包含被摘取和已销毁的。 | 是 |
| secrets | DELETE | `/api/v1/secrets/{secret_id}` | 销毁单条。只能销毁自己发布的。 | 是 |
| secrets | POST | `/api/v1/secrets/{secret_id}/unlock` | 花金币摘取。成功才扣费，余额不足会返回 4001。 | 是 |
| sim-ta | GET | `/api/v1/sim-ta` | 查看双方的授权状态和自己的忠实度设置。 | 是 |
| sim-ta | POST | `/api/v1/sim-ta/chat` | 和对方的分身对话。 | 是 |
| sim-ta | PUT | `/api/v1/sim-ta/consent` | 开启 / 撤销「用我的数据做模拟」的授权。 | 是 |
| sim-ta | PUT | `/api/v1/sim-ta/settings` | 切换忠实度：更接近真实 / 更理想化。 | 是 |
| todos | GET | `/api/v1/todos` | 列出清单。用 type 切换共同 / 单人。 | 是 |
| todos | POST | `/api/v1/todos` | 新建清单项。 | 是 |
| todos | PUT | `/api/v1/todos/{todo_id}` | 部分更新。单人清单只有创建者能改。 | 是 |
| todos | DELETE | `/api/v1/todos/{todo_id}` | 删除清单项。 | 是 |
| todos | POST | `/api/v1/todos/{todo_id}/complete` | 完成清单项，同时返回一张纪念卡片。 | 是 |
| uploads | POST | `/api/v1/uploads/diary-image` | 上传一张日记图片。 | 是 |
| uploads | DELETE | `/api/v1/uploads/{key}` | 删除当前关系内的一张图片。key 必须属于当前 couple。 | 是 |
| users | GET | `/api/v1/users/me` | 获取当前登录用户。依赖已保证 user 存在。 | 是 |
| ops | GET | `/health` | 进程存活检查。不访问数据库，用于负载均衡/容器探活。 | 否 |
| ops | GET | `/health/db` | 数据库连通性检查。数据库不可用时这里会抛 500。 | 否 |
| ops | GET | `/metrics` | Prometheus 指标端点。 | 否 |

## 接口详情

### agent

#### `GET /api/v1/agent/conversations`

我发起过的会话，按最近活动排序。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `target_id` | int | 是 |
| `title` | string? | 是 |
| `persist` | bool | 是 |
| `created_at` | datetime | 是 |
| `updated_at` | datetime | 是 |
| `expires_at` | datetime | 是 |

---

#### `POST /api/v1/agent/conversations`

新建会话，被模拟对象固定为伴侣。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `title` | string? | 否 |
| `persist` | bool | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `target_id` | int | 是 |
| `title` | string? | 是 |
| `persist` | bool | 是 |
| `created_at` | datetime | 是 |
| `updated_at` | datetime | 是 |
| `expires_at` | datetime | 是 |

---

#### `GET /api/v1/agent/conversations/{conversation_id}`

会话详情，包含消息记录。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `conversation_id` | int | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `target_id` | int | 是 |
| `title` | string? | 是 |
| `persist` | bool | 是 |
| `created_at` | datetime | 是 |
| `updated_at` | datetime | 是 |
| `expires_at` | datetime | 是 |
| `messages` | app__modules__agent__schemas__MessageOut[] | 是 |

---

#### `DELETE /api/v1/agent/conversations/{conversation_id}`

删除会话及其全部消息。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `conversation_id` | int | 是 |

**响应 data**：`null` / `object`（见实现）

---

#### `POST /api/v1/agent/conversations/{conversation_id}/messages/stream`

流式对话（SSE），工具调用也在流里。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `conversation_id` | int | 是 |

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `message` | string | 是 |
| `history` | ChatTurn[] | 否 |

**响应 data**：`null` / `object`（见实现）

---

#### `GET /api/v1/agent/imports`

查看历史导入记录和状态。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `filename` | string | 是 |
| `format` | string | 是 |
| `status` | string | 是 |
| `total_messages` | int | 是 |
| `imported_messages` | int | 是 |
| `indexed_windows` | int | 是 |
| `skipped_messages` | int | 是 |
| `error` | string? | 是 |
| `created_at` | datetime | 是 |
| `finished_at` | datetime? | 是 |

---

#### `POST /api/v1/agent/imports`

导入聊天记录。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `filename` | string | 是 |
| `format` | string | 是 |
| `status` | string | 是 |
| `total_messages` | int | 是 |
| `imported_messages` | int | 是 |
| `indexed_windows` | int | 是 |
| `skipped_messages` | int | 是 |
| `error` | string? | 是 |
| `created_at` | datetime | 是 |
| `finished_at` | datetime? | 是 |

---

#### `GET /api/v1/agent/imports/{import_id}`

查看单次导入的状态和计数。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `import_id` | int | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `filename` | string | 是 |
| `format` | string | 是 |
| `status` | string | 是 |
| `total_messages` | int | 是 |
| `imported_messages` | int | 是 |
| `indexed_windows` | int | 是 |
| `skipped_messages` | int | 是 |
| `error` | string? | 是 |
| `created_at` | datetime | 是 |
| `finished_at` | datetime? | 是 |

---

#### `DELETE /api/v1/agent/imports/{import_id}`

删除一次导入：消息、向量、画像一起清理。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `import_id` | int | 是 |

**响应 data**：`null` / `object`（见实现）

---

### audit

#### `GET /api/v1/audit`

查看自己发起过的敏感操作，时间倒序。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| query | `limit` | int | 否 |
| query | `offset` | int | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `action` | string | 是 |
| `target_type` | string? | 是 |
| `target_id` | int? | 是 |
| `detail` | object? | 是 |
| `ip` | string? | 是 |
| `request_id` | string? | 是 |
| `created_at` | datetime | 是 |

---

### auth

#### `POST /api/v1/auth/login`

手机号 + 密码登录。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `phone` | string | 是 |
| `password` | string | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `access_token` | string | 是 |
| `refresh_token` | string | 是 |
| `token_type` | string | 否 |
| `expires_in` | int | 是 |
| `user` | UserOut | 是 |

---

#### `POST /api/v1/auth/logout`

登出当前设备：吊销传入的 refresh token。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `refresh_token` | string | 是 |

**响应 data**：`null` / `object`（见实现）

---

#### `POST /api/v1/auth/logout-all`

退出所有设备：吊销该用户全部 refresh token。

**响应 data**：`null` / `object`（见实现）

---

#### `POST /api/v1/auth/refresh`

用 refresh token 换新的一对令牌。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `refresh_token` | string | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `access_token` | string | 是 |
| `refresh_token` | string | 是 |
| `token_type` | string | 否 |
| `expires_in` | int | 是 |
| `user` | UserOut | 是 |

---

#### `POST /api/v1/auth/register`

注册并直接返回登录态，省掉客户端再登录一次。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `phone` | string | 是 |
| `password` | string | 是 |
| `nickname` | string | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `access_token` | string | 是 |
| `refresh_token` | string | 是 |
| `token_type` | string | 否 |
| `expires_in` | int | 是 |
| `user` | UserOut | 是 |

---

### bills

#### `GET /api/v1/bills`

列出可见账目，可按类型和共同/个人过滤。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| query | `type` | string? | 否 |
| query | `scope` | string? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `payer_id` | int | 是 |
| `amount` | string? | 是 |
| `category` | string | 是 |
| `type` | string | 是 |
| `scope` | string | 是 |
| `is_private` | bool | 是 |
| `remark` | string? | 是 |
| `created_at` | datetime | 是 |

---

#### `POST /api/v1/bills`

记一笔支出或付出。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `amount` | number \| string? | 否 |
| `category` | string | 是 |
| `type` | "money" \| "time" \| "energy" \| "emotion" | 否 |
| `scope` | "shared" \| "personal" | 否 |
| `is_private` | bool | 否 |
| `remark` | string? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `payer_id` | int | 是 |
| `amount` | string? | 是 |
| `category` | string | 是 |
| `type` | string | 是 |
| `scope` | string | 是 |
| `is_private` | bool | 是 |
| `remark` | string? | 是 |
| `created_at` | datetime | 是 |

---

#### `GET /api/v1/bills/stats`

统计汇总。只给共同视角，不提供个人对比。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `count` | int | 是 |
| `money_total` | string | 是 |
| `shared_total` | string | 是 |
| `personal_total` | string | 是 |
| `by_category` | CategoryStat[] | 是 |
| `non_money_counts` | object | 是 |

---

#### `PUT /api/v1/bills/{bill_id}`

更新自己记的账。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `bill_id` | int | 是 |

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `amount` | number \| string? | 否 |
| `category` | string | 是 |
| `type` | "money" \| "time" \| "energy" \| "emotion" | 否 |
| `scope` | "shared" \| "personal" | 否 |
| `is_private` | bool | 否 |
| `remark` | string? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `payer_id` | int | 是 |
| `amount` | string? | 是 |
| `category` | string | 是 |
| `type` | string | 是 |
| `scope` | string | 是 |
| `is_private` | bool | 是 |
| `remark` | string? | 是 |
| `created_at` | datetime | 是 |

---

#### `DELETE /api/v1/bills/{bill_id}`

删除自己记的账。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `bill_id` | int | 是 |

**响应 data**：`null` / `object`（见实现）

---

### coin-applies

#### `GET /api/v1/coin-applies`

我发起过的申请（所有状态）。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `applicant_id` | int | 是 |
| `amount` | int | 是 |
| `reason` | string | 是 |
| `status` | string | 是 |
| `approved_amount` | int? | 是 |
| `decision_remark` | string? | 是 |
| `created_at` | datetime | 是 |
| `decided_at` | datetime? | 是 |

---

#### `POST /api/v1/coin-applies`

发起申请。对方会在 /pending 里看到。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `amount` | int | 是 |
| `reason` | string | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `applicant_id` | int | 是 |
| `amount` | int | 是 |
| `reason` | string | 是 |
| `status` | string | 是 |
| `approved_amount` | int? | 是 |
| `decision_remark` | string? | 是 |
| `created_at` | datetime | 是 |
| `decided_at` | datetime? | 是 |

---

#### `GET /api/v1/coin-applies/pending`

对方发起的、等我审批的申请。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `applicant_id` | int | 是 |
| `amount` | int | 是 |
| `reason` | string | 是 |
| `status` | string | 是 |
| `approved_amount` | int? | 是 |
| `decision_remark` | string? | 是 |
| `created_at` | datetime | 是 |
| `decided_at` | datetime? | 是 |

---

#### `POST /api/v1/coin-applies/{apply_id}/approve`

通过申请，可附带调整后的金额。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `apply_id` | int | 是 |

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `amount` | int? | 否 |
| `remark` | string? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `applicant_id` | int | 是 |
| `amount` | int | 是 |
| `reason` | string | 是 |
| `status` | string | 是 |
| `approved_amount` | int? | 是 |
| `decision_remark` | string? | 是 |
| `created_at` | datetime | 是 |
| `decided_at` | datetime? | 是 |

---

#### `POST /api/v1/coin-applies/{apply_id}/reject`

拒绝申请，可附理由。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `apply_id` | int | 是 |

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `remark` | string? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `applicant_id` | int | 是 |
| `amount` | int | 是 |
| `reason` | string | 是 |
| `status` | string | 是 |
| `approved_amount` | int? | 是 |
| `decision_remark` | string? | 是 |
| `created_at` | datetime | 是 |
| `decided_at` | datetime? | 是 |

---

### coins

#### `GET /api/v1/coins/balance`

查询自己的金币余额。没绑定伴侣也可以查。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `balance` | int | 是 |

---

#### `POST /api/v1/coins/gift`

给对方赠币。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `amount` | int | 是 |
| `remark` | string? | 否 |
| `idempotency_key` | string? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `type` | string | 是 |
| `direction` | string | 是 |
| `amount` | int | 是 |
| `from_user_id` | int? | 是 |
| `to_user_id` | int? | 是 |
| `ref_type` | string? | 是 |
| `ref_id` | int? | 是 |
| `remark` | string? | 是 |
| `created_at` | datetime | 是 |

---

#### `GET /api/v1/coins/transactions`

分页查询自己的流水。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| query | `limit` | int | 否 |
| query | `offset` | int | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `type` | string | 是 |
| `direction` | string | 是 |
| `amount` | int | 是 |
| `from_user_id` | int? | 是 |
| `to_user_id` | int? | 是 |
| `ref_type` | string? | 是 |
| `ref_id` | int? | 是 |
| `remark` | string? | 是 |
| `created_at` | datetime | 是 |

---

### conflicts

#### `POST /api/v1/conflicts`

发起会话。同一时间只能有一个未关闭的会话。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `status` | string | 是 |
| `started_at` | datetime | 是 |
| `ended_at` | datetime? | 是 |

---

#### `GET /api/v1/conflicts/{session_id}`

查看会话详情：消息和复盘。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `session_id` | int | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `status` | string | 是 |
| `started_at` | datetime | 是 |
| `ended_at` | datetime? | 是 |
| `messages` | app__modules__conflicts__schemas__MessageOut[] | 是 |
| `reviews` | ReviewOut[] | 是 |

---

#### `POST /api/v1/conflicts/{session_id}/cool`

进入冷静期。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `session_id` | int | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `status` | string | 是 |
| `started_at` | datetime | 是 |
| `ended_at` | datetime? | 是 |

---

#### `POST /api/v1/conflicts/{session_id}/end`

结束交流，进入复盘阶段。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `session_id` | int | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `status` | string | 是 |
| `started_at` | datetime | 是 |
| `ended_at` | datetime? | 是 |

---

#### `POST /api/v1/conflicts/{session_id}/messages`

发送消息。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `session_id` | int | 是 |

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `content` | string | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `message` | app__modules__conflicts__schemas__MessageOut | 是 |
| `gentle_prompt` | string? | 否 |

---

#### `POST /api/v1/conflicts/{session_id}/review`

提交复盘。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `session_id` | int | 是 |

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `want_to_be_understood` | string | 是 |
| `heard_partner_need` | string | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `status` | string | 是 |
| `started_at` | datetime | 是 |
| `ended_at` | datetime? | 是 |

---

### couples

#### `POST /api/v1/couples/bind`

用对方的邀请码完成绑定。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `code` | string | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `user1_id` | int | 是 |
| `user2_id` | int | 是 |
| `bind_at` | datetime | 是 |

---

#### `POST /api/v1/couples/invite`

生成邀请码，交给对方输入。24 小时内有效。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `code` | string | 是 |
| `expires_at` | datetime | 是 |

---

#### `GET /api/v1/couples/me`

查询当前关系。没绑定时 data 为 null，不是报错。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `user1_id` | int | 是 |
| `user2_id` | int | 是 |
| `bind_at` | datetime | 是 |

---

#### `POST /api/v1/couples/unbind`

解除绑定。必须显式传 confirm=true。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `confirm` | bool | 否 |
| `reason` | string? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `user1_id` | int | 是 |
| `user2_id` | int | 是 |
| `bind_at` | datetime | 是 |

---

### daily

#### `GET /api/v1/daily`

今日问题与回答。没回答过时 my_answer 为 null。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `day` | date | 是 |
| `question` | string | 是 |
| `my_answer` | string? | 是 |
| `partner_answer` | string? | 是 |

---

#### `POST /api/v1/daily`

提交或修改今天的回答，返回更新后的视图。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `answer` | string | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `day` | date | 是 |
| `question` | string | 是 |
| `my_answer` | string? | 是 |
| `partner_answer` | string? | 是 |

---

### diaries

#### `GET /api/v1/diaries`

列出日记。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| query | `mode` | string? | 否 |
| query | `event_id` | string? | 否 |
| query | `limit` | int | 否 |
| query | `offset` | int | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `event_id` | string? | 是 |
| `mode` | string | 是 |
| `title` | string? | 是 |
| `content` | string | 是 |
| `mood_tags` | string[] | 是 |
| `location` | string? | 是 |
| `images` | string[] | 是 |
| `image_urls` | string[] | 否 |
| `author_id` | int | 是 |
| `created_at` | datetime | 是 |
| `updated_at` | datetime | 是 |

---

#### `POST /api/v1/diaries`

新建日记。写同一件事时两个人传同一个 event_id。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `mode` | "shared" \| "personal" | 否 |
| `title` | string? | 否 |
| `content` | string | 是 |
| `mood_tags` | string[] | 否 |
| `location` | string? | 否 |
| `images` | string[] | 否 |
| `event_id` | string? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `event_id` | string? | 是 |
| `mode` | string | 是 |
| `title` | string? | 是 |
| `content` | string | 是 |
| `mood_tags` | string[] | 是 |
| `location` | string? | 是 |
| `images` | string[] | 是 |
| `image_urls` | string[] | 否 |
| `author_id` | int | 是 |
| `created_at` | datetime | 是 |
| `updated_at` | datetime | 是 |

---

#### `GET /api/v1/diaries/{diary_id}`

读取单篇。只能读到本关系内的日记。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `diary_id` | int | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `event_id` | string? | 是 |
| `mode` | string | 是 |
| `title` | string? | 是 |
| `content` | string | 是 |
| `mood_tags` | string[] | 是 |
| `location` | string? | 是 |
| `images` | string[] | 是 |
| `image_urls` | string[] | 否 |
| `author_id` | int | 是 |
| `created_at` | datetime | 是 |
| `updated_at` | datetime | 是 |

---

#### `PUT /api/v1/diaries/{diary_id}`

部分更新。个人视角只有作者能改。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `diary_id` | int | 是 |

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `title` | string? | 否 |
| `content` | string? | 否 |
| `mood_tags` | string[]? | 否 |
| `location` | string? | 否 |
| `images` | string[]? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `event_id` | string? | 是 |
| `mode` | string | 是 |
| `title` | string? | 是 |
| `content` | string | 是 |
| `mood_tags` | string[] | 是 |
| `location` | string? | 是 |
| `images` | string[] | 是 |
| `image_urls` | string[] | 否 |
| `author_id` | int | 是 |
| `created_at` | datetime | 是 |
| `updated_at` | datetime | 是 |

---

#### `DELETE /api/v1/diaries/{diary_id}`

删除。个人视角只有作者能删。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `diary_id` | int | 是 |

**响应 data**：`null` / `object`（见实现）

---

### inquiries

#### `POST /api/v1/inquiries`

发起询问。返回精简信息，完整内容走详情接口。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `question` | string | 是 |

**响应 data**：`null` / `object`（见实现）

---

#### `GET /api/v1/inquiries/{session_id}`

查看详情。双方都提交之前看不到彼此的内容。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `session_id` | int | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `question` | string | 是 |
| `status` | string | 是 |
| `ai_response` | string? | 是 |
| `submitted_count` | int | 是 |
| `my_input_submitted` | bool | 是 |
| `inputs` | string[] | 是 |
| `supplements` | string[] | 是 |
| `created_at` | datetime | 是 |
| `closed_at` | datetime? | 是 |

---

#### `POST /api/v1/inquiries/{session_id}/close`

关闭询问，形成共同记录。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `session_id` | int | 是 |

**响应 data**：`null` / `object`（见实现）

---

#### `POST /api/v1/inquiries/{session_id}/generate`

触发 AI 汇总。双方都提交后才允许。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `session_id` | int | 是 |

**响应 data**：`null` / `object`（见实现）

---

#### `POST /api/v1/inquiries/{session_id}/input`

提交自己的真实想法。collecting 阶段可反复修改。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `session_id` | int | 是 |

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `content` | string | 是 |

**响应 data**：`null` / `object`（见实现）

---

#### `POST /api/v1/inquiries/{session_id}/supplement`

在 AI 回复后追加补充意见。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `session_id` | int | 是 |

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `content` | string | 是 |

**响应 data**：`null` / `object`（见实现）

---

### mall

#### `GET /api/v1/mall/items`

已上架商品列表（双方都能看到同一份）。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `creator_id` | int | 是 |
| `title` | string | 是 |
| `description` | string? | 是 |
| `price_coins` | int | 是 |
| `approved_price` | int? | 是 |
| `max_orders` | int? | 是 |
| `status` | string | 是 |
| `reject_reason` | string? | 是 |
| `created_at` | datetime | 是 |

---

#### `POST /api/v1/mall/items`

上架商品，等待对方审批价格。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `title` | string | 是 |
| `description` | string? | 否 |
| `price_coins` | int | 是 |
| `max_orders` | int? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `creator_id` | int | 是 |
| `title` | string | 是 |
| `description` | string? | 是 |
| `price_coins` | int | 是 |
| `approved_price` | int? | 是 |
| `max_orders` | int? | 是 |
| `status` | string | 是 |
| `reject_reason` | string? | 是 |
| `created_at` | datetime | 是 |

---

#### `GET /api/v1/mall/items/mine`

我上架的商品，包含待审批 / 被拒绝 / 已下架。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `creator_id` | int | 是 |
| `title` | string | 是 |
| `description` | string? | 是 |
| `price_coins` | int | 是 |
| `approved_price` | int? | 是 |
| `max_orders` | int? | 是 |
| `status` | string | 是 |
| `reject_reason` | string? | 是 |
| `created_at` | datetime | 是 |

---

#### `POST /api/v1/mall/items/{item_id}/approve`

审批通过，可修改最终价格。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `item_id` | int | 是 |

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `price_coins` | int? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `creator_id` | int | 是 |
| `title` | string | 是 |
| `description` | string? | 是 |
| `price_coins` | int | 是 |
| `approved_price` | int? | 是 |
| `max_orders` | int? | 是 |
| `status` | string | 是 |
| `reject_reason` | string? | 是 |
| `created_at` | datetime | 是 |

---

#### `POST /api/v1/mall/items/{item_id}/offline`

下架自己上架的商品。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `item_id` | int | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `creator_id` | int | 是 |
| `title` | string | 是 |
| `description` | string? | 是 |
| `price_coins` | int | 是 |
| `approved_price` | int? | 是 |
| `max_orders` | int? | 是 |
| `status` | string | 是 |
| `reject_reason` | string? | 是 |
| `created_at` | datetime | 是 |

---

#### `POST /api/v1/mall/items/{item_id}/reject`

拒绝上架。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `item_id` | int | 是 |

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `reason` | string? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `creator_id` | int | 是 |
| `title` | string | 是 |
| `description` | string? | 是 |
| `price_coins` | int | 是 |
| `approved_price` | int? | 是 |
| `max_orders` | int? | 是 |
| `status` | string | 是 |
| `reject_reason` | string? | 是 |
| `created_at` | datetime | 是 |

---

#### `GET /api/v1/mall/orders`

关系内的全部订单。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `item_id` | int | 是 |
| `buyer_id` | int | 是 |
| `price` | int | 是 |
| `status` | string | 是 |
| `completed_at` | datetime? | 是 |
| `created_at` | datetime | 是 |

---

#### `POST /api/v1/mall/orders`

购买商品：扣币并生成待兑现订单。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `item_id` | int | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `item_id` | int | 是 |
| `buyer_id` | int | 是 |
| `price` | int | 是 |
| `status` | string | 是 |
| `completed_at` | datetime? | 是 |
| `created_at` | datetime | 是 |

---

#### `POST /api/v1/mall/orders/{order_id}/complete`

服务提供方确认订单已完成。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `order_id` | int | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `item_id` | int | 是 |
| `buyer_id` | int | 是 |
| `price` | int | 是 |
| `status` | string | 是 |
| `completed_at` | datetime? | 是 |
| `created_at` | datetime | 是 |

---

### notifications

#### `GET /api/v1/notifications`

列出通知。unread_only=true 时只返回未读。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| query | `unread_only` | bool | 否 |
| query | `limit` | int | 否 |
| query | `offset` | int | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `type` | string | 是 |
| `title` | string | 是 |
| `content` | string? | 是 |
| `related_type` | string? | 是 |
| `related_id` | int? | 是 |
| `is_read` | bool | 是 |
| `created_at` | datetime | 是 |

---

#### `POST /api/v1/notifications/read-all`

全部标记已读。

**响应 data**：`null` / `object`（见实现）

---

#### `GET /api/v1/notifications/unread-count`

未读数，用于红点。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `unread` | int | 是 |

---

#### `POST /api/v1/notifications/{notification_id}/read`

标记单条已读。不是自己的通知不会更新。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `notification_id` | int | 是 |

**响应 data**：`null` / `object`（见实现）

---

### privacy

#### `POST /api/v1/privacy/delete`

注销账号。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `password` | string | 是 |

**响应 data**：`null` / `object`（见实现）

---

#### `GET /api/v1/privacy/export`

导出自己的全部个人数据（JSON）。

**响应 data**：`null` / `object`（见实现）

---

### secrets

#### `GET /api/v1/secrets`

对方发布、我还能摘的秘密。列表里没有内容。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `level` | string | 是 |
| `cost_coins` | int | 是 |
| `is_burn_after_read` | bool | 是 |
| `status` | string | 是 |
| `authored_by_me` | bool | 是 |
| `viewed` | bool | 是 |
| `created_at` | datetime | 是 |

---

#### `POST /api/v1/secrets`

发布一条秘密。返回列表项，不回显内容。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `content` | string | 是 |
| `level` | "normal" \| "deep" | 否 |
| `cost_coins` | int? | 否 |
| `is_burn_after_read` | bool | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `level` | string | 是 |
| `cost_coins` | int | 是 |
| `is_burn_after_read` | bool | 是 |
| `status` | string | 是 |
| `authored_by_me` | bool | 是 |
| `viewed` | bool | 是 |
| `created_at` | datetime | 是 |

---

#### `DELETE /api/v1/secrets`

一键销毁自己发布的全部秘密，不碰对方的。

**响应 data**：`null` / `object`（见实现）

---

#### `GET /api/v1/secrets/mine`

我发布的秘密，包含被摘取和已销毁的。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `level` | string | 是 |
| `cost_coins` | int | 是 |
| `is_burn_after_read` | bool | 是 |
| `status` | string | 是 |
| `authored_by_me` | bool | 是 |
| `viewed` | bool | 是 |
| `created_at` | datetime | 是 |

---

#### `DELETE /api/v1/secrets/{secret_id}`

销毁单条。只能销毁自己发布的。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `secret_id` | int | 是 |

**响应 data**：`null` / `object`（见实现）

---

#### `POST /api/v1/secrets/{secret_id}/unlock`

花金币摘取。成功才扣费，余额不足会返回 4001。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `secret_id` | int | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `content` | string | 是 |
| `level` | string | 是 |
| `cost_coins` | int | 是 |
| `is_burn_after_read` | bool | 是 |
| `status` | string | 是 |
| `created_at` | datetime | 是 |

---

### sim-ta

#### `GET /api/v1/sim-ta`

查看双方的授权状态和自己的忠实度设置。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `my_consent` | bool | 是 |
| `partner_consent` | bool | 是 |
| `fidelity` | string | 是 |

---

#### `POST /api/v1/sim-ta/chat`

和对方的分身对话。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `message` | string | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `reply` | string | 是 |
| `fidelity` | string | 是 |
| `disclaimer` | string | 是 |

---

#### `PUT /api/v1/sim-ta/consent`

开启 / 撤销「用我的数据做模拟」的授权。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `authorized` | bool | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `my_consent` | bool | 是 |
| `partner_consent` | bool | 是 |
| `fidelity` | string | 是 |

---

#### `PUT /api/v1/sim-ta/settings`

切换忠实度：更接近真实 / 更理想化。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `fidelity` | "faithful" \| "idealized" | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `my_consent` | bool | 是 |
| `partner_consent` | bool | 是 |
| `fidelity` | string | 是 |

---

### todos

#### `GET /api/v1/todos`

列出清单。用 type 切换共同 / 单人。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| query | `type` | string? | 否 |
| query | `category` | string? | 否 |
| query | `status` | string? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `type` | string | 是 |
| `category` | string | 是 |
| `title` | string | 是 |
| `description` | string? | 是 |
| `status` | string | 是 |
| `creator_id` | int | 是 |
| `completed_at` | datetime? | 是 |
| `created_at` | datetime | 是 |

---

#### `POST /api/v1/todos`

新建清单项。

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `type` | "shared" \| "personal" | 否 |
| `category` | string | 是 |
| `title` | string | 是 |
| `description` | string? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `type` | string | 是 |
| `category` | string | 是 |
| `title` | string | 是 |
| `description` | string? | 是 |
| `status` | string | 是 |
| `creator_id` | int | 是 |
| `completed_at` | datetime? | 是 |
| `created_at` | datetime | 是 |

---

#### `PUT /api/v1/todos/{todo_id}`

部分更新。单人清单只有创建者能改。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `todo_id` | int | 是 |

**请求体**

| 字段 | 类型 | 必填 |
|---|---|---|
| `category` | string? | 否 |
| `title` | string? | 否 |
| `description` | string? | 否 |
| `status` | "pending" \| "completed" \| "cancelled"? | 否 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `type` | string | 是 |
| `category` | string | 是 |
| `title` | string | 是 |
| `description` | string? | 是 |
| `status` | string | 是 |
| `creator_id` | int | 是 |
| `completed_at` | datetime? | 是 |
| `created_at` | datetime | 是 |

---

#### `DELETE /api/v1/todos/{todo_id}`

删除清单项。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `todo_id` | int | 是 |

**响应 data**：`null` / `object`（见实现）

---

#### `POST /api/v1/todos/{todo_id}/complete`

完成清单项，同时返回一张纪念卡片。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `todo_id` | int | 是 |

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `todo` | TodoOut | 是 |
| `card` | MemoryCard | 是 |

---

### uploads

#### `POST /api/v1/uploads/diary-image`

上传一张日记图片。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `key` | string | 是 |
| `url` | string | 是 |
| `size` | int | 是 |
| `content_type` | string | 是 |

---

#### `DELETE /api/v1/uploads/{key}`

删除当前关系内的一张图片。key 必须属于当前 couple。

**参数**

| 位置 | 名称 | 类型 | 必填 |
|---|---|---|---|
| path | `key` | string | 是 |

**响应 data**：`null` / `object`（见实现）

---

### users

#### `GET /api/v1/users/me`

获取当前登录用户。依赖已保证 user 存在。

**响应 data**

| 字段 | 类型 | 必填 |
|---|---|---|
| `id` | int | 是 |
| `phone` | string | 是 |
| `nickname` | string | 是 |
| `avatar` | string? | 否 |
| `created_at` | datetime | 是 |

---

### ops

#### `GET /health`

进程存活检查。不访问数据库，用于负载均衡/容器探活。

**响应 data**：`null` / `object`（见实现）

---

#### `GET /health/db`

数据库连通性检查。数据库不可用时这里会抛 500。

**响应 data**：`null` / `object`（见实现）

---

#### `GET /metrics`

Prometheus 指标端点。

**响应 data**：`null` / `object`（见实现）

---
