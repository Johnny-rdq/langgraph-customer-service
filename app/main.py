"""
FastAPI 应用启动入口
最纯净版本
"""
import sys
import threading
import subprocess
from pathlib import Path
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.core.config import get_settings
from app.api.chat import router as chat_router
from app.api.session import router as session_router
from app.core.db import create_db_and_tables
from app.api.ws import router as ws_router
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from fastapi import HTTPException
from fastapi import Request
from app.agent.state import current_session_id


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
# 关掉 uvicorn 的请求日志（每 2 秒轮询会刷屏）
logging.getLogger("uvicorn.access").disabled = True

_frontend_process = None

# 定义前端传过来的消息格式
class MessageRequest(BaseModel):
    role: str
    content: str

def _start_frontend():
    global _frontend_process
    frontend_dir = _project_root / "frontend"
    if not frontend_dir.exists() or not (frontend_dir / "node_modules").exists():
        return
    logger.info("启动前端...")
    _frontend_process = subprocess.Popen(
        "npm run dev", cwd=str(frontend_dir), shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore"
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    threading.Thread(target=_start_frontend, daemon=True).start()
    yield
    if _frontend_process:
        _frontend_process.terminate()

app = FastAPI(title="LangGraph 客服系统", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(chat_router)
app.include_router(session_router)

# 在注册 chat.py 路由的地方附近加上：
app.include_router(ws_router)


# 强行接管发消息的接口
@app.post("/api/v1/sessions/{session_id}/messages")
async def chat_with_agent(session_id: str, request: MessageRequest):
    # 如果是客服发的消息，直接忽略不走图（因为直接存数据库了）
    if request.role != "user":
        return {"status": "ok"}

    from app.agent.graph import build_graph

    try:
        # 1. 获取编译好的图
        compiled_graph = build_graph()

        # 2. 🌟 核心：强行把网址里的 session_id 绑进线程配置！
        config = {"configurable": {"thread_id": session_id}}

        # 3. 带着 config 运行图
        response = compiled_graph.invoke(
            {
                "messages": [HumanMessage(content=request.content)],
                "session_id": session_id
            },
            config=config
        )

        # 4. 提取 AI 的最后一条回复
        last_message = response["messages"][-1]
        content = last_message.content if hasattr(last_message, 'content') else last_message.get('content', '')

        return {"role": "assistant", "content": content}

    except Exception as e:
        import logging
        logging.error(f"图运行报错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 🌟 安检站：强行拦截所有请求，抠出网址里的 ID 存入保险箱
@app.middleware("http")
async def intercept_session_id(request: Request, call_next):
    if "/sessions/" in request.url.path:
        parts = request.url.path.split("/")
        try:
            # 例如网址是 /api/v1/sessions/a08eeeeb.../messages
            idx = parts.index("sessions")
            # 把抠出来的 ID 塞进刚才定义的保险箱里
            current_session_id.set(parts[idx + 1])
        except Exception:
            pass
    return await call_next(request)

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    frontend_url = "http://localhost:3000"
    admin_url = "http://localhost:3000/admin"
    backend_url = "http://localhost:8888"
    print("=" * 55)
    print("  🤖 LangGraph 智能客服系统")
    print("=" * 55)
    print(f"  🌐 用户端: {frontend_url}")
    print(f"  🛠️  管理端: {admin_url}")
    print(f"  📡 API 文档: {backend_url}/docs")
    print("=" * 55)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8888, reload=False)