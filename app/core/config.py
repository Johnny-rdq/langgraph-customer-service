"""
核心配置模块
负责读取 .env 环境变量与全局配置，统一管理所有配置项
"""
from pydantic_settings import BaseSettings  # pydantic-settings 提供从 .env 自动加载配置的能力
from functools import lru_cache  # 缓存配置对象，避免重复读取


class Settings(BaseSettings):
    """全局配置类 —— 所有配置项从此处统一获取"""

    # ── LLM Chat 模型配置（支持任意 OpenAI 兼容的 API，如 DeepSeek / 百炼 / OpenAI）──
    LLM_API_KEY: str = ""  # Chat 模型的 API Key
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # OpenAI 兼容端点地址
    LLM_MODEL: str = "deepseek-chat"  # 使用的模型名称，deepseek-chat 为 DeepSeek 最便宜文本模型
    LLM_TEMPERATURE: float = 0.7  # LLM 温度参数，控制回复的随机性
    LLM_MAX_TOKENS: int = 2048  # LLM 最大输出 Token 数

    # ── Embedding 模型配置（用于向量检索，独立于 Chat 模型）──
    DASHSCOPE_API_KEY: str = ""  # 阿里云百炼 API Key，Embedding 模型 text-embedding-v2 使用

    # ── 服务配置 ──
    APP_NAME: str = "LangGraph 智能客服系统"  # 应用名称，用于日志和文档展示
    APP_HOST: str = "0.0.0.0"  # FastAPI 服务绑定地址
    APP_PORT: int = 8000  # FastAPI 服务端口
    DEBUG: bool = True  # 调试模式开关

    # ── 知识库配置 ──
    KNOWLEDGE_BASE_PATH: str = "data/knowledge_base.txt"  # 本地知识库文件路径

    # ── 对话配置 ──
    MAX_HISTORY_LENGTH: int = 20  # 最大保留对话轮数，防止上下文过长

    # ── 人工客服配置 ──
    HUMAN_SERVICE_THRESHOLD: float = 0.5  # 转人工的置信度阈值，低于此值则转人工

    class Config:
        env_file = ".env"  # 自动从 .env 文件加载环境变量
        env_file_encoding = "utf-8"  # .env 文件编码格式


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例（带缓存）

    多次调用返回同一个对象，避免反复读取文件
    """
    return Settings()  # 实例化配置对象
