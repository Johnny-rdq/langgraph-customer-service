# LangGraph 智能客服系统 🤖

基于 **LangGraph + DeepSeek + ChromaDB + 阿里云百炼 Embedding** 构建的智能客服系统，支持意图识别、向量语义检索、物流查询、SSE 流式对话、转人工 + 管理员实时接管等完整客服工作流。

## 🏗️ 项目架构

```
langgraph-customer-service/
├── app/
│   ├── main.py                  # FastAPI 启动入口（自动启动前后端 + 日志/URL 打印）
│   ├── core/                    # 核心基础设施
│   │   ├── config.py            # 环境变量与全局配置 (pydantic-settings)
│   │   ├── db.py                # SQLite 数据库连接
│   │   └── llm.py               # LLM 实例化（DeepSeek，OpenAI 兼容协议）
│   ├── api/                     # FastAPI 路由层
│   │   ├── chat.py              # SSE 流式对话 + 转人工/投诉拦截 + WebSocket 通知
│   │   ├── session.py           # 会话 CRUD + 消息持久化
│   │   └── ws.py                # WebSocket 管理（用户推送 + 管理员实时监听）
│   ├── agent/                   # LangGraph 工作流
│   │   ├── state.py             # 图状态定义 + ContextVar 保险箱
│   │   ├── nodes.py             # 处理节点（意图+情绪/检索/生成/转人工/物流/闲聊）
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
┌──────────────────────────┐
│  意图识别节点 + 情绪判断  │
│ (classify_intent)         │
└────────┬─────────────────┘
         │
    ┌────┼────────────┬──────────┬─────────┐
    ▼    ▼            ▼          ▼         ▼
  human complaint   inquiry  logistics  general
    │    │            │          │         │
    └────┘            ▼          ▼         ▼
      │      ┌──────────────┐ ┌───────┐ ┌─────────┐
      │      │ 知识库检索   │ │物流查询│ │直接回复 │
      │      │(ChromaDB)    │ │(正则+ │ │(direct) │
      │      └──────┬───────┘ │ LLM)  │ └────┬────┘
      │             │         └───┬───┘      │
      │        ┌────┼────┐        │          │
      │        ▼    ▼    ▼        │          │
      │      有匹配 无匹配         │          │
      │        │    │             │          │
      │        ▼    ▼             ▼          ▼
      │  ┌──────────────┐       END        END
      │  │ 生成回复节点  │
      │  │(generate)    │
      │  └──────┬───────┘
      │         │
      │         ▼
      │      有疑虑?
      │    ┌────┼────┐
      │    ▼    ▼    ▼
      └──►┌──────────────┐
          │ 人工客服节点  │
          │(human_service)│
          └──────┬───────┘
                 │
                 ▼
               END
```

## 🛠️ 技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **Web 框架** | FastAPI | 异步 Web + WebSocket |
| **AI 编排** | LangGraph | 状态图工作流 + SqliteSaver 记忆 |
| **Chat 模型** | DeepSeek（OpenAI 兼容协议） | deepseek-chat，可切换任意兼容 API |
| **Embedding** | 阿里云百炼 DashScope | text-embedding-v2，向量语义检索 |
| **向量数据库** | ChromaDB | 本地持久化，MD5 自动更新索引 |
| **数据库** | SQLModel + SQLite | 会话与消息存储 |
| **数据校验** | Pydantic v2 | 请求/响应自动校验 |
| **实时通信** | WebSocket | 管理员面板实时推送 |
| **前端框架** | React 18 + Vite | 现代化前端 SPA |
| **UI 样式** | TailwindCSS 3 | 原子化 CSS |
| **图标** | Lucide React | 轻量图标库 |
| **容器化** | Docker + docker-compose | 一键部署 |

## 🚀 快速开始

### 方式一：Docker 部署（推荐 🐳）

> 一键启动前后端，无需手动安装 Python/Node 环境。

**1. 克隆项目**

```bash
git clone https://github.com/Johnny-rdq/langgraph-customer-service.git
cd langgraph-customer-service
```

**2. 配置环境变量**

```bash
cp .env.example .env
# 编辑 .env，必填 DASHSCOPE_API_KEY=sk-xxxxxxxx
# APP_PORT 可自定义后端端口，默认 8001
```

**3. 启动**

```bash
docker-compose up -d --build
```

**4. 访问**

| 地址 | 说明 |
|------|------|
| http://localhost:3000 | 用户聊天界面 |
| http://localhost:3000/admin | 人工客服工作台 |
| http://localhost:8001/docs | API 文档 (Swagger) |

**5. 停止**

```bash
docker-compose down       # 停止容器
docker-compose down -v    # 停止并删除数据卷（清空数据库）
```

### 方式二：本地开发

**1. 环境准备**

- **Python** >= 3.10
- **Node.js** >= 18

**2. 安装依赖**

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

**3. 配置并启动**

```bash
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY，APP_PORT 设为 8888
python app/main.py   # 一键启动前后端
```

**4. 访问**：http://localhost:3000（用户端）/ http://localhost:3000/admin（管理端）/ http://localhost:8888/docs（API）

### 端口说明

| 模式 | 后端端口 | 前端端口 |
|------|----------|----------|
| Docker 部署 | `8001`（由 `.env` 的 `APP_PORT` 控制） | `3000` |
| 本地开发 | `8888`（main.py 默认） | `3000` |

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
| `LLM_API_KEY` | Chat 模型 API Key（**必填**） | — |
| `LLM_BASE_URL` | Chat 模型 API 地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL` | Chat 模型选择 | `deepseek-chat` |
| `LLM_TEMPERATURE` | 回复随机性 (0~1) | `0.7` |
| `LLM_MAX_TOKENS` | 最大输出 Token | `2048` |
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key（**必填**，向量检索用） | — |
| `APP_PORT` | 服务端口 | `8000` |
| `APP_HOST` | 服务绑定地址 | `0.0.0.0` |
| `DEBUG` | 调试模式 | `true` |
| `KNOWLEDGE_BASE_PATH` | 知识库文件路径 | `data/knowledge_base.txt` |

> Chat / Embedding 模型分离：Chat 走 DeepSeek（可通过 `LLM_BASE_URL` 切换到任意 OpenAI 兼容 API），Embedding 走阿里云百炼 text-embedding-v2。

## 🐳 Docker 架构

```
浏览器(localhost) → :3000(Vite Dev Server) → :8001(FastAPI)
                         │                        │
                     cs-frontend ──cs-network── cs-backend
                         │                        │
                    Proxy /api/* →         LangGraph + ChromaDB
                    重写 Location 头          + SQLite
```

- 前端 Vite 代理将 `/api/*` 请求转发到后端容器（通过内部网络 `cs-network`）
- 代理自动重写 307 重定向的 Location 头，避免浏览器 DNS 无法解析 `backend` 容器名
- WebSocket 通过前端代理转发到后端，无需直连后端端口
- 持久化数据挂载在 `./storage/`（SQLite 数据库 + ChromaDB 向量库）

### Docker 常见问题

**Q: 页面卡死 / `ERR_NAME_NOT_RESOLVED` 错误**

> 已被修复（vite 代理重写 Location 头），若仍出现请确保 `.env` 中 `APP_PORT` 与 docker-compose 端口映射一致。

**Q: 前端修改没生效**

```bash
docker-compose up -d --build frontend  # 只重建前端
```

**Q: 清空所有数据重新开始**

```bash
docker-compose down -v
rm -rf storage/
```

## 🎯 核心功能

- **5 种意图识别 + 情绪判断**：complaint / inquiry / logistics / general / human，负面情绪累计 2 次自动转人工（首次容忍）
- **向量语义检索**：ChromaDB + text-embedding-v2，首次启动自动灌库
- **多轮对话记忆**：LangGraph SqliteSaver，自动注入最近 10 轮上下文
- **SSE 流式响应**：逐 Token 返回，打字机效果
- **转人工 + 实时接管**：用户转人工 → WebSocket 推送通知 → 管理员面板实时接管
- **管理员工作台**：`/admin` 独立页面，WebSocket 实时监听 + 轮询兜底，查看/回复排队会话

## 📄 License

MIT
