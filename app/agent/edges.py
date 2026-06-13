"""
LangGraph 条件边定义模块
"""
import logging
from app.agent.state import AgentState

logger = logging.getLogger(__name__)

def route_after_intent(state: AgentState) -> str:
    # 1. 绝对强制物理拦截转人工
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        content = last_msg.content if hasattr(last_msg, 'content') else last_msg.get('content', '')
        if "转人工" in content or "人工" in content or "投诉" in content:
            return "human_service"

    intent = state.get("intent", "general")

    # 🌟 如果是静音模式（人工接管中），直接结束图流程，不查知识库也不聊天
    if intent == "silence":
        from langgraph.graph import END
        return END

    if intent == "human":
        return "human_service"
    elif intent == "logistics":
        return "logistics_node"
    elif intent in ("complaint", "inquiry"):
        return "retrieve_knowledge"
    else:
        return "direct_response"


def route_after_retrieval(state: AgentState) -> str:
    context = state.get("retrieved_context", "")
    intent = state.get("intent", "")

    if not context or context.startswith("暂无"):
        if intent == "complaint":
            return "human_service"
        return "generate_response"
    return "generate_response"

def route_after_response(state: AgentState) -> str:
    requires_human = state.get("requires_human", False)
    if requires_human:
        return "human_service"
    return "__end__"