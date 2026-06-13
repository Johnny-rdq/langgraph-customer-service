"""
LangGraph 节点定义模块
定义工作流中每个节点的具体逻辑：意图识别、知识检索、生成回复、转人工判断
"""
import logging  # 日志模块，用于记录运行信息
from langchain_core.messages import AIMessage, HumanMessage  # LangChain 消息类型
from app.agent.state import AgentState  # 导入状态定义
from app.core.llm import get_llm  # 导入 LLM 实例获取函数
from app.tools.retriever import retrieve_knowledge  # 导入知识库检索工具
from app.tools.logistics import handle_logistics_intent  # 导入物流查询工具
from sqlmodel import Session
from app.core.db import engine  # 假设你的 db.py 里暴露了 engine
from app.models.db_models import ChatSession
import requests
import threading

logger = logging.getLogger(__name__)  # 创建当前模块的日志记录器


# ── 意图识别提示模板 ──
INTENT_CLASSIFY_PROMPT = """你是一个智能客服的意图识别模块。请分析用户的输入，判断其意图类别。

## 意图类别
- complaint: 用户投诉产品或服务问题
- inquiry: 用户咨询产品信息、使用方法、政策等
- logistics: 查询订单状态、物流、快递到哪了等。
- general: 一般性问候或闲聊
- human: 用户明确要求转人工客服


## 输出格式
只输出意图类别名称，不要输出任何其他内容。

用户消息: {user_message}

意图:"""


# ── 回复生成提示模板 ──
RESPONSE_GENERATION_PROMPT = """你是一个专业、友好的客服助手。请根据以下信息回复用户。

## 客服守则
1. 态度友好、耐心、专业
2. 如果有相关知识库内容，优先基于知识库回复
3. 如果知识库无法解答，诚实告知用户，并建议转人工
4. 回复简洁明了，避免长篇大论
5. 使用礼貌用语
6. 绝对禁止使用任何 Emoji 表情符号（如 📦、🚚、🔀 等特殊图形），只能输出纯文本！

## 知识库参考内容
{retrieved_context}

## 对话历史
{chat_history}

## 当前用户消息
{user_message}

## 你的回复
"""


def classify_intent_node(state: dict, config: dict = None) -> dict:
    import logging
    from app.core.db import engine
    from sqlmodel import Session
    from app.models.db_models import ChatSession
    from langchain_core.messages import AIMessage
    from app.agent.state import current_session_id  # 👈 导入保险箱

    logger = logging.getLogger(__name__)

    # 🎯 降维打击：不靠底层传参了，直接从保险箱里拿！
    session_id = current_session_id.get()

    if session_id:
        try:
            with Session(engine) as db:
                chat = db.get(ChatSession, session_id)
                # 只有精准匹配到的当前会话是人工模式，才静音
                if chat and chat.is_human_mode:
                    return {
                        **state,
                        "intent": "silence",
                        "messages": [AIMessage(content="[系统: 消息已送达客服，请稍候...]")],
                        "current_step": "classify_intent",
                    }
        except Exception as e:
            pass

    user_message = state["messages"][-1].content if state["messages"] else ""
    from app.core.llm import get_llm
    prompt = INTENT_CLASSIFY_PROMPT.format(user_message=user_message)

    llm = get_llm()
    response = llm.invoke(prompt)
    intent = response.content.strip().lower()

    import re
    if re.findall(r'\d{5,}', user_message):
        intent = "logistics"

    return {
        **state,
        "intent": intent,
        "current_step": "classify_intent",
    }


def retrieve_knowledge_node(state: AgentState) -> AgentState:
    logger.info("[RETRIEVE] 进入知识库检索节点...")
    user_message = state["messages"][-1].content if state["messages"] else ""
    retrieved_docs = retrieve_knowledge(query=user_message, top_k=3)
    context = "\n\n---\n\n".join(retrieved_docs) if retrieved_docs else "暂无相关知识库内容。"

    logger.info(f"[RETRIEVE] 检索到 {len(retrieved_docs)} 条相关知识")
    return {
        **state,
        "retrieved_context": context,
        "current_step": "retrieve_knowledge",
    }


def generate_response_node(state: AgentState) -> AgentState:
    logger.info("[REPLY] 进入回复生成节点...")
    llm = get_llm()
    user_message = state["messages"][-1].content if state["messages"] else ""

    history_messages = state["messages"][:-1] if len(state["messages"]) > 1 else []
    chat_history = "\n".join(
        f"{'用户' if isinstance(m, HumanMessage) else '客服'}: {m.content}"
        for m in history_messages[-10:]
    )

    prompt = RESPONSE_GENERATION_PROMPT.format(
        retrieved_context=state["retrieved_context"] or "暂无相关知识库内容。",
        chat_history=chat_history or "暂无历史对话。",
        user_message=user_message,
    )

    response = llm.invoke(prompt)
    reply_text = response.content.strip()

    logger.info(f"[OK] 回复生成完成，长度: {len(reply_text)} 字符")
    return {
        **state,
        "messages": [AIMessage(content=reply_text)],
        "current_step": "generate_response",
    }


def human_service_node(state: AgentState, config: dict = None) -> AgentState:
    """
    DP 转人工客服节点 —— 将当前会话标记为人工模式，写入数据库排队队列。
    DP 设计思路：前端主要走 chat_stream (SSE) 路径，但图路径（main.py 的 /messages 接口）
    DP 也会触发此节点。因此本节点作为兜底方案，确保无论走哪条路径，is_human_mode 都能被写入。
    DP session_id 获取策略（优先级从高到低）：
    DP   1. ContextVar（main.py 中间件已从 URL 中提取并存入保险箱）
    DP   2. config["configurable"]["thread_id"]（LangGraph 配置传递）
    DP   3. state["session_id"]（状态中的会话 ID）
    DP   4. 数据库最新会话兜底（暴力兜底，避免找不到 ID）
    DP 副作用：
    DP   1. 向 ChatSession 表写入 is_human_mode = True（管理员面板据此拉取排队列表）
    DP   2. 会话记录不存在时自动创建
    DP   3. 保存用户最后一条消息到 ChatMessage 表
    DP   4. 通过 WebSocket 实时通知管理员面板（减少轮询延迟）
    """
    import logging
    from app.core.db import engine
    from sqlmodel import Session as DBSession, select
    from app.models.db_models import ChatSession, ChatMessage
    from langchain_core.messages import AIMessage, HumanMessage
    from app.agent.state import current_session_id  # ContextVar 保险箱

    logger = logging.getLogger(__name__)

    # ── session_id 获取策略（多级降级）──
    session_id = None
    # 优先级 1：ContextVar（main.py 中间件从 URL 提取）
    try:
        ctx_id = current_session_id.get()
        if ctx_id:
            session_id = ctx_id
            logger.info(f"🔒 从 ContextVar 获取 session_id: {session_id}")
    except Exception as e:
        logger.debug(f"ContextVar 读取失败（正常情况）: {e}")

    # 优先级 2：LangGraph config 中的 thread_id
    if not session_id and config and "configurable" in config:
        session_id = config["configurable"].get("thread_id")
        if session_id:
            logger.info(f"🔧 从 config 获取 session_id: {session_id}")

    # 优先级 3：state 中的 session_id
    if not session_id:
        session_id = state.get("session_id")
        if session_id:
            logger.info(f"📋 从 state 获取 session_id: {session_id}")

    # ── 提取用户最后一条消息文本（用于保存和通知）──
    user_message_text = ""
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, "content"):
            user_message_text = last_msg.content[:100]  # 截取前 100 字符
        elif isinstance(last_msg, dict):
            user_message_text = last_msg.get("content", "")[:100]

    # ── 写入数据库 ──
    saved_session_id = None  # 记录最终写入的会话 ID
    try:
        with DBSession(engine) as db:
            chat = None
            if session_id:
                chat = db.get(ChatSession, session_id)
                # 会话记录不存在则自动创建
                if not chat:
                    chat = ChatSession(id=session_id, title=user_message_text[:30] or "转人工会话")
                    db.add(chat)
                    logger.info(f"📝 自动创建 ChatSession: {session_id}")

            if not chat:
                # 终极兜底：取数据库最新会话
                chat = db.exec(select(ChatSession).order_by(ChatSession.created_at.desc())).first()
                if chat:
                    logger.warning(f"⚠️ 未找到指定会话，兜底使用最新会话: {chat.id}")

            if chat:
                chat.is_human_mode = True  # 标记为人工模式
                db.add(chat)
                # 保存用户最后一条消息（供管理员查看）
                if user_message_text and chat.id:
                    user_msg = ChatMessage(
                        session_id=chat.id,
                        role="user",
                        content=user_message_text
                    )
                    db.add(user_msg)
                    # DP 同时保存 AI 转接确认消息，确保轮询加载时用户能看到转接提示
                    transfer_msg = ChatMessage(
                        session_id=chat.id, role="assistant",
                        content="【系统提示】已为您成功转接，人工客服马上就来！"
                    )
                    db.add(transfer_msg)
                db.commit()
                saved_session_id = chat.id
                logger.info(f"✅ 转人工成功！会话 {saved_session_id} 已写入排队队列")
            else:
                logger.error("❌ 转人工失败：无法找到任何会话记录")
    except Exception as e:
        logger.error(f"转人工数据库写入失败: {e}", exc_info=True)

    # ── 通过 WebSocket 实时通知管理员面板 ──
    if saved_session_id:
        try:
            import asyncio
            from app.api.ws import manager
            # 尝试在事件循环中发送广播（图路径可能是同步调用）
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(manager.broadcast_to_admin({
                    "type": "new_human_session",
                    "session_id": saved_session_id,
                    "user_message": user_message_text[:50]
                }))
            except RuntimeError:
                # 没有运行中的事件循环，同步场景下跳过通知（管理员轮询兜底）
                logger.debug("无运行中的事件循环，跳过 WebSocket 通知（管理员轮询会兜底）")
        except Exception as ws_err:
            logger.debug(f"WebSocket 通知跳过（正常情况）: {ws_err}")

    return {
        **state,
        "requires_human": True,
        "messages": [AIMessage(content="【系统提示】已为您成功转接，人工客服马上就来！")],
        "current_step": "human_service",
    }


def direct_response_node(state: AgentState) -> AgentState:
    logger.info("[REPLY] 进入直接回复节点...")
    llm = get_llm()
    user_message = state["messages"][-1].content if state["messages"] else ""
    greeting_prompt = f"""你是一个友好的客服助手。用户发来了一条消息，请给出简洁友好的回复。

用户消息: {user_message}

客服回复:"""

    response = llm.invoke(greeting_prompt)
    reply_text = response.content.strip()

    logger.info(f"[OK] 直接回复完成，长度: {len(reply_text)} 字符")
    return {
        **state,
        "messages": [AIMessage(content=reply_text)],
        "current_step": "direct_response",
    }


def logistics_node(state: AgentState) -> AgentState:
    logger.info("[LOGISTICS] 进入物流查询节点...")
    user_message = state["messages"][-1].content if state["messages"] else ""
    llm = get_llm()
    result_text = handle_logistics_intent(user_message, llm)

    if result_text.startswith("系统提示："):
        polish_prompt = f"""你是一个友好的客服助手。以下是系统给出的内部提示，请把它转换成对用户友好、自然的回复。

系统提示: {result_text}

要求：态度友好、简洁明了，使用纯文本不要用 Emoji。

客服回复:"""
        response = llm.invoke(polish_prompt)
        reply_text = response.content.strip()
    else:
        polish_prompt = f"""你是一个友好的客服助手。以下是用户的物流查询结果，请用友好、自然的语言告诉用户。

物流信息: {result_text}

要求：态度友好、简洁明了，使用纯文本不要用 Emoji。

客服回复:"""
        response = llm.invoke(polish_prompt)
        reply_text = response.content.strip()

    logger.info(f"[LOGISTICS] 物流查询完成，回复长度: {len(reply_text)} 字符")
    return {
        **state,
        "messages": [AIMessage(content=reply_text)],
        "current_step": "logistics",
    }