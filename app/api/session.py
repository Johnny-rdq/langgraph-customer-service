from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.db import get_session
from app.models.db_models import ChatSession
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

@router.get("/")
def get_all_sessions(db: Session = Depends(get_session)):
    """获取所有历史会话（按最后更新时间倒序排序）"""
    sessions = db.exec(select(ChatSession).order_by(ChatSession.updated_at.desc())).all()
    return sessions

@router.post("/")
def create_session(db: Session = Depends(get_session)):
    """新建一个会话"""
    new_session = ChatSession(id=str(uuid.uuid4()), title="新对话")
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_session)):
    """删除指定会话"""
    session = db.get(ChatSession, session_id)
    if session:
        db.delete(session)
        db.commit()
    return {"status": "ok", "message": "删除成功"}