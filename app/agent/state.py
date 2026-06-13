"""
LangGraph 状态定义模块
定义图流转过程中使用的共享状态对象，所有节点通过此状态进行数据交换
"""
from typing import List, Annotated, Optional  # 类型标注工具
from typing_extensions import TypedDict  # TypedDict 用于定义结构化字典类型
from langgraph.graph.message import add_messages  # LangGraph 提供的消息列表追加函数
from langchain_core.messages import BaseMessage  # LangChain 消息基类


class AgentState(TypedDict):
    """Agent 状态定义 —— LangGraph 图中各节点共享的状态对象

    每个字段都定义了 reducer 函数，用于控制新数据如何合并到已有状态中。
    messages 字段使用 LangGraph 内置的 add_messages 作为 reducer，
    支持增量追加消息到消息列表。
    """
    # ── 对话消息列表 ──
    # reducer=add_messages 会自动将新消息追加到列表末尾，而不是覆盖
    messages: Annotated[List[BaseMessage], add_messages]

    # ── 用户 ID ──
    user_id: str  # 标识当前对话属于哪个用户

    # ── 会话 ID ──
    session_id: str  # 当前会话的唯一标识

    # ── 识别到的用户意图 ──
    intent: str  # 意图分类结果，如 "complaint" / "inquiry" / "general"

    # ── 检索到的知识库内容 ──
    retrieved_context: str  # RAG 检索出的相关知识点拼接文本

    # ── 是否需要转人工 ──
    requires_human: bool  # True 表示需要转接人工客服

    # ── 当前步骤名称 ──
    # 用于追踪和调试，记录当前正处于哪个节点
    current_step: str


def get_initial_state(
    user_id: str,
    session_id: str,
    first_message: Optional[BaseMessage] = None,
) -> AgentState:
    """创建图的初始状态

    在每次新对话或恢复会话时调用，构建初始状态字典

    Args:
        user_id: 用户唯一标识
        session_id: 会话唯一标识
        first_message: 首条用户消息（可选）

    Returns:
        初始化的 AgentState 字典
    """
    initial_messages = [first_message] if first_message else []  # 如果有首条消息则放入列表
    return {
        "messages": initial_messages,  # 初始消息列表
        "user_id": user_id,  # 用户 ID
        "session_id": session_id,  # 会话 ID
        "intent": "",  # 意图待识别
        "retrieved_context": "",  # 知识库内容待检索
        "requires_human": False,  # 默认不转人工
        "current_step": "init",  # 标记当前处于初始化步骤
    }

# 🌟 全局上下文变量（保险箱），用于跨文件无缝传递 ID
from contextvars import ContextVar
current_session_id: ContextVar[str] = ContextVar("current_session_id", default="")
