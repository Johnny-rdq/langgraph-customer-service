"""
FastAPI 应用启动入口
PyCharm 中直接运行此文件即可启动后端 + 前端 + 自动打开浏览器
"""
import sys                                       # 系统模块

# ── Windows 下强制 stdout 使用 UTF-8 编码，解决 GBK 无法编码 emoji 等 Unicode 字符的问题 ──
# 必须在所有输出之前执行，否则 print() 含 emoji 会抛出 UnicodeEncodeError
if sys.stdout.encoding.upper() != "UTF-8":       # 仅在非 UTF-8 时才重配置（如 Windows GBK）
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 重设编码 + 无法编码的字符用 ? 替换
    except Exception:                            # 部分环境（如管道重定向）不支持 reconfigure
        pass                                     # 静默忽略，后续用 logger 替代 print 来兜底

import subprocess                                # 子进程管理，用于启动前端服务
# import webbrowser                                # 自动打开浏览器
import threading                                 # 多线程，后台读取前端日志
import time                                      # 延时等待
from pathlib import Path                         # 路径处理
# 1. 在顶部导入这些
from contextlib import asynccontextmanager
from app.core.db import create_db_and_tables
from app.api.session import router as session_router



# ── 将项目根目录加入 sys.path ──
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import logging                                   # 日志模块
import os                                        # 文件系统操作
from contextlib import asynccontextmanager       # FastAPI 生命周期管理
from fastapi import FastAPI                       # FastAPI 框架
from fastapi.middleware.cors import CORSMiddleware # CORS 中间件
from app.api.chat import router as chat_router   # 对话路由
from app.core.config import get_settings         # 全局配置

# ── 配置日志 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── 全局变量：持有前端子进程引用 ──
_frontend_process = None  # npm run dev 子进程


def _start_frontend():
    """启动前端 Vite 开发服务器（后台子进程）

    在 Python 线程中运行，避免阻塞 FastAPI 启动。
    启动成功后自动打开浏览器。
    """
    global _frontend_process
    frontend_dir = _project_root / "frontend"       # 前端项目目录

    # 检查目录是否存在
    if not frontend_dir.exists():
        logger.warning("[WARN]  前端目录不存在，跳过启动前端: %s", frontend_dir)
        return

    # 检查 node_modules 是否已安装
    if not (frontend_dir / "node_modules").exists():
        logger.warning("[WARN]  前端依赖未安装，请先执行: cd frontend && npm install")
        return

    logger.info("[FRONTEND] 正在启动前端开发服务器...")

    # 启动 npm run dev（shell=True 确保找到 npm 命令）
    _frontend_process = subprocess.Popen(
        "npm run dev",                              # 通过 shell 执行，Windows 下兼容 PATH
        cwd=str(frontend_dir),                      # 工作目录设为 frontend/
        stdout=subprocess.PIPE,                     # 捕获标准输出
        stderr=subprocess.STDOUT,                   # 合并错误输出
        text=True,                                  # 文本模式
        shell=True,                                 # Windows 下通过 shell 启动，解决 PATH 问题
        encoding="utf-8",
        errors="replace",                           # 忽略编码错误
    )

    # ── 后台线程读取前端输出，检测启动完成 ──
    def _monitor():
        frontend_ready = False
        for line in _frontend_process.stdout:
            line = line.strip()
            if line:
                try:
                    print(f"  [前端] {line}")           # 输出到终端（兼容编码）
                except UnicodeEncodeError:
                    print(f"  [前端] (utf-8 output)")   # 编码失败只打印标记
            # 检测启动成功标志
            if "Local:" in line or "localhost" in line:
                frontend_ready = True

        # 进程结束后的处理
        if _frontend_process and _frontend_process.poll() is not None:
            logger.info("[FRONTEND] 前端开发服务器已停止")

    monitor_thread = threading.Thread(target=_monitor, daemon=True)
    monitor_thread.start()

    # ── 等待前端启动就绪（最多等 30 秒）──
    for _ in range(30):
        time.sleep(1)
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:3000", timeout=1)
            break                                    # 能连上就说明就绪
        except Exception:
            continue

    # ── 自动打开浏览器 ──
    logger.info("[NET] 正在打开浏览器...")
    # webbrowser.open("http://localhost:3000")
    logger.info("[OK] 前端已就绪: http://localhost:3000")


def _stop_frontend():
    """停止前端开发服务器"""
    global _frontend_process
    if _frontend_process and _frontend_process.poll() is None:
        logger.info("[FRONTEND] 正在关闭前端开发服务器...")
        _frontend_process.terminate()                # 发送终止信号
        try:
            _frontend_process.wait(timeout=5)        # 等 5 秒退出
        except subprocess.TimeoutExpired:
            _frontend_process.kill()                 # 强制杀进程
        logger.info("[FRONTEND] 前端开发服务器已关闭")


# ── FastAPI 生命周期 ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时拉起前端，关闭时停掉前端"""
    create_db_and_tables()
    settings = get_settings()
    logger.info(f"[START] {settings.APP_NAME} 正在启动...")
    logger.info(f"[MODEL] 模型: {settings.LLM_MODEL}")

    # ── 启动前端服务（在独立线程中，不阻塞 API 启动）──
    frontend_thread = threading.Thread(target=_start_frontend, daemon=True)
    frontend_thread.start()

    logger.info(f"[NET] 后端 API: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")
    yield                                              # 应用运行中
    # ── 关闭清理 ──
    _stop_frontend()
    logger.info("[HELLO] 服务已关闭")


# ── 创建 FastAPI 应用 ──
settings = get_settings()
app = FastAPI(
    title="LangGraph 智能客服系统",
    description="基于 LangGraph + 阿里云百炼的智能客服系统",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS 跨域 ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ──
app.include_router(chat_router)
app.include_router(session_router)


# ── 根路由 ──
@app.get("/")
async def root():
    """根路由"""
    return {
        "service": "LangGraph 智能客服系统",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


# ── 直接运行入口 ──
if __name__ == "__main__":
    import uvicorn

    # 关闭 uvicorn 自带 reload（前端热更新已独立处理）
    use_reload = settings.DEBUG and "--no-reload" not in sys.argv

    print("=" * 50)
    print("  LangGraph 智能客服系统")
    print("=" * 50)
    print()
    print("  启动后将自动:")
    print("    1. 启动后端 API  → http://localhost:8000")
    print("    2. 启动前端页面 → http://localhost:3000")
    print("    3. 打开浏览器")
    print()
    print("  关闭此窗口即可停止所有服务")
    print("=" * 50)
    print()

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=use_reload,
        log_level="info",
    )
