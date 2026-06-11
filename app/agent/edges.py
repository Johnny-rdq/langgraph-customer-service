"""
LangGraph 条件边定义模块
定义图中各节点之间的路由逻辑 —— 根据当前状态决定下一步走向哪个节点
"""
import logging  # 日志模块
from app.agent.state import AgentState  # 导入状态定义

logger = logging.getLogger(__name__)  # 创建日志记录器


def route_after_intent(state: AgentState) -> str:
    """意图识别后的路由函数 —— 根据意图决定下一步节点

    返回目标节点名称，LangGraph 会根据返回值进行路由。

    路由规则:
    - human   → human_service (用户要求转人工)
    - complaint → retrieve_knowledge (先查知识库，再回复)
    - inquiry  → retrieve_knowledge (先查知识库，再回复)
    - general  → direct_response (直接回复，跳过检索)
    - 其他     → direct_response (兜底策略，直接回复)

    Args:
        state: 当前图状态（含意图字段）

    Returns:
        下一个节点名称字符串
    """
    intent = state.get("intent", "general")  # 获取意图，默认 general
    logger.info(f"[ROUTE] 路由决策: intent={intent}")  # 记录路由决策

    if intent == "human":
        return "human_service"  # 用户要求转人工
    elif intent in ("complaint", "inquiry", "logistics"):
        return "retrieve_knowledge"  # 投诉/咨询/物流，先查知识库
    else:
        return "direct_response"  # 闲聊或未知意图，直接回复


def route_after_retrieval(state: AgentState) -> str:
    """知识库检索后的路由函数 —— 根据检索结果质量决定下一步

    判断检索到的内容是否足以回答用户问题。

    路由规则:
    - 检索到有用内容 → generate_response (基于知识库生成回复)
    - 检索内容为空或质量差 → generate_response (仍走生成节点，但会告知用户)
    - 意图为 complaint 且知识库无相关售后政策 → human_service (转人工)

    Args:
        state: 当前图状态（含检索内容和意图）

    Returns:
        下一个节点名称字符串
    """
    context = state.get("retrieved_context", "")  # 获取检索内容
    intent = state.get("intent", "")  # 获取意图

    # 如果检索内容为空或只有占位文本，判断是否需要转人工
    if not context or context.startswith("暂无"):
        if intent == "complaint":
            logger.info("[ROUTE] 投诉类问题且知识库无匹配，转人工")
            return "human_service"  # 投诉类且无知识匹配，转人工
        # 非投诉类，仍然尝试生成回复
        logger.info("[ROUTE] 知识库无匹配，尝试直接生成回复")
        return "generate_response"

    logger.info("[ROUTE] 知识库有匹配，进入回复生成")
    return "generate_response"  # 有检索内容，进入回复生成节点


def route_after_response(state: AgentState) -> str:
    """回复生成后的路由函数 —— 判断是否需要兜底转人工

    在生成回复后，检查是否需要转人工（例如 AI 回复中表达了不确定性）。

    Args:
        state: 当前图状态

    Returns:
        下一个节点名称字符串，通常为 END 表示结束
    """
    requires_human = state.get("requires_human", False)  # 获取转人工标志

    if requires_human:
        logger.info("[ROUTE] AI 信心不足，补充转人工")
        return "human_service"  # 回复后仍需转人工（兜底逻辑）

    logger.info("[ROUTE] 流程结束")
    return "__end__"  # LangGraph 内置结束标记，表示流程终止
