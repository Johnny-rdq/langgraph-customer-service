from sqlmodel import SQLModel, Field, Relationship  # SQLModel ORM 基类、字段和关联
from datetime import datetime  # 时间戳
from typing import Optional, List  # 可选类型和列表类型
import uuid  # 唯一 ID 生成


class ChatMessage(SQLModel, table=True):
    """聊天消息数据表 —— 每条用户/AI 消息有一条记录"""
    __tablename__ = "chat_messages"  # 数据库表名

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),  # 自动生成唯一消息 ID
        primary_key=True,  # 主键
    )
    session_id: str = Field(
        foreign_key="chatsession.id",  # 关联到会话表
        index=True,  # 建立索引，按会话查询快
    )
    role: str = Field()  # 消息角色: "user" 或 "assistant"
    content: str = Field()  # 消息文本内容
    created_at: datetime = Field(default_factory=datetime.utcnow)  # 消息创建时间


class ChatSession(SQLModel, table=True):
    """侧边栏会话列表的数据表"""
    id: str = Field(primary_key=True)  # 会话 ID (同 LangGraph 的 session_id)
    title: str = Field(default="新对话")  # 会话标题
    created_at: datetime = Field(default_factory=datetime.utcnow)  # 创建时间
    updated_at: datetime = Field(default_factory=datetime.utcnow)  # 最后更新时间

    # ── 关联关系：一个会话下有多条消息 ──
    messages: List[ChatMessage] = Relationship(
        back_populates=None,  # 单向关联，消息表不反向引用
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",  # 删除会话时级联删除所有消息
            "order_by": "ChatMessage.created_at",  # 按时间排序
        },
    )