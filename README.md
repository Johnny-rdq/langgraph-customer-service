# LangGraph 智能客服系统 🤖

基于 **LangGraph + 阿里云百炼 (DashScope) + ChromaDB** 构建的智能客服系统，支持意图识别、向量语义检索、物流查询、会话管理、SSE 流式对话，以及一键转人工等完整客服工作流。

## 🏗️ 项目架构

```
langgraph-customer-service/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 启动入口（自动启动前后端）
│   ├── core/                    # 核心配置与基础设施
│   │   ├── __init__.py
│   │   ├── config.py            # 环境变量与全局配置 (pydantic-settings)
│   │   ├── db.py                # SQLite 数据库连接与引擎
│   │   └── llm.py               # 阿里云百炼 LLM 实例化
│   ├── api/                     # FastAPI 路由层
│   │   ├── __init__.py
│   │   ├── chat.py              # 对话接口（普通 + SSE 流式）
│   │   └── session.py           # 会话管理 CRUD 接口
│   ├── agent/                   # LangGraph 工作流核心
│   │   ├── __init__.py
│   │   ├── state.py             # 图状态定义
│   │   ├── nodes.py             # 5 个处理节点（意图/检索/生成/转人工/闲聊）
│   │   ├── edges.py             # 条件路由逻辑
│   │   └── graph.py             # 图组装、编译与 SqliteSaver 记忆
│   ├── tools/                   # 外部工具集成
│   │   ├── __init__.py
│   │   ├── retriever.py         # ChromaDB 向量语义检索
│   │   └── logistics.py         # 物流查询工具（正则 + LLM 双策略）
│   └── models/                  # 数据模型
│       ├── __init__.py
│       ├── schemas.py           # Pydantic 请求/响应模型
│       └── db_models.py         # SQLModel 数据库表模型
├── frontend/
│   ├── src/
│   │   ├── components/          # React 组件 (Sidebar/ChatArea/ChatInput/WelcomeScreen)
│   │   └── hooks/               # 自定义 Hooks (useChat)
│   ├── package.json             # 前端依赖 (React 18 + Vite + TailwindCSS)
│   ├── vite.config.js           # Vite 构建配置（含 API 代理）
│   └── Dockerfile               # 前端独立 Docker 构建
├── data/
│   └── knowledge_base.txt       # 客服知识库（纯文本）
├── storage/                     # 运行时数据（不提交 Git，Docker 挂载）
│   ├── chat_database.db         # SQLite 会话数据库
│   └── chroma_db/               # ChromaDB 向量持久化
├── Dockerfile                   # 后端 Docker 构建
├── docker-compose.yml           # 一键编排后端+前端
├── .dockerignore                # Docker 构建排除
├── .env.example                 # 环境变量模板
├── requirements.txt             # Python 依赖
├── start.bat                    # Windows 一键启动脚本
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
| **Web 框架** | FastAPI | 高性能异步 Web 框架 |
| **AI 编排** | LangGraph | 状态图工作流引擎 |
| **大模型** | 阿里云百炼 DashScope | qwen-turbo / qwen-plus / qwen-max |
| **向量检索** | ChromaDB + text-embedding-v2 | 语义级知识库检索 |
| **中文分词** | jieba + TF-IDF | 传统检索兜底方案 |
| **记忆管理** | LangGraph SqliteSaver | 多轮对话上下文持久化 |
| **数据库** | SQLModel + SQLite | 会话记录存储 |
| **数据校验** | Pydantic v2 | 请求/响应自动校验 |
| **前端框架** | React 18 + Vite | 现代化前端构建 |
| **UI 样式** | TailwindCSS 3 | 原子化 CSS 框架 |
| **图标** | Lucide React | 轻量图标库 |
| **容器化** | Docker + docker-compose | 一键部署 |

## 🚀 快速开始

### 方式一：本地开发运行

#### 1. 环境准备

- **Python** >= 3.10
- **Node.js** >= 18（前端构建需要）

#### 2. 克隆项目

```bash
git clone https://github.com/Johnny-rdq/langgraph-customer-service.git
cd langgraph-customer-service
```

#### 3. 安装依赖

```bash
# Python 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend && npm install && cd ..
```

#### 4. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env，填入你的百炼 API Key
# DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx
```

#### 5. 启动服务

```bash
# 方式一：一键启动（自动启动后端 + 前端）
python app/main.py

# 方式二：分别启动
# 终端 1 - 后端
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# 终端 2 - 前端
cd frontend && npm run dev

# 方式三：Windows 一键启动
start.bat
```

#### 6. 访问服务

| 地址 | 说明 |
|------|------|
| http://localhost:3000 | 前端聊天界面 |
| http://localhost:8000/docs | API 文档 (Swagger UI) |
| http://localhost:8000/api/v1/health | 健康检查 |

### 方式二：Docker 部署 🐳

```bash
# 1. 确保已安装 Docker 和 docker-compose

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY

# 3. 一键启动（后端 + 前端）
docker-compose up -d

# 4. 查看日志
docker-compose logs -f

# 5. 停止服务
docker-compose down
```

部署后访问：
- **前端页面**：http://localhost:3000
- **API 文档**：http://localhost:8000/docs

## 📡 API 接口

### 对话接口

**POST** `/api/v1/chat` — 普通对话（一次性返回）

```json
// 请求
{
  "user_id": "user_001",
  "message": "我想退货，应该怎么操作？",
  "session_id": "optional-session-id"
}

// 响应
{
  "session_id": "abc123...",
  "reply": "您好！本店支持7天无理由退货...",
  "intent": "inquiry",
  "requires_human": false,
  "timestamp": "2025-01-01T12:00:00"
}
```

**POST** `/api/v1/chat/stream` — 流式对话（SSE 逐字返回）

```javascript
// 前端通过 EventSource 或 fetch 接收 SSE 事件流
// 事件类型: intent → retrieval → token (×N) → done
const eventSource = new EventSource('/api/v1/chat/stream');
eventSource.onmessage = (e) => {
  const { type, content } = JSON.parse(e.data);
  // type: "intent" | "retrieval" | "token" | "done" | "error"
};
```

### 会话管理

**GET** `/api/v1/sessions/` — 获取所有历史会话（按更新时间倒序）

**POST** `/api/v1/sessions/` — 创建新会话

```json
// 响应
{
  "id": "uuid-xxx",
  "title": "新对话",
  "created_at": "2025-01-01T12:00:00",
  "updated_at": "2025-01-01T12:00:00"
}
```

**DELETE** `/api/v1/sessions/{session_id}` — 删除指定会话

### 健康检查

**GET** `/api/v1/health`

```json
{
  "status": "healthy",
  "model": "qwen-turbo",
  "service": "langgraph-customer-service"
}
```

## ⚙️ 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key（**必填**） | — |
| `LLM_MODEL` | 模型选择 | `qwen-turbo` |
| `LLM_TEMPERATURE` | 回复随机性 (0~1) | `0.7` |
| `LLM_MAX_TOKENS` | 最大输出 Token | `2048` |
| `APP_HOST` | 服务绑定地址 | `0.0.0.0` |
| `APP_PORT` | 服务端口 | `8000` |
| `DEBUG` | 调试模式 | `true` |
| `KNOWLEDGE_BASE_PATH` | 知识库文件路径 | `data/knowledge_base.txt` |

> 模型可选：`qwen-turbo`（速度快）、`qwen-plus`（推荐）、`qwen-max`（效果最佳）

## 🎯 核心功能

### 5 种意图识别
通过 LLM 自动分析用户消息，识别为以下意图之一：
- **complaint** — 用户投诉 → 检索知识库 → 生成安抚回复 → 必要时转人工
- **inquiry** — 业务咨询 → ChromaDB 语义检索 → 基于知识库回复
- **logistics** — 物流查询 → 正则提取订单号 + LLM 兜底 → 模拟物流数据
- **general** — 闲聊问候 → 直接友好回复
- **human** — 明确要求转人工 → 生成过渡话术

### 向量语义检索
- 使用阿里云 `text-embedding-v2` 模型将知识库向量化
- 基于 ChromaDB 进行高维语义相似度检索
- 首次启动自动将 `data/knowledge_base.txt` 灌入向量库

### 多轮对话记忆
- 基于 LangGraph SqliteSaver 持久化对话历史
- 每次对话自动注入最近 10 轮上下文
- 刷新页面后仍可继续之前的对话

### SSE 流式响应
- 逐步返回生成的 Token，提升用户体验
- 事件类型区分：意图识别结果 → 检索状态 → 逐字回复 → 完成

## 📝 扩展方向

- [ ] 接入向量数据库向量维度升级 (Milvus / Weaviate)
- [ ] 增加多轮对话记忆管理可视化面板
- [ ] 支持语音输入与语音播报 (ASR + TTS)
- [ ] 接入真实物流 API 替代模拟数据
- [ ] 支持多语言 (中/英)
- [ ] 接入工单系统，实现真实转人工流程
- [ ] 添加对话质量自动评估节点
- [ ] 支持意图的多标签分类
- [ ] 生产环境 Nginx 反向代理 + HTTPS

## 📄 License

MIT License
