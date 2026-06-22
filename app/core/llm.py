"""
LLM 实例化模块
支持任意 OpenAI 兼容协议的 API，如 DeepSeek / 百炼 / OpenAI 等
"""
from langchain_openai import ChatOpenAI  # 使用 OpenAI 兼容协议接入
from app.core.config import get_settings  # 导入全局配置


def get_llm() -> ChatOpenAI:
    """创建并返回 LLM 实例

    通过 OpenAI 兼容协议接入，支持 DeepSeek / 百炼 / OpenAI 等任意兼容端点。
    base_url 和 api_key 均可通过 .env 配置切换。
    """
    settings = get_settings()  # 获取全局配置

    # 创建 LLM 实例，使用配置的 base_url 和 api_key
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,  # 使用的模型名称
        temperature=settings.LLM_TEMPERATURE,  # 温度参数控制创造性
        max_tokens=settings.LLM_MAX_TOKENS,  # 限制最大输出 Token
        api_key=settings.LLM_API_KEY,  # Chat 模型 API Key
        base_url=settings.LLM_BASE_URL,  # OpenAI 兼容端点地址
    )
    return llm  # 返回 LLM 实例
