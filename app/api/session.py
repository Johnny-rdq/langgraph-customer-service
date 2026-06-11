from fastapi import APIRouter, Depends, HTTPException  # FastAPI 路由和异常
from sqlmodel import Session, select  # SQLModel 数据库会话和查询
from app.core.db import get_session  # 数据库依赖注入
from app.models.db_models import ChatSession, ChatMessage  # 数据表模型
from app.models.schemas import SaveMessageRequest  # 保存消息的请求体
from datetime import datetime  # 时间更新
import uuid  # 唯一 ID 生成
import logging  # 日志

logger = logging.getLogger(__name__)  # 模块日志记录器

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])  # 会话管理路由


# ═══════════════════════════════════════════════════════════
# 会话 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/")
def get_all_sessions(db: Session = Depends(get_session)):
    """获取所有历史会话（按最后更新时间倒序排序）"""
    sessions = db.exec(
        select(ChatSession).order_by(ChatSession.updated_at.desc())  # 最新活跃的在前
    ).all()
    # 手动构建 dict，避免触发 messages 关系的懒加载
    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@router.post("/")
def create_session(db: Session = Depends(get_session)):
    """新建一个会话，同时在前端生成初始消息占位"""
    new_session = ChatSession(
        id=str(uuid.uuid4()),  # 生成唯一 sessions ID
        title="新对话",  # 默认标题，后续由第一条用户消息更新
    )
    db.add(new_session)  # 加入数据库
    db.commit()  # 提交事务
    db.refresh(new_session)  # 刷新以获取数据库生成的字段
    return {
        "id": new_session.id,
        "title": new_session.title,
        "created_at": new_session.created_at.isoformat(),
        "updated_at": new_session.updated_at.isoformat(),
    }


@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_session)):
    """删除指定会话及其所有消息（级联删除）"""
    session = db.get(ChatSession, session_id)  # 查找会话
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")  # 会话不存在
    db.delete(session)  # 删除会话（级联删除关联的消息）
    db.commit()  # 提交事务
    return {"status": "ok", "message": f"会话 {session_id} 及其所有消息已删除"}


@router.patch("/{session_id}")
def update_session_title(session_id: str, title: str, db: Session = Depends(get_session)):
    """更新会话标题（前端在第一条消息后自动更新）"""
    session = db.get(ChatSession, session_id)  # 查找会话
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    session.title = title[:100]  # 标题最长 100 字符，防止过长
    session.updated_at = datetime.utcnow()  # 更新最后修改时间
    db.add(session)  # 标记为脏
    db.commit()  # 提交
    db.refresh(session)  # 刷新
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


# ═══════════════════════════════════════════════════════════
# 消息 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/{session_id}/messages")
def get_session_messages(session_id: str, db: Session = Depends(get_session)):
    """获取指定会话的所有消息（按时间正序）"""
    session = db.get(ChatSession, session_id)  # 确认会话存在
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = db.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)  # 按会话 ID 过滤
        .order_by(ChatMessage.created_at)  # 按时间正序排列
    ).all()

    # 转换为前端需要的格式
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ]


@router.post("/{session_id}/messages")
def save_message(
    session_id: str,
    body: SaveMessageRequest,  # JSON 请求体（自动校验）
    db: Session = Depends(get_session),
):
    """保存一条消息到指定会话"""
    # 先确认会话存在
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 创建消息记录
    message = ChatMessage(
        id=str(uuid.uuid4()),  # 生成唯一消息 ID
        session_id=session_id,  # 关联会话
        role=body.role,  # 消息角色（已由 Pydantic 校验）
        content=body.content,  # 消息内容
    )

    # 如果会话标题还是默认的，用第一条用户消息做标题
    if session.title == "新对话" and body.role == "user":
        session.title = body.content[:30] + ("…" if len(body.content) > 30 else "")  # 前 30 字

    # 更新会话最后活跃时间
    session.updated_at = datetime.utcnow()

    db.add(message)  # 加入数据库
    db.add(session)  # 更新会话
    db.commit()  # 提交事务
    db.refresh(message)  # 刷新

    logger.info(
        f"💾 消息已保存: session={session_id[:8]}..., "
        f"role={body.role}, len={len(body.content)}"
    )
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
    }


@router.delete("/{session_id}/messages")
def clear_session_messages(session_id: str, db: Session = Depends(get_session)):
    """清空指定会话的所有消息（保留会话本身）"""
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 直接批量删除
    db.exec(
        select(ChatMessage).where(ChatMessage.session_id == session_id)  # 查到所有消息
    )
    messages = db.exec(
        select(ChatMessage).where(ChatMessage.session_id == session_id)
    ).all()
    for msg in messages:
        db.delete(msg)  # 逐条删除

    session.updated_at = datetime.utcnow()  # 更新时间
    db.commit()
    return {"status": "ok", "message": f"已清空会话 {session_id} 的所有消息"}