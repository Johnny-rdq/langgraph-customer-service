"""会话与消息管理 API 路由
提供会话 CRUD + 消息增删查的 RESTful 接口。
会话删除时级联删除所有关联消息。
消息持久化到 SQLite，支持跨设备/刷新后还原聊天记录。
"""
from fastapi import APIRouter, Depends, HTTPException  # FastAPI 路由、依赖注入、HTTP 异常
from sqlmodel import Session, select  # SQLModel 数据库会话和查询语句
from app.core.db import get_session  # 数据库会话依赖注入函数
from app.models.db_models import ChatSession, ChatMessage  # ORM 数据表模型
from app.models.schemas import SaveMessageRequest  # 保存消息的 Pydantic 请求体
from datetime import datetime  # 时间更新
import uuid  # 唯一 ID 生成工具
import logging  # 日志模块
from app.api.ws import manager

logger = logging.getLogger(__name__)  # 当前模块的日志记录器

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])  # 会话管理路由组


@router.post("/{session_id}/exit_human")
async def exit_human_mode(session_id: str, db: Session = Depends(get_session)):
    """用户主动退出人工客服模式"""
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 恢复为智能助手模式
    session.is_human_mode = False
    session.updated_at = datetime.utcnow()
    db.add(session)
    db.commit()

    # 🌟 瞬间通知管理端，把这个会话从排队列表中移除
    await manager.broadcast_to_admin({
        "type": "session_exited",
        "session_id": session_id
    })

    return {"status": "ok", "message": "已退出人工客服"}


# ═══════════════════════════════════════════════════════════
# 会话 CRUD
# ═══════════════════════════════════════════════════════════
@router.get("/")
def get_all_sessions(db: Session = Depends(get_session)):
    """获取所有历史会话，按最后更新时间倒序排列"""
    sessions = db.exec(
        select(ChatSession).order_by(ChatSession.updated_at.desc())  # 最新活跃的在前
    ).all()
    # 手动构建 dict 列表返回，避免触发 messages 关系的懒加载
    return [
        {
            "id": s.id,  # 会话 ID
            "title": s.title,  # 会话标题
            "created_at": s.created_at.isoformat(),  # 创建时间（ISO 格式）
            "updated_at": s.updated_at.isoformat(),  # 最后更新时间
        }
        for s in sessions
    ]


@router.post("/")
def create_session(db: Session = Depends(get_session)):
    """新建一个空白会话，返回会话信息给前端"""
    new_session = ChatSession(
        id=str(uuid.uuid4()),  # 生成全局唯一会话 ID
        title="新对话",  # 默认标题，后续由第一条用户消息自动更新
    )
    db.add(new_session)  # 加入数据库待提交
    db.commit()  # 提交事务写入数据库
    db.refresh(new_session)  # 刷新获取数据库生成的默认值
    return {
        "id": new_session.id,  # 返回会话 ID 给前端
        "title": new_session.title,  # 返回标题
        "created_at": new_session.created_at.isoformat(),  # 返回创建时间
        "updated_at": new_session.updated_at.isoformat(),  # 返回更新时间
    }


@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_session)):
    """删除指定会话及其所有消息（级联删除，由 ORM 关系自动处理）"""
    session = db.get(ChatSession, session_id)  # 查找会话对象
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")  # 404 返回给前端
    db.delete(session)  # 删除会话 → ORM 级联删除关联的所有 ChatMessage
    db.commit()  # 提交删除事务
    logger.info(f"会话已删除: {session_id[:8]}...")  # 记录日志
    return {"status": "ok", "message": f"会话 {session_id} 及其所有消息已删除"}  # 返回成功


@router.patch("/{session_id}")
def update_session_title(session_id: str, title: str, db: Session = Depends(get_session)):
    """更新会话标题，前端在第一条用户消息后自动调用"""
    session = db.get(ChatSession, session_id)  # 查找会话
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    session.title = title[:100]  # 截断标题，防止超过 100 字符撑爆 UI
    session.updated_at = datetime.utcnow()  # 刷新最后活跃时间
    db.add(session)  # 标记会话对象为脏
    db.commit()  # 提交更新
    db.refresh(session)  # 刷新获取最新数据
    return {
        "id": session.id,  # 返回更新后的会话 ID
        "title": session.title,  # 返回新标题
        "created_at": session.created_at.isoformat(),  # 返回创建时间
        "updated_at": session.updated_at.isoformat(),  # 返回更新时间
    }


# ═══════════════════════════════════════════════════════════
# 消息 CRUD
# ═══════════════════════════════════════════════════════════

@router.get("/{session_id}/messages")
def get_session_messages(session_id: str, db: Session = Depends(get_session)):
    """获取指定会话的所有消息，按创建时间正序排列"""
    session = db.get(ChatSession, session_id)  # 先确认会话存在
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = db.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)  # 按会话 ID 过滤消息
        .order_by(ChatMessage.created_at)  # 按创建时间正序（旧→新）
    ).all()

    # 转换为前端需要的 JSON 格式
    return [
        {
            "id": msg.id,  # 消息唯一 ID
            "role": msg.role,  # 消息角色（user/assistant）
            "content": msg.content,  # 消息文本内容
            "created_at": msg.created_at.isoformat(),  # 消息时间（ISO 格式）
        }
        for msg in messages
    ]


@router.post("/{session_id}/messages")
def save_message(
    session_id: str,
    body: SaveMessageRequest,  # JSON 请求体，Pydantic 自动校验
    db: Session = Depends(get_session),
):
    """保存一条消息到指定会话，同时自动更新会话标题和时间"""
    # 确认目标会话存在
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 创建消息 ORM 对象
    message = ChatMessage(
        id=str(uuid.uuid4()),  # 生成全局唯一消息 ID
        session_id=session_id,  # 关联到所属会话
        role=body.role,  # 消息角色（已由 SaveMessageRequest 校验正则）
        content=body.content,  # 消息文本内容
    )

    # 自动更新会话标题：标题还是默认值时，用第一条用户消息的前 30 字
    if session.title == "新对话" and body.role == "user":
        session.title = body.content[:30] + ("…" if len(body.content) > 30 else "")

    # 刷新会话最后活跃时间
    session.updated_at = datetime.utcnow()

    db.add(message)  # 将消息加入数据库待提交
    db.add(session)  # 将更新后的会话也标记为脏
    db.commit()  # 一次性提交事务
    db.refresh(message)  # 刷新消息对象获取数据库生成的默认值

    logger.info(
        f"[SAVE] 消息已保存: session={session_id[:8]}..., "
        f"role={body.role}, len={len(body.content)}"
    )
    return {
        "id": message.id,  # 返回消息 ID
        "role": message.role,  # 返回消息角色
        "content": message.content,  # 返回消息内容
        "created_at": message.created_at.isoformat(),  # 返回创建时间
    }


@router.delete("/{session_id}/messages")
def clear_session_messages(session_id: str, db: Session = Depends(get_session)):
    """清空指定会话的所有消息，保留会话本身"""
    session = db.get(ChatSession, session_id)  # 查找会话
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 查询该会话下的所有消息
    messages = db.exec(
        select(ChatMessage).where(ChatMessage.session_id == session_id)
    ).all()
    for msg in messages:
        db.delete(msg)  # 逐条删除消息

    session.updated_at = datetime.utcnow()  # 刷新会话最后活跃时间
    db.commit()  # 提交事务
    logger.info(f"已清空会话 {session_id[:8]}... 的所有消息")
    return {"status": "ok", "message": f"已清空会话 {session_id} 的所有消息"}  # 返回成功