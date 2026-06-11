"""DP Pydantic 数据模型模块
DP 定义 API 请求与响应的数据格式，提供自动校验和序列化。
DP 包含 ChatRequest / ChatResponse / SaveMessageRequest / HealthResponse。
"""
from pydantic import BaseModel, Field  # DP Pydantic 数据校验库
from typing import Optional  # DP 可选类型标注
from datetime import datetime  # DP 时间戳类型


# DP ── 请求模型 ──

class ChatRequest(BaseModel):
    """DP 前端发送的对话请求体"""
    user_id: str = Field(..., description="DP 用户唯一标识，用于区分不同会话")
    message: str = Field(
        ...,  # DP ... 表示必填
        min_length=1,  # DP 消息最少 1 个字符
        max_length=5000,  # DP 消息最大 5000 字符
        description="DP 用户发送的消息内容",
    )
    session_id: Optional[str] = Field(
        default=None,  # DP 首次对话可不传，后端自动生成
        description="DP 会话 ID，用于维持多轮对话上下文",
    )


# DP ── 响应模型 ──

class ChatResponse(BaseModel):
    """DP 后端返回的对话响应体"""
    session_id: str = Field(..., description="DP 当前会话唯一 ID")
    reply: str = Field(..., description="DP 客服 Agent 生成的回复内容")
    intent: str = Field(default="general", description="DP 识别到的用户意图")
    requires_human: bool = Field(
        default=False,  # DP 默认不需要转人工
        description="DP 是否需要转人工客服处理",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,  # DP 自动填充当前时间
        description="DP 回复生成时间",
    )


class SaveMessageRequest(BaseModel):
    """DP 保存消息的请求体 —— 前端调用消息保存接口时使用"""
    role: str = Field(
        ...,  # DP 必填
        pattern="^(user|assistant)$",  # DP 正则校验，只允许 user 或 assistant
        description="DP 消息角色",
    )
    content: str = Field(
        ...,  # DP 必填
        min_length=1,  # DP 内容至少 1 个字符
        max_length=10000,  # DP 内容最多 10000 字符
        description="DP 消息文本内容",
    )


class HealthResponse(BaseModel):
    """DP 健康检查响应模型"""
    status: str = Field(default="ok", description="DP 服务状态")
    model: str = Field(default="qwen-turbo", description="DP 当前使用的模型")