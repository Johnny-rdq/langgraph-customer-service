"""
Pydantic 数据模型模块
定义 API 请求与响应的数据格式，提供自动校验和序列化
"""
from pydantic import BaseModel, Field  # Pydantic 数据校验库
from typing import Optional  # 可选类型标注
from datetime import datetime  # 时间戳类型


# ── 请求模型 ──

class ChatRequest(BaseModel):
    """前端发送的对话请求体"""
    user_id: str = Field(..., description="用户唯一标识，用于区分不同会话")
    message: str = Field(
        ...,  # ... 表示必填
        min_length=1,  # 消息最少 1 个字符
        max_length=5000,  # 消息最大 5000 字符
        description="用户发送的消息内容",
    )
    session_id: Optional[str] = Field(
        default=None,  # 首次对话可不传，后端自动生成
        description="会话 ID，用于维持多轮对话上下文",
    )


# ── 响应模型 ──

class ChatResponse(BaseModel):
    """后端返回的对话响应体"""
    session_id: str = Field(..., description="当前会话唯一 ID")
    reply: str = Field(..., description="客服 Agent 生成的回复内容")
    intent: str = Field(default="general", description="识别到的用户意图")
    requires_human: bool = Field(
        default=False,  # 默认不需要转人工
        description="是否需要转人工客服处理",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,  # 自动填充当前时间
        description="回复生成时间",
    )


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(default="ok", description="服务状态")
    model: str = Field(default="qwen-turbo", description="当前使用的模型")
