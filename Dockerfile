# 基于 Python 3.11 构建 FastAPI 后端服务
FROM python:3.11-slim
# 设置工作目录
WORKDIR /app
# 只复制依赖描述文件
COPY requirements.txt .
# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 复制所有源码
COPY . .
# FastAPI 服务端口
EXPOSE 8000
# 启动 FastAPI 服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]