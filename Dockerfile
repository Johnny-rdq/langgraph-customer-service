# ================================================
# LangGraph 智能客服系统 — Dockerfile (后端)
# 基于 Python 3.11 构建 FastAPI 后端服务
# ================================================
FROM python:3.11-slim  # 使用轻量 Python 3.11 镜像

# ── 设置工作目录 ──
WORKDIR /app  # 所有后续操作在 /app 目录下执行

# ── 安装系统依赖 ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \                   # C 编译器，scikit-learn 需要
    g++ \                   # C++ 编译器
    && rm -rf /var/lib/apt/lists/*  # 清理 apt 缓存，减小镜像体积

# ── 安装 Python 依赖 ──
COPY requirements.txt .  # 只复制依赖文件（利用 Docker 缓存层）
RUN pip install --no-cache-dir -r requirements.txt  # 安装所有 Python 依赖

# ── 复制应用代码 ──
COPY app/ ./app/          # FastAPI 应用代码
COPY data/ ./data/        # 知识库等数据文件

# ── 创建数据存储目录 ──
RUN mkdir -p /app/storage  # SQLite 和 ChromaDB 数据目录

# ── 暴露端口 ──
EXPOSE 8888  # FastAPI 服务端口

# ── 启动命令 ──
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888"]  # 启动 FastAPI
