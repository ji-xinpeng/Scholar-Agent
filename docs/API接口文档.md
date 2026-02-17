# Scholar Agent 后端 API 接口文档

> 版本: v1.1 | 更新日期: 2026-02-16
>
> Base URL: `http://localhost:8001/api/v1`
>
> 通用规则：
> - 所有 JSON 请求体使用 `Content-Type: application/json`
> - 文件上传使用 `Content-Type: multipart/form-data`
> - 成功响应 HTTP 200，错误响应 HTTP 4xx/5xx
> - 所有 ID 字段均为 UUID 字符串
> - 时间字段均为 ISO 8601 格式（UTC）

---

## 目录

1. [健康检查](#1-健康检查)
2. [聊天与会话](#2-聊天与会话)
3. [文档管理](#3-文档管理)
4. [文件夹管理](#4-文件夹管理)
5. [用户中心](#5-用户中心)
6. [SSE 事件协议](#6-sse-事件协议)
7. [数据结构速查](#7-数据结构速查)

---

## 1. 健康检查

### `GET /health`

> 检查服务是否正常运行。

**请求**: 无参数

**响应**:
```json
{
  "status": "ok",
  "service": "Scholar Agent"
}
```

---

## 2. 聊天与会话

### 2.1 发送消息（SSE 流式）

### `POST /api/v1/chat/chat`

> 核心接口。前端发送用户消息，后端以 SSE（Server-Sent Events）流式返回处理过程和回答。

**请求体**:
```json
{
  "message": "大语言模型推理能力的最新进展有哪些？",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",  // 可选，为空则自动创建新会话
  "user_id": "default",
  "mode": "normal",       // "normal" = 普通问答 | "agent" = 智能体模式
  "web_search": false      // 是否启用联网搜索
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | ✅ | 用户消息内容 |
| session_id | string\|null | ❌ | 会话ID，为空时自动创建新会话 |
| user_id | string | ❌ | 用户ID，默认 "default" |
| mode | string | ❌ | "normal" 或 "agent"，默认 "normal" |
| web_search | boolean | ❌ | 是否联网搜索，默认 false |

**响应**: `Content-Type: text/event-stream`

**响应头**:
| 头 | 说明 |
|----|------|
| `X-Session-Id` | 本次对话的会话 ID（前端首次对话时用此建立会话绑定） |
| `Cache-Control` | no-cache |
| `Connection` | keep-alive |

**SSE 事件格式**: 见 [第6节 SSE 事件协议](#6-sse-事件协议)

**额度不足错误 (HTTP 402)**:

当用户免费额度用完或付费余额不足时，返回 HTTP 402：

Response:
```json
{
  "detail": {
    "reason": "free_quota_exceeded | insufficient_balance",
    "message": "免费额度已用完...",
    "balance": 0.0,
    "model_mode": "free"
  }
}
```

**后端处理流程**:
1. 若 `session_id` 为空或不存在 → 创建新会话
2. 将用户消息存入 messages 表
3. 根据 `mode` 选择处理逻辑：
   - `normal`: 直接生成回答，以 `stream` 事件逐块推送
   - `agent`: 先推送 `plan` 事件，然后依次推送每个步骤的 `step_start` → `step_progress` → `step_complete`，中间穿插 `stream` 事件
4. 最后推送 `done` 事件
5. 将助手完整回答存入 messages 表

---

### 2.2 获取会话列表

### `GET /api/v1/chat/sessions`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string (query) | ❌ | 默认 "default" |

**响应**:
```json
{
  "sessions": [
    {
      "id": "550e8400-...",
      "user_id": "default",
      "title": "大语言模型推理能力的最新进展有哪些？",
      "mode": "normal",
      "created_at": "2026-02-16T06:30:00.000000",
      "updated_at": "2026-02-16T06:35:00.000000"
    }
  ],
  "total": 1
}
```

> **排序规则**: 按 `updated_at` 降序（最新的在前）
>
> **title 自动生成规则**: 首次用户消息的前 50 个字符，超出加 "..."

---

### 2.3 创建会话

### `POST /api/v1/chat/sessions`

**请求体**:
```json
{
  "user_id": "default",
  "title": "新建对话",
  "mode": "normal"
}
```

**响应**: 返回创建的会话对象（同上 session 结构）

---

### 2.4 删除会话

### `DELETE /api/v1/chat/sessions/{session_id}`

> 同时删除该会话下的所有消息。

**响应**:
```json
{ "status": "ok" }
```

---

### 2.5 获取会话消息

### `GET /api/v1/chat/sessions/{session_id}/messages`

**响应**:
```json
{
  "messages": [
    {
      "id": "msg-uuid-...",
      "session_id": "550e8400-...",
      "role": "user",
      "content": "大语言模型推理能力的最新进展有哪些？",
      "msg_type": "text",
      "metadata": null,
      "created_at": "2026-02-16T06:30:00.000000"
    },
    {
      "id": "msg-uuid-...",
      "session_id": "550e8400-...",
      "role": "assistant",
      "content": "## 研究摘要...",
      "msg_type": "text",
      "metadata": {
        "mode": "agent",
        "papers": [...],
        "citations": [...]
      },
      "created_at": "2026-02-16T06:30:05.000000"
    }
  ]
}
```

> **排序**: 按 `created_at` 升序
>
> **role 取值**: "user" | "assistant"
>
> **metadata**: Agent 模式下包含 papers 和 citations 信息，普通模式为 null

---

## 3. 文档管理

### 3.1 上传文档

### `POST /api/v1/documents/upload`

> `Content-Type: multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | ✅ | 文档文件，支持 .pdf/.doc/.docx/.md/.txt |
| user_id | string | ❌ | 默认 "default" |
| folder_id | string | ❌ | 目标文件夹ID，为空则不归属文件夹 |

**限制**:
- 文件不能为空（400 错误）
- 单文件最大 100MB（400 错误）

**响应**:
```json
{
  "id": "doc-uuid-...",
  "user_id": "default",
  "folder_id": null,
  "filename": "doc-uuid-xxx.pdf",
  "original_name": "attention_is_all_you_need.pdf",
  "file_size": 2048576,
  "file_type": "pdf",
  "page_count": 0,
  "status": "uploaded",
  "created_at": "2026-02-16T06:30:00.000000"
}
```

> **file_type 映射规则**:
> | 扩展名 | file_type |
> |--------|-----------|
> | .pdf | pdf |
> | .doc / .docx | word |
> | .md | markdown |
> | .txt | text |
> | 其他 | other |

---

### 3.2 获取文档列表

### `GET /api/v1/documents/`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string (query) | ❌ | 默认 "default" |
| folder_id | string (query) | ❌ | 按文件夹筛选，为空则返回全部 |
| page | int (query) | ❌ | 页码，从 1 开始，默认 1 |
| page_size | int (query) | ❌ | 每页数量，1~100，默认 10 |

**响应**:
```json
{
  "documents": [
    {
      "id": "doc-uuid-...",
      "user_id": "default",
      "folder_id": "folder-uuid-...",
      "filename": "doc-uuid-xxx.pdf",
      "original_name": "attention.pdf",
      "file_path": "/path/to/file",
      "file_size": 2048576,
      "file_type": "pdf",
      "page_count": 0,
      "status": "uploaded",
      "created_at": "2026-02-16T06:30:00.000000"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 10
}
```

> **排序**: 按 `created_at` 降序
>
> **前端用到的字段**: `id`, `original_name`, `file_size`, `file_type`, `created_at`（用于列表渲染和删除）

---

### 3.3 获取单个文档

### `GET /api/v1/documents/{doc_id}`

**响应**: 同上单个文档对象

**错误**: 404 — `{"detail": "Document not found"}`

---

### 3.4 删除文档

### `DELETE /api/v1/documents/{doc_id}`

> 同时删除服务器上的物理文件。

**响应**:
```json
{ "status": "ok" }
```

**错误**: 404 — `{"detail": "Document not found"}`

---

### 3.5 移动文档到文件夹

### `PUT /api/v1/documents/{doc_id}/move`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| folder_id | string (query) | ❌ | 目标文件夹ID，为空则移出文件夹 |

**响应**:
```json
{ "status": "ok" }
```

---

## 4. 文件夹管理

### 4.1 创建文件夹

### `POST /api/v1/documents/folders`

**请求体**:
```json
{
  "user_id": "default",
  "name": "NLP论文",
  "parent_id": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | ❌ | 默认 "default" |
| name | string | ✅ | 文件夹名称 |
| parent_id | string\|null | ❌ | 父文件夹ID（支持嵌套） |

**响应**:
```json
{
  "id": "folder-uuid-...",
  "user_id": "default",
  "name": "NLP论文",
  "parent_id": null,
  "created_at": "2026-02-16T06:30:00.000000",
  "document_count": 0
}
```

---

### 4.2 获取文件夹列表

### `GET /api/v1/documents/folders/list`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string (query) | ❌ | 默认 "default" |

**响应**:
```json
{
  "folders": [
    {
      "id": "folder-uuid-...",
      "user_id": "default",
      "name": "NLP论文",
      "parent_id": null,
      "created_at": "2026-02-16T06:30:00.000000",
      "document_count": 5
    }
  ]
}
```

> **document_count**: 该文件夹下的文档数量（实时计算）
>
> **排序**: 按 `created_at` 升序

---

### 4.3 删除文件夹

### `DELETE /api/v1/documents/folders/{folder_id}`

> 删除文件夹后，其下文档的 `folder_id` 被置为 `null`（文档不会被删除）。

**响应**:
```json
{ "status": "ok" }
```

---

## 5. 用户中心

### 5.1 获取用户资料

### `GET /api/v1/users/profile`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string (query) | ❌ | 默认 "default" |

> 若用户不存在，自动创建默认资料。

**响应**:
```json
{
  "user_id": "default",
  "display_name": "User_default",
  "avatar_url": "",
  "research_field": "",
  "knowledge_level": "intermediate",
  "institution": "",
  "bio": "",
  "model_mode": "free",
  "balance": 0.0,
  "created_at": "2026-02-16T06:30:00.000000",
  "updated_at": "2026-02-16T06:30:00.000000"
}
```

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | string | 用户唯一标识 |
| display_name | string | 显示名称 |
| avatar_url | string | 头像URL（预留） |
| research_field | string | 研究方向 |
| knowledge_level | string | "beginner" \| "intermediate" \| "advanced" |
| institution | string | 所属机构 |
| bio | string | 个人简介 |
| model_mode | string | "free" \| "paid" |
| balance | float | 账户余额（元） |
| created_at | string | 创建时间 |
| updated_at | string | 最后更新时间 |

---

### 5.2 更新用户资料

### `PUT /api/v1/users/profile`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string (query) | ❌ | 默认 "default" |

**请求体**（所有字段可选，只传需要更新的）:
```json
{
  "display_name": "张三",
  "research_field": "自然语言处理",
  "institution": "清华大学",
  "knowledge_level": "advanced",
  "bio": "研究方向为大语言模型推理",
  "model_mode": "paid"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| display_name | string | 显示名称 |
| avatar_url | string | 头像URL |
| research_field | string | 研究方向 |
| knowledge_level | string | "beginner" \| "intermediate" \| "advanced" |
| institution | string | 所属机构 |
| bio | string | 个人简介 |
| model_mode | string | "free" \| "paid" |

**响应**: 返回更新后的完整用户资料（同 5.1）

---

### 5.3 充值

### `POST /api/v1/users/recharge`

**请求体**:
```json
{
  "user_id": "default",
  "amount": 100.0
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | ❌ | 默认 "default" |
| amount | float | ✅ | 充值金额（元），必须 > 0 |

> 充值后 `model_mode` 自动设为 "paid"，`balance` 累加。

**响应**: 返回更新后的完整用户资料（同 5.1）

---

### 5.4 获取费用统计

### `GET /api/v1/users/usage`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string (query) | ❌ | 默认 "default" |

**响应**:
```json
{
  "user_id": "default",
  "model_mode": "free",
  "balance": 50.0,
  "today": {
    "count": 5,
    "cost": 0.25,
    "free_remaining": 15,
    "free_quota": 20
  },
  "total": {
    "count": 100,
    "cost": 12.50,
    "tokens": 0
  },
  "pricing": {
    "normal": 0.05,
    "agent": 0.20,
    "free_daily_quota": 20
  }
}
```

---

### 5.5 获取用量记录

### `GET /api/v1/users/usage/records`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string (query) | ❌ | 默认 "default" |
| page | int (query) | ❌ | 页码，默认 1 |
| page_size | int (query) | ❌ | 每页条数，默认 20 |

**响应**:
```json
{
  "records": [
    {
      "id": "uuid",
      "user_id": "default",
      "session_id": "session-uuid",
      "mode": "agent",
      "cost": 0.20,
      "token_count": 0,
      "created_at": "2026-02-16T..."
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20
}
```

---

## 6. SSE 事件协议

> 适用于 `POST /api/v1/chat/chat` 接口的流式响应。
>
> 格式: 标准 SSE，每个事件由 `event:` 行和 `data:` 行组成，以 `\n\n` 分隔。

### 6.1 事件类型总览

| event | 触发模式 | 说明 |
|-------|---------|------|
| `plan` | Agent | 推送研究计划（TODO 列表） |
| `step_start` | Both | 某步骤开始执行 |
| `step_progress` | Agent | 步骤执行进度更新 |
| `step_complete` | Both | 某步骤执行完成 |
| `stream` | Both | 流式文本内容片段 |
| `done` | Both | 全部完成 |
| `cost` | Both | 本次对话产生的费用 |

### 6.2 各事件 data 格式

#### `plan` — 推送研究计划

```
event: plan
data: {"plan": [{"id": "s1", "action": "检索学术数据库", "tool": "SearchTool", "status": "pending"}, ...], "timestamp": "..."}
```

| 字段 | 说明 |
|------|------|
| plan[].id | 步骤唯一ID |
| plan[].action | 步骤描述（中文） |
| plan[].tool | 使用的工具名 |
| plan[].status | 初始状态，固定 "pending" |

#### `step_start` — 步骤开始

```
event: step_start
data: {"step_id": "s1", "action": "检索学术数据库", "timestamp": "..."}
```

#### `step_progress` — 步骤进度

```
event: step_progress
data: {"step_id": "s1", "progress": 0.5, "message": "已搜索 50% 的数据源", "timestamp": "..."}
```

| 字段 | 说明 |
|------|------|
| progress | 0.0 ~ 1.0 的浮点数 |
| message | 当前进度的文字说明 |

#### `step_complete` — 步骤完成

```
event: step_complete
data: {"step_id": "s1", "result": {"papers_found": 5, "papers": [...]}, "timestamp": "..."}
```

#### `stream` — 流式文本片段

```
event: stream
data: {"content": "这是一段回答内容的片段...", "timestamp": "..."}
```

> 前端需要将多次 `stream` 事件的 `content` 累加拼接，实时渲染。

#### `done` — 完成

```
event: done
data: {"content": "完整的回答内容...", "timestamp": "..."}
```

> 收到 `done` 后，前端应：
> 1. 将累积内容作为 assistant 消息添加到列表
> 2. 清空流式内容
> 3. 解除 loading 状态

#### `cost` — 本次对话费用

```
event: cost
data: {"cost": 0.20, "balance": 99.80, "model_mode": "paid", "timestamp": "..."}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| cost | float | 本次对话费用（元） |
| balance | float | 账户余额（元） |
| model_mode | string | "free" \| "paid" |
| timestamp | string | 时间戳 |

### 6.3 普通模式事件流示例

```
event: step_start
data: {"step_id":"answer","action":"生成回答","timestamp":"..."}

event: stream
data: {"content":"关于这个","timestamp":"..."}

event: stream
data: {"content":"问题，","timestamp":"..."}

event: stream
data: {"content":"最新的研究表明...","timestamp":"..."}

event: done
data: {"content":"关于这个问题，最新的研究表明...","timestamp":"..."}

event: cost
data: {"cost":0.05,"balance":99.95,"model_mode":"paid","timestamp":"..."}
```

### 6.4 Agent 模式事件流示例

```
event: step_start
data: {"step_id":"plan","action":"分析查询并创建研究计划","timestamp":"..."}

event: plan
data: {"plan":[{"id":"s1","action":"检索学术数据库","tool":"SearchTool","status":"pending"},{"id":"s2","action":"筛选与排序结果","tool":"FilterTool","status":"pending"},{"id":"s3","action":"归纳关键发现","tool":"SummarizeTool","status":"pending"},{"id":"s4","action":"生成引用","tool":"CitationTool","status":"pending"}],"timestamp":"..."}

event: step_start
data: {"step_id":"s1","action":"检索学术数据库","timestamp":"..."}

event: step_progress
data: {"step_id":"s1","progress":0.2,"message":"已搜索 20% 的数据源","timestamp":"..."}

event: step_progress
data: {"step_id":"s1","progress":0.5,"message":"已搜索 50% 的数据源","timestamp":"..."}

event: step_progress
data: {"step_id":"s1","progress":1.0,"message":"已搜索 100% 的数据源","timestamp":"..."}

event: step_complete
data: {"step_id":"s1","result":{"papers_found":5,"papers":[...]},"timestamp":"..."}

event: step_start
data: {"step_id":"s2","action":"筛选与排序结果","timestamp":"..."}

event: step_complete
data: {"step_id":"s2","result":{"filtered_count":4,"papers":[...]},"timestamp":"..."}

event: step_start
data: {"step_id":"s3","action":"归纳关键发现","timestamp":"..."}

event: stream
data: {"content":"## 研究摘要: ","timestamp":"..."}

event: stream
data: {"content":"大语言模型推理\n\n基于","timestamp":"..."}

...（更多 stream 事件）

event: step_complete
data: {"step_id":"s3","result":{"summary_length":1200},"timestamp":"..."}

event: step_start
data: {"step_id":"s4","action":"生成引用","timestamp":"..."}

event: stream
data: {"content":"\n\n---\n**References:**\n[1] Vaswani et al...","timestamp":"..."}

event: step_complete
data: {"step_id":"s4","result":{"citation_count":4},"timestamp":"..."}

event: done
data: {"content":"## 研究摘要: 大语言模型推理\n\n基于...完整内容...","timestamp":"..."}

event: cost
data: {"cost":0.20,"balance":99.80,"model_mode":"paid","timestamp":"..."}
```

---

## 7. 数据结构速查

### 7.1 Session 会话

```json
{
  "id": "uuid",
  "user_id": "string",
  "title": "string (≤53 chars)",
  "mode": "normal | agent",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

### 7.2 Message 消息

```json
{
  "id": "uuid",
  "session_id": "uuid",
  "role": "user | assistant",
  "content": "string",
  "msg_type": "text",
  "metadata": "object | null",
  "created_at": "ISO8601"
}
```

### 7.3 Document 文档

```json
{
  "id": "uuid",
  "user_id": "string",
  "folder_id": "uuid | null",
  "filename": "string (存储文件名)",
  "original_name": "string (原始文件名)",
  "file_size": "int (bytes)",
  "file_type": "pdf | word | markdown | text | other",
  "page_count": "int",
  "status": "uploaded",
  "created_at": "ISO8601"
}
```

### 7.4 Folder 文件夹

```json
{
  "id": "uuid",
  "user_id": "string",
  "name": "string",
  "parent_id": "uuid | null",
  "created_at": "ISO8601",
  "document_count": "int (动态计算)"
}
```

### 7.5 UserProfile 用户资料

```json
{
  "user_id": "string",
  "display_name": "string",
  "avatar_url": "string",
  "research_field": "string",
  "knowledge_level": "beginner | intermediate | advanced",
  "institution": "string",
  "bio": "string",
  "model_mode": "free | paid",
  "balance": "float",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

### 7.6 UsageRecord 用量记录

```json
{
  "id": "uuid",
  "user_id": "string",
  "session_id": "uuid | null",
  "mode": "normal | agent",
  "cost": "float (元)",
  "token_count": "int",
  "created_at": "ISO8601"
}
```

---

## 附录: 错误码

| HTTP 状态码 | 说明 |
|------------|------|
| 200 | 成功 |
| 400 | 请求参数错误（空文件、文件过大等） |
| 402 | 额度不足（免费额度用完或付费余额不足） |
| 404 | 资源不存在（文档/会话未找到） |
| 422 | 请求体格式错误（JSON 解析失败等） |
| 500 | 服务器内部错误 |

错误响应格式:
```json
{
  "detail": "错误描述信息"
}
```
