"""DP 物流查询工具模块
DP 提供订单号提取 + 物流轨迹查询功能。
DP 物流数据从 data/logistics_data.txt 文件加载，只建单一订单号索引。
DP 查询时用滑动窗口匹配：对用户输入中的数字串，尝试直接匹配 + 长短截取。
"""
import logging  # 日志模块
import re  # 正则表达式提取订单号
from pathlib import Path  # 跨平台文件路径处理
from langchain_core.language_models.chat_models import BaseChatModel  # LLM 基类类型标注

logger = logging.getLogger(__name__)  # 当前模块日志记录器


def _load_logistics_db() -> dict:
    """DP 从 data/logistics_data.txt 加载物流模拟数据库（只建单一订单号索引）

    DP 不再建副索引，把运单号→订单号的转换逻辑放到查询时处理。

    Returns:
        DP dict: {订单号: 物流轨迹文本}
    """
    db = {}  # 订单号 → 物流信息的映射
    file_path = Path(__file__).resolve().parent.parent.parent / "data" / "logistics_data.txt"  # 数据文件路径

    if not file_path.exists():  # 文件不存在时返回空库
        logger.warning(f"物流数据文件不存在: {file_path}")
        return db

    try:
        with open(file_path, "r", encoding="utf-8") as f:  # UTF-8 读取
            for raw_line in f:
                line = raw_line.strip()  # 去首尾空白
                if not line or line.startswith("#"):  # 跳过空行和注释行
                    continue
                if "|" not in line:  # 跳过格式不正确的行
                    continue
                parts = line.split("|", 1)  # 按第一个 | 分割
                if len(parts) != 2:
                    continue
                order_id = parts[0].strip()  # 订单号（如 112233）
                info = parts[1].strip()  # 物流轨迹文本
                if order_id and info:  # 双方都非空才入库
                    db[order_id] = info  # 只建单一索引：订单号 → 物流信息
        logger.info(f"物流数据加载完成: 共 {len(db)} 条记录")
    except Exception as e:
        logger.error(f"加载物流数据文件失败: {e}")  # 文件读取异常不阻塞服务

    return db


# 全局物流数据库（模块加载时一次性读取，只含订单号索引）
MOCK_LOGISTICS_DB = _load_logistics_db()
# 所有订单号的列表，用于滑动窗口匹配
_ORDER_IDS = list(MOCK_LOGISTICS_DB.keys())


def _match_order(user_message: str) -> str:
    """DP 从用户消息中智能匹配订单号

    DP 匹配策略（按优先级）：
    DP   1. 提取所有数字串，直接查库（如用户输入纯 6 位订单号）
    DP   2. 对长数字串尝试滑窗截取 6 位子串（如运单号 ZT1122334455 → 1122334455 → 窗口匹配 112233）
    DP   3. 用订单号反向匹配：检查消息中是否包含某个已知订单号为子串

    Returns:
        DP 匹配到的订单号，未找到返回空字符串
    """
    digits_list = re.findall(r'\d+', user_message)  # 提取所有连续数字串

    for d in digits_list:
        # 策略一：直接匹配（如 "112233" 正好是订单号）
        if d in MOCK_LOGISTICS_DB:
            logger.info(f"[MATCH] 直接命中订单号: '{d}'")
            return d
        # 策略二：对 ≥6 位数字串，用 6 位滑窗在所有已知订单号中匹配
        if len(d) >= 6:  # 至少 6 位才有可能是运单号
            for window_size in (6, 7, 8):  # 尝试不同窗口（订单号以 6 位为主，兼容不同长度）
                for i in range(len(d) - window_size + 1):  # 滑窗遍历
                    sub = d[i:i + window_size]  # 截取窗口子串
                    if sub in MOCK_LOGISTICS_DB:
                        logger.info(f"[MATCH] 滑窗命中: '{sub}' <- '{d}'[窗口={window_size}, offset={i}]")
                        return sub

    # 策略三：反向匹配 —— 用户消息是否包含已知订单号作为子串
    for oid in _ORDER_IDS:
        if oid in user_message:
            logger.info(f"[MATCH] 反向匹配命中: '{oid}'")
            return oid

    # 全部未命中，返回第一个 5-12 位数字兜底
    for d in digits_list:
        if 5 <= len(d) <= 12:
            logger.info(f"[FALLBACK] 兜底数字: '{d}'（不在库中）")
            return d

    return ""  # 完全没数字


async def handle_logistics_intent(user_message: str, llm: BaseChatModel) -> str:
    """DP 物流查询意图处理（异步）

    DP 先走正则智能匹配（零 LLM 消耗），失败时走 LLM 兜底。

    Args:
        user_message: 用户发送的原始消息文本
        llm: 阿里云百炼 LLM 实例

    Returns:
        DP 物流查询结果文本
    """
    logger.debug("[DEBUG-1] 进入物流查询工具！")  # 使用 logger 避免 Windows GBK 编码问题

    try:
        # ════════════════════════════════════════════════════
        # 策略一：正则智能匹配（零 LLM 消耗）
        # ════════════════════════════════════════════════════
        logger.debug(f"[DEBUG-2] 尝试匹配: '{user_message}'")  # 调试日志
        matched = _match_order(user_message)  # 调用智能匹配函数

        if matched:  # 匹配到了订单号
            logger.debug(f"[DEBUG-3] 匹配结果: '{matched}'")  # 调试日志
            result = MOCK_LOGISTICS_DB.get(matched)  # 查库
            if result:
                return result  # 命中，返回物流信息
            else:
                # 数字存在但不在库中（兜底数字）
                return (
                    f"系统提示：在物流系统中未查到订单号 {matched} 的物流信息。"
                    "请在回复中安抚用户情绪，建议核对订单号是否正确，"
                    "或询问用户是否通过其他渠道（如淘宝/京东平台）下单。"
                    "如确认单号无误，建议用户联系人工客服查询后台详细记录。"
                )

        # ════════════════════════════════════════════════════
        # 策略二：LLM 语义识别（兜底路径）
        # ════════════════════════════════════════════════════
        logger.debug("[DEBUG-4] 正则未命中，调用 LLM 识别...")  # 调试日志

        prompt = (
            "请从用户的这句话中找出订单号，只输出订单号数字，不要有任何其他字符。"
            "如果没有找到订单号，请只输出'无'。"
            f"用户的话：'{user_message}'"
        )

        response = await llm.ainvoke(prompt)  # 异步调用 LLM
        ans = response.content.strip()  # 去空白
        logger.debug(f"[DEBUG-5] LLM 返回: '{ans}'")  # 调试日志

        if "无" in ans or not ans:  # 未识别到订单号
            logger.debug("[DEBUG-6] LLM 判定无订单号")  # 调试日志
            return (
                "系统提示：用户未提供订单号，请在回复中礼貌地询问用户具体的订单号（6位数字，如 123456），"
                "或者请用户提供快递单号（以 SF/JD/YT/ZT/YD 开头）。"
            )

        # LLM 返回的数字也走一遍智能匹配
        llm_digits = re.findall(r'\d+', ans)  # 从 LLM 结果提取数字
        for d in llm_digits:
            if d in MOCK_LOGISTICS_DB:
                logger.debug(f"[DEBUG-7] LLM 提取命中: '{d}'")  # 调试日志
                return MOCK_LOGISTICS_DB[d]
        # 兜底
        order_id = llm_digits[0] if llm_digits else ""
        logger.debug(f"[DEBUG-7] LLM 兜底: '{order_id}'")  # 调试日志
        result = MOCK_LOGISTICS_DB.get(order_id)
        if result:
            return result
        return (
            f"系统提示：在物流系统中未查到订单号 {order_id} 的物流信息。"
            "请在回复中安抚用户情绪，建议核对订单号是否正确。"
        )

    except Exception as e:
        logger.error(f"[DEBUG-ERROR] 物流工具异常: {e}")  # 错误日志
        return "系统提示：物流查询系统暂时繁忙，请在回复中向用户致歉，并建议稍后重试或联系人工客服。"