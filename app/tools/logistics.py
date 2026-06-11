"""
物流查询工具模块
基于 JSON 格式加载数据，极致稳定
"""
import logging
import json
import re
from pathlib import Path
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)

def _load_logistics_db() -> dict:
    file_path = Path(__file__).resolve().parent.parent.parent / "data" / "logistics_data.json"
    if not file_path.exists():
        logger.warning("找不到 logistics_data.json 文件")
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"读取物流 JSON 失败: {e}")
        return {}

MOCK_LOGISTICS_DB = _load_logistics_db()

def handle_logistics_intent(user_message: str, llm: BaseChatModel = None) -> str:
    """绝对安全的物流查询逻辑（纯同步，兼容 LangGraph 同步图调用）"""
    try:
        # 1. 提取连续数字
        digits_list = re.findall(r'\d{5,}', user_message)

        if not digits_list:
            return "系统提示：用户未提供有效的订单号，请礼貌地询问具体的单号。"

        target_id = digits_list[0]

        # 2. 直接去字典里取，取不到就是没有
        result = MOCK_LOGISTICS_DB.get(target_id)

        if result:
            return result
        else:
            return f"系统提示：在系统中未查到单号为 {target_id} 的物流信息，请建议用户核对单号。"

    except Exception as e:
        logger.error(f"物流工具内部异常: {e}")
        return "系统提示：物流系统异常，请致歉并建议稍后重试。"