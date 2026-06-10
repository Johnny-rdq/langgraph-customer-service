"""
对话 API 路由模块
提供面向前端的 RESTful 对话接口（普通 + 流式 SSE）
"""
import uuid                                    # 唯一会话 ID
import json                                    # JSON 序列化
import logging                                 # 日志
import time                                    # 计时
from fastapi import APIRouter, HTTPException   # FastAPI 路由和异常
from fastapi.responses import StreamingResponse # SSE 流式响应
from app.models.schemas import ChatRequest, ChatResponse  # 请求/响应模型
from app.agent.graph import build_graph        # Graph 工作流（非流式用）
from app.agent.state import get_initial_state  # 初始状态工厂
from app.agent.nodes import (                  # 导入 prompt 模板和工具
    INTENT_CLASSIFY_PROMPT,
    RESPONSE_GENERATION_PROMPT,
)
from app.core.llm import get_llm               # LLM 实例
from app.tools.retriever import retrieve_knowledge  # 知识库检索
from langchain_core.messages import HumanMessage, AIMessage  # LangChain 消息类型
from app.tools.logistics import handle_logistics_intent


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])
_graph = build_graph()  # 全局图实例（非流式端点用）


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """普通对话接口（一次性返回完整回复）"""
    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(
        f"📩 收到请求: user_id={request.user_id}, "
        f"session_id={session_id[:8]}..., message={request.message[:50]}..."
    )

    initial_state = get_initial_state(
        user_id=request.user_id,
        session_id=session_id,
        first_message=HumanMessage(content=request.message),
    )

    try:
        config = {"configurable": {"thread_id": session_id}}
        result = await _graph.ainvoke(initial_state, config=config)

        messages = result.get("messages", [])
        reply = ""
        if messages:
            for msg in reversed(messages):
                if hasattr(msg, "type") and msg.type == "ai":
                    reply = msg.content
                    break
            if not reply and messages:
                reply = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])

        intent = result.get("intent", "general")
        requires_human = result.get("requires_human", False)

        elapsed = time.time() - start_time
        logger.info(f"✅ 处理完成: elapsed={elapsed:.2f}s, intent={intent}")

        return ChatResponse(
            session_id=session_id,
            reply=reply,
            intent=intent,
            requires_human=requires_human,
        )
    except Exception as e:
        logger.error(f"❌ 处理出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"客服系统处理出错: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式对话接口 —— SSE 逐字返回 AI 回复

    流程：意图识别 → 知识检索 → 流式生成回复
    前端通过 EventSource / fetch + ReadableStream 接收
    """
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"📩 [流式] 收到请求: session={session_id[:8]}..., msg={request.message[:50]}...")

    # ── 生成 SSE 事件的异步生成器 ──
    async def event_generator():
        llm = get_llm()
        start_time = time.time()

        try:
            # ── 第 1 步：意图识别（非流式，很快）──
            intent_prompt = INTENT_CLASSIFY_PROMPT.format(user_message=request.message)
            intent_response = await llm.ainvoke(intent_prompt)
            intent = intent_response.content.strip().lower() if intent_response.content else "general"
            logger.info(f"📌 [流式] 意图: {intent}")

            # 发送意图事件
            yield f"data: {json.dumps({'type': 'intent', 'content': intent}, ensure_ascii=False)}\n\n"

            # ── 第 2 步：背景信息获取（智能路由）──
            context = "暂无相关背景信息。"

            if "logistics" in intent:
                print("🔀 [DEBUG-ROUTE] 路由命中：物流意图，准备调用工具...")
                context = await handle_logistics_intent(request.message, llm)
                print("📊 [DEBUG-ROUTE] 工具执行完毕，成功拿到 context 背景资料！")

            elif "complaint" in intent or "inquiry" in intent:
                retrieved = retrieve_knowledge(query=request.message, top_k=3)
                context = "\n".join(retrieved) if retrieved else "暂无相关知识库内容。"

            # 发送检索事件
            has_knowledge = context != "暂无相关知识库内容。"
            yield f"data: {json.dumps({'type': 'retrieval', 'has_knowledge': has_knowledge}, ensure_ascii=False)}\n\n"

            # ── 第 3 步：流式生成回复 ──

            # [新增] 1. 配置当前会话 ID
            config = {"configurable": {"thread_id": session_id}}

            # [新增] 2. 从 LangGraph 获取历史记忆
            state_snapshot = _graph.get_state(config)
            existing_messages = state_snapshot.values.get("messages", []) if state_snapshot.values else []

            # [新增] 3. 拼装成历史文本（只取最近 10 条防超长）
            chat_history = "\n".join(
                f"{'用户' if isinstance(m, HumanMessage) else '客服'}: {m.content}"
                for m in existing_messages[-10:]
            )

            # 修改 Prompt，把空字符串换成真实的 chat_history
            prompt = RESPONSE_GENERATION_PROMPT.format(
                retrieved_context=context,
                chat_history=chat_history,  # <--- 修改这里
                user_message=request.message,
            )

            # ... 这里的 async for chunk in llm.astream(prompt): 保持不变 ...

            # 流式调用 LLM，逐 token yield
            full_reply = ""
            async for chunk in llm.astream(prompt):
                token = chunk.content if hasattr(chunk, "content") and chunk.content else ""
                if token:
                    full_reply += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"


            # [新增] 4. 将本轮问答存入 LangGraph 记忆库
            _graph.update_state(
                config,
                {"messages": [
                    HumanMessage(content=request.message),
                    AIMessage(content=full_reply)
                ]}
            )

            # ── 发送完成事件 ──
            elapsed = time.time() - start_time

            logger.info(f"✅ [流式] 完成: elapsed={elapsed:.2f}s, len={len(full_reply)}")

            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'intent': intent, 'requires_human': intent == 'human'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"❌ [流式] 出错: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",        # SSE MIME 类型
        headers={
            "Cache-Control": "no-cache",        # 禁止缓存
            "Connection": "keep-alive",         # 保持连接
            "X-Accel-Buffering": "no",          # Nginx 禁用缓冲（如有）
        },
    )


@router.get("/health")
async def health_check():
    """健康检查接口"""
    from app.core.config import get_settings
    settings = get_settings()
    return {
        "status": "healthy",
        "model": settings.LLM_MODEL,
        "service": "langgraph-customer-service",
    }
