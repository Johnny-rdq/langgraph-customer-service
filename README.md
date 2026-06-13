# LangGraph 智能客服系统 🤖

基于 **LangGraph + 阿里云百炼 (DashScope) + ChromaDB** 构建的智能客服系统，支持意图识别、向量语义检索、物流查询、SSE 流式对话、转人工 + 管理员实时接管等完整客服工作流。

## 🏗️ 项目架构

```
langgraph-customer-service/
├── app/
│   ├── main.py                  # FastAPI 启动入口（自动启动前后端 + 日志/URL 打印）
│   ├── core/                    # 核心基础设施
│   │   ├── config.py            # 环境变量与全局配置 (pydantic-settings)
│   │   ├── db.py                # SQLite 数据库连接
│   │   └── llm.py               # 阿里云百炼 LLM 实例化
│   ├── api/                     # FastAPI 路由层
│   │   ├── chat.py              # SSE 流式对话 + 转人工拦截 + WebSocket 通知
│   │   ├── session.py           # 会话 CRUD + 消息持久化
│   │   └── ws.py                # WebSocket 管理（用户推送 + 管理员实时监听）
│   ├── agent/                   # LangGraph 工作流
│   │   ├── state.py             # 图状态定义 + ContextVar 保险箱
│   │   ├── nodes.py             # 处理节点（意图/检索/生成/转人工/物流/闲聊）
│   │   ├── edges.py             # 条件路由
│   │   └── graph.py             # 图组装 + SqliteSaver 记忆
│   ├── tools/                   # 外部工具
│   │   ├── retriever.py         # ChromaDB 向量语义检索
│   │   └── logistics.py         # 物流查询（正则 + LLM 双策略）
│   └── models/                  # 数据模型
│       ├── schemas.py           # Pydantic 请求/响应模型
│       └── db_models.py         # SQLModel 表（ChatSession + ChatMessage）
├── frontend/
│   ├── src/
│   │   ├── components/          # React 组件 (Sidebar/ChatArea/ChatInput/WelcomeScreen/MessageItem)
│   │   ├── hooks/               # useChat Hook (SSE + WebSocket)
│   │   └── AdminPanel.jsx       # 人工客服工作台（独立路由 /admin）
│   ├── package.json
│   └── vite.config.js           # Vite + API 代理
├── data/knowledge_base.txt      # 客服知识库
├── storage/                     # 运行时数据（不提交 Git）
│   ├── chat_database.db         # SQLite 会话数据库
│   └── chroma_db/               # ChromaDB 向量存储
├── Dockerfile                   # 后端 Docker
├── docker-compose.yml           # 一键编排
├── requirements.txt
└── README.md
```

## 🔄 工作流

```
用户消息
  │
  ▼
┌─────────────────┐
│  意图识别节点    │
│ (classify_intent)│
└────────┬────────┘
         │
    ┌────┼────┬──────────┬─────────┐
    ▼    ▼    ▼          ▼         ▼
  human complaint inquiry logistics general
    │    │       │          │         │
    │    └───┬───┘          │         │
    │        ▼              ▼         │
    │  ┌──────────────┐ ┌───────────┐ │
    │  │ 知识库检索   │ │ 物流查询  │ │
    │  │(ChromaDB)   │ │ (正则+LLM)│ │
    │  └──────┬───────┘ └─────┬─────┘ │
    │         │               │       │
    │    ┌────┼────┐          │       │
    │    ▼    ▼    ▼          │       │
    │  有匹配 无匹配           │       │
    │    │    │               │       │
    │    ▼    ▼               ▼       ▼
    │  ┌──────────────┐ ┌──────────────┐
    │  │ 生成回复节点  │ │ 直接回复节点 │
    │  │(generate)    │ │(direct)      │
    │  └──────┬───────┘ └──────┬───────┘
    │         │                │
    │         ▼                │
    │      有疑虑?             │
    │    ┌────┼────┐          │
    │    ▼    ▼    ▼          │
    │  ┌──────────────┐       │
    └──► 人工客服节点  │◄──────┘
       │(human)       │
       └──────────────┘
              │
              ▼
            END
```

## 🛠️ 技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **Web 框架** | FastAPI | 异步 Web + WebSocket |
| **AI 编排** | LangGraph | 状态图工作流 + SqliteSaver 记忆 |
| **大模型** | 阿里云百炼 DashScope | qwen-turbo / qwen-plus / qwen-max |
| **向量检索** | ChromaDB + text-embedding-v2 | 语义级知识库检索 |
| **数据库** | SQLModel + SQLite | 会话与消息存储 |
| **数据校验** | Pydantic v2 | 请求/响应自动校验 |
| **实时通信** | WebSocket | 管理员面板实时推送 |
| **前端框架** | React 18 + Vite | 现代化前端 SPA |
| **UI 样式** | TailwindCSS 3 | 原子化 CSS |
| **图标** | Lucide React | 轻量图标库 |
| **容器化** | Docker + docker-compose | 一键部署 |

## 🚀 快速开始

### 1. 环境准备

- **Python** >= 3.10
- **Node.js** >= 18

### 2. 克隆项目

```bash
git clone https://github.com/Johnny-rdq/langgraph-customer-service.git
cd langgraph-customer-service
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入百炼 API Key: DASHSCOPE_API_KEY=sk-xxxxxxxx
```

### 5. 启动

```bash
python app/main.py
```

### 6. 访问

| 地址 | 说明 |
|------|------|
| http://localhost:3000 | 用户聊天界面 |
| http://localhost:3000/admin | 人工客服工作台 |
| http://localhost:8888/docs | API 文档 (Swagger) |

### Docker 部署 🐳

```bash
cp .env.example .env  # 编辑填入 DASHSCOPE_API_KEY
docker-compose up -d   # 一键启动前后端
docker-compose down    # 停止
```

## 📡 API 接口

### 对话

**POST** `/api/v1/chat` — 普通对话（一次性返回）

```json
// 请求
{ "user_id": "user_001", "message": "怎么退货？", "session_id": "optional" }

// 响应
{ "session_id": "abc123...", "reply": "您好！本店支持7天无理由退货...", "intent": "inquiry", "requires_human": false }
```

**POST** `/api/v1/chat/stream` — SSE 流式对话（逐字返回）

```
事件类型: intent → retrieval → token (×N) → done
```

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/sessions/` | 获取所有会话（按更新时间倒序） |
| POST | `/api/v1/sessions/` | 创建新会话 |
| GET | `/api/v1/sessions/{id}/messages` | 获取会话消息列表 |
| POST | `/api/v1/sessions/{id}/messages` | 保存消息到会话 |
| DELETE | `/api/v1/sessions/{id}` | 删除会话及其消息 |

### 人工客服

| 方法 | 路径 | 说明 |
|------|------|------|
| WS | `/api/v1/ws/admin/listen` | 管理员 WebSocket（实时接收排队/消息通知） |
| GET | `/api/v1/ws/admin/sessions` | 获取排队中的会话列表 |
| POST | `/api/v1/ws/admin/send` | 管理员发送回复给用户 |
| WS | `/api/v1/ws/{session_id}` | 用户 WebSocket（接收管理员实时回复） |

## ⚙️ 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key（**必填**） | — |
| `LLM_MODEL` | 模型选择 | `qwen-turbo` |
| `LLM_TEMPERATURE` | 回复随机性 (0~1) | `0.7` |
| `LLM_MAX_TOKENS` | 最大输出 Token | `2048` |
| `APP_PORT` | 服务端口 | `8888` |
| `DEBUG` | 调试模式 | `true` |

> 模型可选：`qwen-turbo`（快速）、`qwen-plus`（推荐）、`qwen-max`（最佳效果）

## 🎯 核心功能

- **5 种意图识别**：complaint / inquiry / logistics / general / human
- **向量语义检索**：ChromaDB + text-embedding-v2，首次启动自动灌库
- **多轮对话记忆**：LangGraph SqliteSaver，自动注入最近 10 轮上下文
- **SSE 流式响应**：逐 Token 返回，打字机效果
- **转人工 + 实时接管**：用户转人工 → WebSocket 推送通知 → 管理员面板实时接管
- **管理员工作台**：`/admin` 独立页面，WebSocket 实时监听 + 轮询兜底，查看/回复排队会话

## 📄 License

MIT
