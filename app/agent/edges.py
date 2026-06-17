"""
LangGraph 条件边定义模块
"""
import logging
from app.agent.state import AgentState

logger = logging.getLogger(__name__)

def route_after_intent(state: AgentState) -> str:
    intent = state.get("intent", "general")

    # 🌟 如果是静音模式（人工接管中），直接结束图流程，不查知识库也不聊天
    if intent == "silence":
        from langgraph.graph import END
        return END

    if intent == "human":
        return "human_service"
    elif intent == "logistics":
        return "logistics_node"
    elif intent == "complaint":
        # 后端 投诉统一转人工处理，不走知识库检索
        return "human_service"
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
