"""
LLM 实例化模块
接入阿里云百炼 (DashScope) 模型，提供统一的 LLM 调用接口
"""
from langchain_openai import ChatOpenAI  # 百炼兼容 OpenAI 协议，使用 langchain_openai 接入
from app.core.config import get_settings  # 导入全局配置


def get_llm() -> ChatOpenAI:
    """创建并返回阿里云百炼 LLM 实例

    百炼平台提供 OpenAI 兼容的 API 端点，因此可以直接使用 ChatOpenAI 接入。
    支持的模型: qwen-max, qwen-plus, qwen-turbo, qwen2.5-72b-instruct 等
    """
    settings = get_settings()  # 获取全局配置

    # 创建 LLM 实例，对接百炼兼容端点
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,  # 使用的百炼模型名称
        temperature=settings.LLM_TEMPERATURE,  # 温度参数控制创造性
        max_tokens=settings.LLM_MAX_TOKENS,  # 限制最大输出 Token
        api_key=settings.DASHSCOPE_API_KEY,  # 百炼 API Key
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 百炼 OpenAI 兼容端点
    )
    return llm  # 返回 LLM 实例
