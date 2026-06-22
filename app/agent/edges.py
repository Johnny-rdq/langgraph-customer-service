"""
LangGraph 条件边定义模块
"""
import logging
from app.agent.state import AgentState

logger = logging.getLogger(__name__)

def route_after_intent(state: AgentState) -> str:
    # 后端 同时读取意图和情绪，做差异化路由
    intent = state.get("intent", "general")
    sentiment = state.get("sentiment", "neutral")

    # 🌟 如果是静音模式（人工接管中），直接结束图流程，不查知识库也不聊天
    if intent == "silence":
        from langgraph.graph import END
        return END

    # 🌟 情绪负面 → 无论什么意图，一律转人工（用户情绪爆炸，AI 处理不了）
    if sentiment == "negative":
        return "human_service"

    if intent == "human":
        return "human_service"
    elif intent == "logistics":
        return "logistics_node"
    elif intent == "complaint":
        # 后端 情绪负面已在上面拦截，走到这的投诉情绪为 neutral/positive
        # 先走知识库检索让 AI 尝试解决，解决不了再转人工
        return "retrieve_knowledge"
    elif intent == "inquiry":
        return "retrieve_knowledge"
    else:
        return "direct_response"


def route_after_retrieval(state: AgentState) -> str:
    context = state.get("retrieved_context", "")

    if not context or context.startswith("暂无"):
        # 后端 知识库无匹配时仍尝试生成回复（generate_response 会自行判断是否转人工）
        return "generate_response"
    return "generate_response"

def route_after_response(state: AgentState) -> str:
    requires_human = state.get("requires_human", False)
    if requires_human:
        return "human_service"
    return "__end__"
