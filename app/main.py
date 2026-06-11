"""
FastAPI 应用启动入口
最纯净版本
"""
import sys
import threading
import time
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_frontend_process = None

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

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    # 强制将端口锁死为 8888，无视配置文件
    frontend_url = "http://localhost:3000"  # 前端页面地址
    backend_url = "http://localhost:8888"  # 后端 API 地址
    print("=" * 50)  # 分隔线
    print("  🤖 LangGraph 智能客服系统")  # 标题
    print("=" * 50)  # 分隔线
    print(f"  🌐 前端页面: {frontend_url}")  # 前端链接（PyCharm 可点击跳转）
    print(f"  📡 API 文档: {backend_url}/docs")  # Swagger 文档链接
    print("=" * 50)  # 分隔线
    uvicorn.run("app.main:app", host="0.0.0.0", port=8888, reload=False)