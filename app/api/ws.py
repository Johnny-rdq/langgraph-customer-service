# app/api/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import logging
from pydantic import BaseModel
from sqlmodel import Session
from app.core.db import engine
from app.models.db_models import ChatMessage
from fastapi import Request
from sqlmodel import select
from app.models.db_models import ChatSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ws", tags=["websocket"])

class ConnectionManager:
    """
    WebSocket 连接管理器 —— 管理两类连接：
      1. 用户连接：以 session_id 为 key，用于向用户推送客服回复
      2. 管理员连接：以 __admin_broadcast__ 为 key，用于向管理员面板实时推送新排队会话通知
    管理员面板原本只靠 3 秒轮询拉取排队列表，用户转人工后最坏要等 3 秒。
    新增 connect_admin / disconnect_admin / broadcast_to_admin 方法，
    让后端在会话转人工时立即推送通知，管理员面板收到后立即刷新，无需等轮询。
    """
    ADMIN_KEY = "__admin_broadcast__"  # 管理员专用 session key

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}  # { session_id: [websocket, ...] }
        # 预置管理员频道连接列表（独立于用户连接，避免广播时污染用户 channel）
        if self.ADMIN_KEY not in self.active_connections:
            self.active_connections[self.ADMIN_KEY] = []

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"Session {session_id} WebSocket connected. Total connections: {len(self.active_connections[session_id])}")

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
            logger.info(f"Session {session_id} WebSocket disconnected.")

    async def send_personal_message(self, message: dict, session_id: str):
        """向指定的会话发送 JSON 消息（用于向用户推送客服回复）"""
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"WebSocket 消息发送失败: {e}")

    # ── 管理员面板实时推送方法（详见类 docstring）──
    async def connect_admin(self, websocket: WebSocket):
        """管理员面板 WebSocket 连接（复用 ADMIN_KEY 隔离用户连接）"""
        await self.connect(websocket, self.ADMIN_KEY)
        logger.info(f"🔔 管理员面板已连接，当前管理端连接数: {len(self.active_connections.get(self.ADMIN_KEY, []))}")

    def disconnect_admin(self, websocket: WebSocket):
        """管理员面板断开连接"""
        self.disconnect(websocket, self.ADMIN_KEY)

    async def broadcast_to_admin(self, message: dict):
        """向所有管理员面板广播消息，发送失败不抛异常（单个连接失败不影响其他）"""
        admin_connections = self.active_connections.get(self.ADMIN_KEY, [])
        if not admin_connections:
            logger.debug("无管理员面板连接，跳过广播")
            return
        disconnected = []  # 收集断开的连接稍后统一清理
        for connection in admin_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"管理员 WebSocket 发送失败，标记清理: {e}")
                disconnected.append(connection)
        for conn in disconnected:  # 清理断开的连接
            try:
                self.disconnect_admin(conn)
            except Exception:
                pass
        if admin_connections:
            logger.debug(f"📡 已向 {len(admin_connections)} 个管理员面板推送: {message.get('type', 'unknown')}")

# 🌟 新增：客服专属的“打字机”接口
class AdminMessage(BaseModel):
    session_id: str
    content: str

# 实例化全局管理器
manager = ConnectionManager()

@router.websocket("/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            # 等待接收客户端发来的消息（这主要是为了维持心跳或接收用户端的主动通信）
            data = await websocket.receive_text()
            # 这里的处理逻辑后续可以扩展，目前先放着
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)


# ── 管理员面板专用 WebSocket 端点（路径: ws://localhost:8888/api/v1/ws/admin/listen）──
@router.websocket("/admin/listen")
async def admin_websocket_endpoint(websocket: WebSocket):
    """
    管理员打开 /admin 时自动连接此端点，后端在用户转人工时通过
    broadcast_to_admin 推送新会话通知，管理员面板收到后立即刷新排队列表。
    """
    await manager.connect_admin(websocket)
    try:
        while True:
            # 保持连接活跃，接收客户端心跳（ping）
            data = await websocket.receive_text()
            # 如果收到 "ping"，回复 "pong" 保持连接
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_admin(websocket)
        logger.info("🔔 管理员面板已断开")


@router.post("/admin/send", summary="客服工作台：向指定会话发消息")
async def admin_send_message(msg: AdminMessage):
    # 1. 把客服的回复存入数据库，确保刷新页面不丢失
    try:
        with Session(engine) as db:
            admin_msg = ChatMessage(
                session_id=msg.session_id,
                role="assistant",
                content=msg.content
            )
            db.add(admin_msg)
            db.commit()
    except Exception as e:
        logger.error(f"客服消息入库失败: {e}")

    # 2. 通过 WebSocket 瞬间推送给正在看页面的用户
    await manager.send_personal_message({
        "type": "admin_reply",
        "content": msg.content
    }, msg.session_id)

    return {"status": "ok", "message": "已成功发送给用户！"}


# 🌟 新增：供飞书/钉钉机器人回调的 Webhook 接口
@router.post("/webhook/im", summary="接收飞书机器人的消息回调")
async def im_webhook_receiver(request: Request):
    """
    飞书群里有人回复消息时，飞书平台会把内容推送给这个接口。
    """
    try:
        payload = await request.json()
        logger.info(f"[FEISHU] 收到飞书事件推送: {payload}")

        # 🌟 飞书首次配置 URL 时，会发送一个 challenge 验证请求，必须原样返回
        if "challenge" in payload:
            return {"challenge": payload["challenge"]}

        # 解析飞书发送的消息事件
        event = payload.get("event", {})
        message = event.get("message", {})

        if not message:
            return {"status": "ignored"}

        # 1. 提取飞书群里输入的文本内容（飞书返回的 text 是 JSON 字符串格式）
        import json
        content_str = message.get("content", "{}")
        content_data = json.loads(content_str)
        raw_text = content_data.get("text", "").strip()  # 客服实际回复的话

        # 🌟 核心工程设计：客服怎么指定发给哪个用户？
        # 我们在通知飞书时，文本里会带上【会话ID: xxx】
        # 客服在飞书回复时，可以采用格式：“会话ID 你的回复内容”
        # 这里用正则表达式，精准剥离出目标的会话 ID 和真正的回复内容
        import re
        match = re.match(r"([a-f0-9\-]{36})\s+(.*)", raw_text)
        if not match:
            logger.warning(f"[FEISHU] 收到非标准格式回复，忽略: {raw_text}")
            return {"status": "format_error", "msg": "未检测到有效的 UUID 会话ID"}

        target_session_id = match.group(1)
        actual_reply = match.group(2)

        # 2. 将真人的回复同步持久化到数据库
        with Session(engine) as db:
            admin_msg = ChatMessage(
                session_id=target_session_id,
                role="assistant",
                content=actual_reply
            )
            db.add(admin_msg)
            db.commit()

        # 3. 触发 WebSocket，将真人客服的话瞬间大跨步推送到用户的浏览器屏幕
        await manager.send_personal_message({
            "type": "admin_reply",
            "content": actual_reply
        }, target_session_id)

        logger.info(f"[SUCCESS] 飞书人工回复已成功同步至会话: {target_session_id}")
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"[FEISHU ERROR] 处理回调失败: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.get("/admin/sessions", summary="获取所有等待人工接管的会话")
async def get_human_sessions():
    """
    供客服前端页面调用，拉取排队列表。
    按创建时间倒序排列（最新转人工的排最上面），
    同时返回会话标题（与用户聊天侧边栏标题同步），便于客服识别。
    """
    try:
        from app.core.db import engine
        from sqlmodel import Session
        with Session(engine) as db:
            sessions = db.exec(
                select(ChatSession)
                .where(ChatSession.is_human_mode == True)
                .order_by(ChatSession.created_at.desc())  # 最新排最上面
            ).all()

            return [
                {
                    "session_id": s.id,
                    "title": s.title or "新对话",  # 会话标题，与用户侧边栏同步
                    "created_at": s.created_at,
                }
                for s in sessions
            ]
    except Exception as e:
        logger.error(f"拉取排队列表失败: {e}")
        return []