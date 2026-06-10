from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class ChatSession(SQLModel, table=True):
    """侧边栏会话列表的数据表"""
    id: str = Field(primary_key=True)            # 会话 ID (同 LangGraph 的 session_id)
    title: str = Field(default="新对话")          # 会话标题
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)