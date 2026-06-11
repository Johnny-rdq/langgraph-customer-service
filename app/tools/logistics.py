"""DP 物流查询工具模块
DP 提供订单号提取 + 物流轨迹查询功能。
DP 双策略：先用正则提取数字（快速），失败时走 LLM 兜底识别。
DP 物流数据从 data/logistics_data.txt 文件加载，方便动态扩充。
"""
import logging  # 日志模块
import re  # 正则表达式提取订单号
from pathlib import Path  # 跨平台文件路径处理
from langchain_core.language_models.chat_models import BaseChatModel  # LLM 基类类型标注

logger = logging.getLogger(__name__)  # 当前模块日志记录器

# ═══════════════════════════════════════════════════════════
# 从 data/logistics_data.txt 加载物流模拟数据
# 格式：订单号 | 物流信息，每行一条，支持 # 注释
# ═══════════════════════════════════════════════════════════

def _load_logistics_db() -> dict:
    """DP 从 data/logistics_data.txt 文件加载物流模拟数据库

    DP 文件格式: 每行一条记录，用 | 分隔订单号和物流信息。
    DP 以 # 开头的行视为注释，空行自动跳过。

    Returns:
        DP dict: {订单号: 物流轨迹文本}
    """
    db = {}  # 订单号 → 物流信息的映射
    # 文件路径：项目根目录 / data / logistics_data.txt
    file_path = Path(__file__).resolve().parent.parent.parent / "data" / "logistics_data.txt"

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
                parts = line.split("|", 1)  # 按第一个 | 分割（最多 2 段）
                if len(parts) != 2:
                    continue
                order_id = parts[0].strip()  # 订单号
                info = parts[1].strip()  # 物流轨迹文本
                if order_id and info:  # 双方都非空才入库
                    db[order_id] = info
        logger.info(f"物流数据加载完成: 共 {len(db)} 条记录")
    except Exception as e:
        logger.error(f"加载物流数据文件失败: {e}")  # 文件读取异常不阻塞服务

    return db


# 全局物流数据库（模块加载时一次性读取）
MOCK_LOGISTICS_DB = _load_logistics_db()


def query_mock_db(order_id: str) -> str:
    """DP 根据订单号查询物流数据库

    DP 订单号为空时返回引导话术让客服询问用户。
    DP 订单号不在库中时返回核对建议。

    Args:
        order_id: DP 提取到的订单号（纯数字字符串）

    Returns:
        DP 物流状态文本，供 LLM 嵌入回复使用
    """
    if not order_id:  # 用户未提供订单号
        return (
            "系统提示：用户未提供订单号，请在回复中礼貌地询问用户具体的订单号（6位数字，如 123456），"
            "或者请用户提供快递单号（以 SF/JD/YT/ZT/YD 开头）。"
        )

    result = MOCK_LOGISTICS_DB.get(order_id)  # 查库
    if result:
        return result  # 命中

    # 未命中
    return (
        f"系统提示：在物流系统中未查到订单号 {order_id} 的物流信息。"
        "请在回复中安抚用户情绪，建议核对订单号是否正确，"
        "或询问用户是否通过其他渠道（如淘宝/京东平台）下单。"
        "如确认单号无误，建议用户联系人工客服查询后台详细记录。"
    )


async def handle_logistics_intent(user_message: str, llm: BaseChatModel) -> str:
    """DP 物流查询意图处理（异步）

    DP 双策略提取订单号：
    DP   策略一：正则直接提取数字 —— 零延迟，不消耗 LLM Token
    DP   策略二：LLM 语义识别 —— 兜底处理"帮我查下快递"之类的消息

    Args:
        user_message: 用户发送的原始消息文本
        llm: 阿里云百炼 LLM 实例

    Returns:
        DP 物流查询结果文本
    """
    print("\n▶️ [DEBUG-1] 进入物流查询工具！")

    try:
        # ════════════════════════════════════════════════════
        # 策略一：正则提取数字（快速路径，零 LLM 消耗）
        # ════════════════════════════════════════════════════
        print("🔍 [DEBUG-2] 正则提取数字...")
        digits = re.findall(r'\d+', user_message)  # 匹配所有连续数字

        if digits:
            order_id = digits[0]  # 取第一个数字串
            # 过滤：订单号通常在 5-12 位之间
            if 5 <= len(order_id) <= 12:
                print(f"🎯 [DEBUG-3] 正则命中！订单号: '{order_id}'，跳过 LLM")
                return query_mock_db(order_id)  # 直接查库

        # ════════════════════════════════════════════════════
        # 策略二：LLM 语义识别（兜底路径）
        # ════════════════════════════════════════════════════
        print("📝 [DEBUG-4] 正则未命中，调用 LLM 识别...")

        prompt = (
            "请从用户的这句话中找出订单号，只输出订单号数字，不要有任何其他字符。"
            "如果没有找到订单号，请只输出'无'。"
            f"用户的话：'{user_message}'"
        )

        response = await llm.ainvoke(prompt)  # 异步调用 LLM
        ans = response.content.strip()  # 去空白
        print(f"🤖 [DEBUG-5] LLM 返回: '{ans}'")

        if "无" in ans or not ans:  # 未识别到
            print("⚠️ [DEBUG-6] LLM 判定无订单号")
            return query_mock_db("")

        clean_digits = re.findall(r'\d+', ans)  # 清洗 LLM 回复中的数字
        order_id = clean_digits[0] if clean_digits else ""  # 取第一个
        print(f"🎯 [DEBUG-7] 从 LLM 回复清洗出订单号: '{order_id}'")
        return query_mock_db(order_id)  # 查库

    except Exception as e:
        print(f"❌ [DEBUG-ERROR] 物流工具异常: {e}")
        return "系统提示：物流查询系统暂时繁忙，请在回复中向用户致歉，并建议稍后重试或联系人工客服。"