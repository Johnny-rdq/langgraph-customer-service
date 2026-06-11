"""
LangGraph 节点定义模块
定义工作流中每个节点的具体逻辑：意图识别、知识检索、生成回复、转人工判断
"""
import logging  # 日志模块，用于记录运行信息
from langchain_core.messages import AIMessage, HumanMessage  # LangChain 消息类型
from app.agent.state import AgentState  # 导入状态定义
from app.core.llm import get_llm  # 导入 LLM 实例获取函数
from app.tools.retriever import retrieve_knowledge  # 导入知识库检索工具

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

## 知识库参考内容
{retrieved_context}

## 对话历史
{chat_history}

## 当前用户消息
{user_message}

## 你的回复
"""


def classify_intent_node(state: AgentState) -> AgentState:
    """意图识别节点 —— 分析用户输入，分类用户意图

    作为图的入口节点，识别用户意图后路由到不同的下游节点。

    Args:
        state: 当前图状态

    Returns:
        更新后的图状态（含意图字段）
    """
    logger.info("[SEARCH] 进入意图识别节点...")  # 记录日志

    # 获取最后一条用户消息
    user_message = state["messages"][-1].content if state["messages"] else ""

    # 构建意图识别提示
    prompt = INTENT_CLASSIFY_PROMPT.format(user_message=user_message)

    # 调用 LLM 进行意图识别
    llm = get_llm()  # 获取 LLM 实例
    response = llm.invoke(prompt)  # 同步调用 LLM
    intent = response.content.strip().lower()  # 提取并清洗意图字符串

    # 预判：消息含 ≥5 位连续数字直接当物流
    import re
    digits = re.findall(r'\d{5,}', user_message)
    if digits:
        intent = "logistics"
        logger.info(f"[INTENT] 预判物流（检测到数字: {digits[0]}），跳过 LLM 分类")

    logger.info(f"[INTENT] 最终意图: {intent}")
    return {
        **state,  # 保留原有状态
        "intent": intent,  # 更新意图
        "current_step": "classify_intent",  # 更新当前步骤
    }


def retrieve_knowledge_node(state: AgentState) -> AgentState:
    """知识库检索节点 —— 根据用户问题检索相关知识

    适用于 inquiry 和 complaint 类意图，从知识库中获取相关信息。

    Args:
        state: 当前图状态

    Returns:
        更新后的图状态（含检索到的知识内容）
    """
    logger.info("[RETRIEVE] 进入知识库检索节点...")  # 记录日志

    # 获取最后一条用户消息作为检索查询
    user_message = state["messages"][-1].content if state["messages"] else ""

    # 调用检索工具获取相关知识
    retrieved_docs = retrieve_knowledge(query=user_message, top_k=3)  # 检索 top 3 相关知识

    # 拼接检索结果为文本
    context = "\n\n---\n\n".join(retrieved_docs) if retrieved_docs else "暂无相关知识库内容。"

    logger.info(f"[RETRIEVE] 检索到 {len(retrieved_docs)} 条相关知识")  # 记录检索结果数量
    return {
        **state,  # 保留原有状态
        "retrieved_context": context,  # 更新检索内容
        "current_step": "retrieve_knowledge",  # 更新当前步骤
    }


def generate_response_node(state: AgentState) -> AgentState:
    """回复生成节点 —— 综合上下文和意图，生成最终回复

    利用意图识别结果、知识库内容和对话历史，生成专业的客服回复。

    Args:
        state: 当前图状态

    Returns:
        更新后的图状态（含 AI 回复消息）
    """
    logger.info("[REPLY] 进入回复生成节点...")  # 记录日志

    llm = get_llm()  # 获取 LLM 实例

    # 获取用户最后一条消息
    user_message = state["messages"][-1].content if state["messages"] else ""

    # 构建对话历史文本（排除最后一条用户消息，因为它单独传递）
    history_messages = state["messages"][:-1] if len(state["messages"]) > 1 else []
    chat_history = "\n".join(
        f"{'用户' if isinstance(m, HumanMessage) else '客服'}: {m.content}"
        for m in history_messages[-10:]  # 只取最近 10 条历史，防止过长
    )

    # 构建生成提示
    prompt = RESPONSE_GENERATION_PROMPT.format(
        retrieved_context=state["retrieved_context"] or "暂无相关知识库内容。",
        chat_history=chat_history or "暂无历史对话。",
        user_message=user_message,
    )

    # 调用 LLM 生成回复
    response = llm.invoke(prompt)  # 同步调用，生成回复
    reply_text = response.content.strip()  # 提取回复文本

    logger.info(f"[OK] 回复生成完成，长度: {len(reply_text)} 字符")  # 记录生成结果
    return {
        **state,  # 保留原有状态
        "messages": [AIMessage(content=reply_text)],  # 将 AI 回复追加到消息列表
        "current_step": "generate_response",  # 更新当前步骤
    }


def human_service_node(state: AgentState) -> AgentState:
    """人工客服节点 —— 标记需要转人工，并生成提示消息

    当意图识别为需要转人工、或客服 Agent 信心不足时进入此节点。

    Args:
        state: 当前图状态

    Returns:
        更新后的图状态（标记转人工，生成过渡话术）
    """
    logger.info("[HUMAN] 进入人工客服节点...")  # 记录日志

    # 转人工过渡话术
    human_message = (
        "感谢您的耐心等待。您的问题我已记录下来，正在为您转接人工客服，"
        "请稍候。在线客服会在工作时间内尽快回复您。"
    )

    return {
        **state,  # 保留原有状态
        "requires_human": True,  # 标记需要转人工
        "messages": [AIMessage(content=human_message)],  # 追加过渡消息
        "current_step": "human_service",  # 更新当前步骤
    }


def direct_response_node(state: AgentState) -> AgentState:
    """直接回复节点 —— 处理简单问候或闲聊，无需检索知识库

    适用于 general 意图，直接生成友好的闲聊回复。

    Args:
        state: 当前图状态

    Returns:
        更新后的图状态（含 AI 回复消息）
    """
    logger.info("[REPLY] 进入直接回复节点...")  # 记录日志

    llm = get_llm()  # 获取 LLM 实例

    # 获取用户消息
    user_message = state["messages"][-1].content if state["messages"] else ""

    # 简单问候类提示
    greeting_prompt = f"""你是一个友好的客服助手。用户发来了一条消息，请给出简洁友好的回复。

用户消息: {user_message}

客服回复:"""

    # 调用 LLM 生成回复
    response = llm.invoke(greeting_prompt)
    reply_text = response.content.strip()

    logger.info(f"[OK] 直接回复完成，长度: {len(reply_text)} 字符")
    return {
        **state,  # 保留原有状态
        "messages": [AIMessage(content=reply_text)],  # 追加 AI 回复
        "current_step": "direct_response",  # 更新当前步骤
    }
