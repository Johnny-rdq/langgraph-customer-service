# ================================================
# LangGraph 智能客服系统 — 前端 Dockerfile
# 基于 Node.js 构建 React + Vite 前端开发服务器
# ================================================
FROM node:20-alpine  # 使用轻量 Node.js 20 Alpine 镜像

# ── 设置工作目录 ──
WORKDIR /app  # 所有操作在 /app 目录下

# ── 安装依赖 ──
COPY package*.json ./  # 只复制依赖描述文件（利用 Docker 缓存）
RUN npm ci  # 按 lock 文件精确安装依赖

# ── 复制源码 ──
COPY . .  # 复制所有前端源码

# ── 暴露端口 ──
EXPOSE 3000  # Vite 开发服务器端口

# ── 启动 Vite 开发服务器 ──
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]  # --host 允许外部访问
