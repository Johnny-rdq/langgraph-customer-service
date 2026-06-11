"""DP 会话与消息管理 API 路由
DP 提供会话 CRUD + 消息增删查的 RESTful 接口。
DP 会话删除时级联删除所有关联消息。
DP 消息持久化到 SQLite，支持跨设备/刷新后还原聊天记录。
"""
from fastapi import APIRouter, Depends, HTTPException  # DP FastAPI 路由、依赖注入、HTTP 异常
from sqlmodel import Session, select  # DP SQLModel 数据库会话和查询语句
from app.core.db import get_session  # DP 数据库会话依赖注入函数
from app.models.db_models import ChatSession, ChatMessage  # DP ORM 数据表模型
from app.models.schemas import SaveMessageRequest  # DP 保存消息的 Pydantic 请求体
from datetime import datetime  # DP 时间更新
import uuid  # DP 唯一 ID 生成工具
import logging  # DP 日志模块

logger = logging.getLogger(__name__)  # DP 当前模块的日志记录器

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])  # DP 会话管理路由组


# ═══════════════════════════════════════════════════════════
# DP 会话 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/")
def get_all_sessions(db: Session = Depends(get_session)):
    """DP 获取所有历史会话，按最后更新时间倒序排列"""
    sessions = db.exec(
        select(ChatSession).order_by(ChatSession.updated_at.desc())  # DP 最新活跃的在前
    ).all()
    # DP 手动构建 dict 列表返回，避免触发 messages 关系的懒加载
    return [
        {
            "id": s.id,  # DP 会话 ID
            "title": s.title,  # DP 会话标题
            "created_at": s.created_at.isoformat(),  # DP 创建时间（ISO 格式）
            "updated_at": s.updated_at.isoformat(),  # DP 最后更新时间
        }
        for s in sessions
    ]


@router.post("/")
def create_session(db: Session = Depends(get_session)):
    """DP 新建一个空白会话，返回会话信息给前端"""
    new_session = ChatSession(
        id=str(uuid.uuid4()),  # DP 生成全局唯一会话 ID
        title="新对话",  # DP 默认标题，后续由第一条用户消息自动更新
    )
    db.add(new_session)  # DP 加入数据库待提交
    db.commit()  # DP 提交事务写入数据库
    db.refresh(new_session)  # DP 刷新获取数据库生成的默认值
    return {
        "id": new_session.id,  # DP 返回会话 ID 给前端
        "title": new_session.title,  # DP 返回标题
        "created_at": new_session.created_at.isoformat(),  # DP 返回创建时间
        "updated_at": new_session.updated_at.isoformat(),  # DP 返回更新时间
    }


@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_session)):
    """DP 删除指定会话及其所有消息（级联删除，由 ORM 关系自动处理）"""
    session = db.get(ChatSession, session_id)  # DP 查找会话对象
    if not session:
        raise HTTPException(status_code=404, detail="DP 会话不存在")  # DP 404 返回给前端
    db.delete(session)  # DP 删除会话 → ORM 级联删除关联的所有 ChatMessage
    db.commit()  # DP 提交删除事务
    logger.info(f"DP 会话已删除: {session_id[:8]}...")  # DP 记录日志
    return {"status": "ok", "message": f"DP 会话 {session_id} 及其所有消息已删除"}


@router.patch("/{session_id}")
def update_session_title(session_id: str, title: str, db: Session = Depends(get_session)):
    """DP 更新会话标题，前端在第一条用户消息后自动调用"""
    session = db.get(ChatSession, session_id)  # DP 查找会话
    if not session:
        raise HTTPException(status_code=404, detail="DP 会话不存在")
    session.title = title[:100]  # DP 截断标题，防止超过 100 字符撑爆 UI
    session.updated_at = datetime.utcnow()  # DP 刷新最后活跃时间
    db.add(session)  # DP 标记会话对象为脏
    db.commit()  # DP 提交更新
    db.refresh(session)  # DP 刷新获取最新数据
    return {
        "id": session.id,  # DP 返回更新后的会话 ID
        "title": session.title,  # DP 返回新标题
        "created_at": session.created_at.isoformat(),  # DP 返回创建时间
        "updated_at": session.updated_at.isoformat(),  # DP 返回更新时间
    }


# ═══════════════════════════════════════════════════════════
# DP 消息 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/{session_id}/messages")
def get_session_messages(session_id: str, db: Session = Depends(get_session)):
    """DP 获取指定会话的所有消息，按创建时间正序排列"""
    session = db.get(ChatSession, session_id)  # DP 先确认会话存在
    if not session:
        raise HTTPException(status_code=404, detail="DP 会话不存在")

    messages = db.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)  # DP 按会话 ID 过滤消息
        .order_by(ChatMessage.created_at)  # DP 按创建时间正序（旧→新）
    ).all()

    # DP 转换为前端需要的 JSON 格式
    return [
        {
            "id": msg.id,  # DP 消息唯一 ID
            "role": msg.role,  # DP 消息角色（user/assistant）
            "content": msg.content,  # DP 消息文本内容
            "created_at": msg.created_at.isoformat(),  # DP 消息时间（ISO 格式）
        }
        for msg in messages
    ]


@router.post("/{session_id}/messages")
def save_message(
    session_id: str,
    body: SaveMessageRequest,  # DP JSON 请求体，Pydantic 自动校验
    db: Session = Depends(get_session),
):
    """DP 保存一条消息到指定会话，同时自动更新会话标题和时间"""
    # DP 确认目标会话存在
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="DP 会话不存在")

    # DP 创建消息 ORM 对象
    message = ChatMessage(
        id=str(uuid.uuid4()),  # DP 生成全局唯一消息 ID
        session_id=session_id,  # DP 关联到所属会话
        role=body.role,  # DP 消息角色（已由 SaveMessageRequest 校验正则）
        content=body.content,  # DP 消息文本内容
    )

    # DP 自动更新会话标题：标题还是默认值时，用第一条用户消息的前 30 字
    if session.title == "新对话" and body.role == "user":
        session.title = body.content[:30] + ("…" if len(body.content) > 30 else "")

    # DP 刷新会话最后活跃时间
    session.updated_at = datetime.utcnow()

    db.add(message)  # DP 将消息加入数据库待提交
    db.add(session)  # DP 将更新后的会话也标记为脏
    db.commit()  # DP 一次性提交事务
    db.refresh(message)  # DP 刷新消息对象获取数据库生成的默认值

    logger.info(
        f"DP 💾 消息已保存: session={session_id[:8]}..., "
        f"role={body.role}, len={len(body.content)}"
    )
    return {
        "id": message.id,  # DP 返回消息 ID
        "role": message.role,  # DP 返回消息角色
        "content": message.content,  # DP 返回消息内容
        "created_at": message.created_at.isoformat(),  # DP 返回创建时间
    }


@router.delete("/{session_id}/messages")
def clear_session_messages(session_id: str, db: Session = Depends(get_session)):
    """DP 清空指定会话的所有消息，保留会话本身"""
    session = db.get(ChatSession, session_id)  # DP 查找会话
    if not session:
        raise HTTPException(status_code=404, detail="DP 会话不存在")

    # DP 查询该会话下的所有消息
    messages = db.exec(
        select(ChatMessage).where(ChatMessage.session_id == session_id)
    ).all()
    for msg in messages:
        db.delete(msg)  # DP 逐条删除消息

    session.updated_at = datetime.utcnow()  # DP 刷新会话最后活跃时间
    db.commit()  # DP 提交事务
    logger.info(f"DP 已清空会话 {session_id[:8]}... 的所有消息")
    return {"status": "ok", "message": f"DP 已清空会话 {session_id} 的所有消息"}