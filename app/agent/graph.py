"""
LangGraph 图组装模块
将 State、Nodes、Edges 组装成完整的工作流，编译为可执行的 graph 应用
"""
import logging  # 日志模块
from langgraph.graph import StateGraph, END  # LangGraph 核心：状态图和结束标记
from app.agent.state import AgentState  # 导入状态定义
from app.agent.nodes import (  # 导入所有节点函数
    classify_intent_node,
    retrieve_knowledge_node,
    generate_response_node,
    human_service_node,
    direct_response_node,
)
from app.agent.edges import (  # 导入所有路由函数
    route_after_intent,
    route_after_retrieval,
    route_after_response,
)

logger = logging.getLogger(__name__)  # 创建日志记录器


def build_graph() -> StateGraph:
    """构建并编译 LangGraph 客服工作流

    工作流结构:
    ```
    classify_intent (意图识别)
        ├── intent=human ──→ human_service ──→ END
        ├── intent=complaint/inquiry ──→ retrieve_knowledge (检索知识库)
        │       ├── 有匹配 ──→ generate_response ──→ END
        │       └── 无匹配(投诉) ──→ human_service ──→ END
        └── intent=general ──→ direct_response ──→ END
    ```

    Returns:
        编译好的 StateGraph 实例，可用于 invoke/ainvoke
    """
    logger.info("🏗️  开始构建 LangGraph 客服工作流...")  # 记录日志

    # ── 创建状态图 ──
    workflow = StateGraph(AgentState)  # 指定图的状态类型

    # ── 添加节点 ──
    # 每个节点对应一个处理函数
    workflow.add_node("classify_intent", classify_intent_node)  # 意图识别节点
    workflow.add_node("retrieve_knowledge", retrieve_knowledge_node)  # 知识库检索节点
    workflow.add_node("generate_response", generate_response_node)  # 回复生成节点
    workflow.add_node("human_service", human_service_node)  # 人工客服节点
    workflow.add_node("direct_response", direct_response_node)  # 直接回复节点（闲聊）

    # ── 设置入口点 ──
    # 所有对话都从意图识别开始
    workflow.set_entry_point("classify_intent")

    # ── 添加条件边 ──
    # 从意图识别节点出发，根据意图路由到不同节点
    workflow.add_conditional_edges(
        "classify_intent",  # 出发节点
        route_after_intent,  # 路由函数
        {
            "human_service": "human_service",  # 转人工
            "retrieve_knowledge": "retrieve_knowledge",  # 检索知识库
            "direct_response": "direct_response",  # 直接回复
        },
    )

    # ── 从检索节点出发的条件边 ──
    workflow.add_conditional_edges(
        "retrieve_knowledge",  # 出发节点
        route_after_retrieval,  # 路由函数
        {
            "generate_response": "generate_response",  # 生成回复
            "human_service": "human_service",  # 转人工
        },
    )

    # ── 从回复生成节点出发的条件边 ──
    workflow.add_conditional_edges(
        "generate_response",  # 出发节点
        route_after_response,  # 路由函数
        {
            "human_service": "human_service",  # 兜底转人工
            "__end__": END,  # 结束
        },
    )

    # ── 普通边（无条件跳转）──
    workflow.add_edge("human_service", END)  # 人工节点后结束
    workflow.add_edge("direct_response", END)  # 直接回复后结束

    # ── 编译图 ──
    compiled_graph = workflow.compile()  # 将图编译为可执行对象

    logger.info("✅ LangGraph 客服工作流构建完成!")  # 记录完成日志
    return compiled_graph  # 返回编译后的图
