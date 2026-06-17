# 使用轻量 Node.js 20 Alpine 镜像
FROM node:20-alpine
# 设置工作目录
WORKDIR /app
# 只复制依赖描述文件
COPY package*.json ./
# 按 lock 文件精确安装依赖
RUN npm ci
# 复制所有前端源码
COPY . .
# Vite 开发服务器端口
EXPOSE 3000
# 启动 Vite 开发服务器
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]