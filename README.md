# LangGraph 智能客服系统 🎧

基于 **LangGraph + 阿里云百炼 (DashScope)** 构建的智能客服系统，支持意图识别、知识库检索、自动回复与转人工等完整客服工作流。

## 🏗️ 项目架构

```
langgraph-customer-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 启动入口
│   ├── core/                   # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py           # 环境变量与全局配置
│   │   └── llm.py              # LLM 实例化 (阿里云百炼)
│   ├── api/                    # FastAPI 路由
│   │   ├── __init__.py
│   │   └── chat.py             # 对话接口
│   ├── agent/                  # LangGraph 核心逻辑
│   │   ├── __init__.py
│   │   ├── state.py            # 图状态定义
│   │   ├── nodes.py            # 节点任务定义
│   │   ├── edges.py            # 条件边/路由逻辑
│   │   └── graph.py            # 图组装与编译
│   ├── tools/                  # 外部工具
│   │   ├── __init__.py
│   │   └── retriever.py        # RAG 知识库检索
│   └── models/                 # Pydantic 数据模型
│       ├── __init__.py
│       └── schemas.py          # API 请求/响应模型
├── data/                       # 本地数据
│   └── knowledge_base.txt      # 客服业务知识库
├── .env.example                # 环境变量示例
├── requirements.txt            # 项目依赖
└── README.md                   # 项目说明
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
    ┌────┼────┬──────────┐
    ▼    ▼    ▼          ▼
  human complaint  inquiry  general
    │    │       │          │
    │    └───┬───┘          │
    │        ▼              │
    │  ┌──────────────┐     │
    │  │ 知识库检索   │     │
    │  │(retrieve)    │     │
    │  └──────┬───────┘     │
    │         │              │
    │    ┌────┼────┐        │
    │    ▼    ▼    ▼        │
    │  有匹配 无匹配(投诉)   │
    │    │    │              │
    │    ▼    ▼              ▼
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

## 🚀 快速开始

### 1. 克隆项目

```bash
cd langgraph-customer-service
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env，填入你的百炼 API Key
# DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx
```

### 4. 启动服务

```bash
# 方式一: 直接运行
python app/main.py

# 方式二: 使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 访问接口

- **API 文档 (Swagger UI)**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/v1/health
- **对话接口**: `POST http://localhost:8000/api/v1/chat`

## 📡 API 接口

### 对话接口

**POST** `/api/v1/chat`

```json
{
  "user_id": "user_001",
  "message": "我想退货，应该怎么操作？",
  "session_id": "optional-session-id"
}
```

响应:

```json
{
  "session_id": "abc123...",
  "reply": "您好！本店支持7天无理由退货...",
  "intent": "inquiry",
  "requires_human": false,
  "timestamp": "2025-01-01T12:00:00"
}
```

### 健康检查

**GET** `/api/v1/health`

```json
{
  "status": "healthy",
  "model": "qwen-plus",
  "service": "langgraph-customer-service"
}
```

## 🛠️ 技术栈

| 组件 | 技术选型 |
|------|----------|
| Web 框架 | FastAPI |
| AI 编排 | LangGraph |
| 大模型 | 阿里云百炼 (qwen-plus) |
| 知识检索 | TF-IDF + 余弦相似度 (scikit-learn) |
| 中文分词 | jieba |
| 数据校验 | Pydantic v2 |

## 📝 扩展方向

- [ ] 接入向量数据库 (ChromaDB / Milvus) 提升检索精度
- [ ] 增加多轮对话记忆管理 (checkpoint)
- [ ] 添加流式响应 (SSE / WebSocket)
- [ ] 支持多语言 (中/英)
- [ ] 接入工单系统，实现真实转人工流程
- [ ] 添加对话质量评估节点
- [ ] 支持意图的多标签分类
