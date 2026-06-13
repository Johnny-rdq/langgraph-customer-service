"""
对话 API 路由模块
全面重写：加入物理级字符净化，彻底解决 Windows GBK 编码崩溃问题
"""
import uuid
import json
import asyncio as _asyncio  # 用于 to_thread 执行同步 graph.invoke
import logging
import time
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatRequest, ChatResponse
from app.agent.graph import build_graph
from app.agent.state import get_initial_state
from app.agent.nodes import INTENT_CLASSIFY_PROMPT, RESPONSE_GENERATION_PROMPT
from app.core.llm import get_llm
from app.tools.retriever import retrieve_knowledge
from langchain_core.messages import HumanMessage, AIMessage
from app.tools.logistics import handle_logistics_intent
from sqlmodel import Session
from app.core.db import engine
from app.models.db_models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])
_graph = build_graph()

# 🛡️ 终极核武器：物理抹除所有 Emoji 和特殊符号
def clean_text(text: str) -> str:
    if not text:
        return ""
    # 过滤掉所有不在基本多语言平面 (BMP) 的字符（精准删掉所有 Emoji）
    return re.sub(r'[^\u0000-\uFFFF]', '', text)

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """普通对话接口"""
    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())
    safe_message = clean_text(request.message)

    initial_state = get_initial_state(
        user_id=request.user_id,
        session_id=session_id,
        first_message=HumanMessage(content=safe_message),
    )

    try:
        import asyncio as _asyncio
        config = {"configurable": {"thread_id": session_id}}
        # SqliteSaver 不支持异步，在线程池中执行同步 invoke
        result = await _asyncio.to_thread(_graph.invoke, initial_state, config)

        messages = result.get("messages", [])
        reply = ""
        if messages:
            for msg in reversed(messages):
                if hasattr(msg, "type") and msg.type == "ai":
                    reply = msg.content
                    break

        intent = result.get("intent", "general")
        return ChatResponse(
            session_id=session_id,
            reply=clean_text(reply),
            intent=intent,
            requires_human=result.get("requires_human", False),
        )
    except Exception as e:
        logger.error(f"[ERROR] 处理出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="客服系统处理出错")


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式对话接口 —— SSE 逐字返回 AI 回复"""
    session_id = request.session_id or str(uuid.uuid4())
    safe_message = clean_text(request.message)

    async def event_generator():
        llm = get_llm()
        start_time = time.time()

        try:
            # 🌟🌟🌟 拦截器：检查是否已被人工接管 🌟🌟🌟
            with Session(engine) as db:
                chat_session = db.get(ChatSession, session_id)
                if chat_session and chat_session.is_human_mode:
                    # DP 会话已处于人工模式，用户消息已由 session.py 持久化，此处不重复保存。
                    # DP 通过 WebSocket 实时推送用户消息给管理员面板（减少 2 秒轮询延迟）。
                    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'intent': 'human', 'requires_human': True}, ensure_ascii=True)}\n\n"
                    try:
                        from app.api.ws import manager
                        await manager.broadcast_to_admin({
                            "type": "user_message",
                            "session_id": session_id,
                            "content": safe_message[:100],
                            "role": "user"
                        })
                    except Exception:
                        pass  # WebSocket 通知失败不影响主流程
                    return
            # 🌟🌟🌟 拦截器结束 🌟🌟🌟
        except:
            pass

        try:
            # 1. 意图识别
            intent_prompt = INTENT_CLASSIFY_PROMPT.format(user_message=safe_message)
            intent_response = await llm.ainvoke(intent_prompt)
            intent = clean_text(intent_response.content).strip().lower() if intent_response.content else "general"

            if re.findall(r'\d{5,}', safe_message):
                intent = "logistics"

            yield f"data: {json.dumps({'type': 'intent', 'content': intent}, ensure_ascii=True)}\n\n"

            # ─────────────────────────────────────────────────
            # DP 核心修复：用户转人工时立即写入数据库 + 通知管理员面板。
            # 问题背景：之前识别到 human 意图后只返回 requires_human=True，从未写 is_human_mode，
            # 导致管理员轮询 /ws/admin/sessions 永远看不到该会话。
            # 修复要点：①写入 is_human_mode ②创建 ChatSession（如不存在）
            # ③保存 AI 转接确认消息到 ChatMessage ④WebSocket 实时推送 ⑤结束 SSE 流
            # 注意：用户消息已由 session.py 的 save_message 持久化，此处不重复保存。
            # ─────────────────────────────────────────────────
            if intent == "human":
                try:
                    with Session(engine) as db:
                        chat_session = db.get(ChatSession, session_id)
                        if not chat_session:
                            chat_session = ChatSession(id=session_id, title=safe_message[:30])
                            db.add(chat_session)
                        chat_session.is_human_mode = True
                        db.add(chat_session)
                        # 保存 AI 转接确认消息（用户消息已由 session.py 持久化，避免重复）
                        transfer_msg = ChatMessage(
                            session_id=session_id, role="assistant",
                            content="【系统提示】已为您成功转接，人工客服马上就来！"
                        )
                        db.add(transfer_msg)
                        db.commit()
                        logger.info(f"✅ 转人工成功！会话 {session_id} 已写入排队队列")
                    try:
                        from app.api.ws import manager
                        await manager.broadcast_to_admin({
                            "type": "new_human_session",
                            "session_id": session_id,
                            "user_message": safe_message[:50]
                        })
                    except Exception as ws_err:
                        logger.warning(f"WebSocket 通知失败（不影响主流程）: {ws_err}")
                except Exception as e:
                    logger.error(f"转人工数据库写入失败: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'intent': 'human', 'requires_human': True}, ensure_ascii=True)}\n\n"
                return

            # 2. 获取背景资料
            context = "暂无相关背景信息。"
            is_logistics = "logistics" in intent
            if is_logistics:
                raw_logistics = handle_logistics_intent(safe_message, llm)  # 同步调用（物流查询无异步 IO）
                context = clean_text(raw_logistics)  # 物流查询结果（可能是轨迹信息或系统提示）
            elif "complaint" in intent or "inquiry" in intent:
                retrieved = retrieve_knowledge(query=safe_message, top_k=3)
                context = clean_text("\n".join(retrieved)) if retrieved else "暂无相关知识库内容。"

            has_knowledge = not context.startswith("暂无") and not context.startswith("系统提示：")
            yield f"data: {json.dumps({'type': 'retrieval', 'has_knowledge': has_knowledge}, ensure_ascii=True)}\n\n"

            # 3. 提取历史记录并流式生成
            config = {"configurable": {"thread_id": session_id}}
            state_snapshot = _graph.get_state(config)
            existing_messages = state_snapshot.values.get("messages", []) if state_snapshot.values else []

            chat_history = "\n".join(
                f"{'用户' if isinstance(m, HumanMessage) else '客服'}: {clean_text(m.content)}"
                for m in existing_messages[-10:]
            )

            # 物流查询使用专用提示词：告知 LLM 这是直接查询结果，直接转述给用户
            if is_logistics and has_knowledge:
                prompt = f"""你是一个友好、专业的客服助手。以下是用户查询的物流轨迹信息，请用自然友好的语言转述给用户。

## 物流轨迹信息
{context}

## 用户问题
{safe_message}

## 客服守则
1. 态度友好、耐心、专业
2. 直接基于物流轨迹信息回复用户，不要添加不存在的信息
3. 回复简洁明了，避免长篇大论
4. 使用礼貌用语
5. 禁止使用任何 Emoji 表情符号，只能输出纯文本

## 你的回复
"""
            elif is_logistics and not has_knowledge:
                # 物流查询失败（无单号或单号不存在），用系统提示润色
                prompt = f"""你是一个友好的客服助手。以下是系统内部提示，请转换成对用户友好、自然的回复。

系统提示: {context}

要求：态度友好、简洁明了，使用纯文本不要用 Emoji。

客服回复:"""
            else:
                prompt = RESPONSE_GENERATION_PROMPT.format(
                    retrieved_context=context,
                    chat_history=chat_history,
                    user_message=safe_message,
                )

            full_reply = ""
            async for chunk in llm.astream(prompt):
                raw_token = chunk.content if hasattr(chunk, "content") and chunk.content else ""

                # ⚔️ 核心防御：只要大模型吐出 Emoji，立刻变为空！
                token = clean_text(raw_token)

                if token:
                    full_reply += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=True)}\n\n"

            # 4. 存入数据库（此时 full_reply 已是纯文本，数据库绝对不会崩）
            try:
                _graph.update_state(
                    config,
                    {"messages": [HumanMessage(content=safe_message), AIMessage(content=full_reply)]}
                )
            except Exception as e:
                logger.warning(f"记忆写入失败，但不影响回复: {e}")

            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'intent': intent, 'requires_human': intent == 'human'}, ensure_ascii=True)}\n\n"

        except Exception as e:
            logger.error(f"[ERROR] 流式出错: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': '系统繁忙，请稍后再试'}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )