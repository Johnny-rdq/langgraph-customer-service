import logging
import re
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


def query_mock_db(order_id: str) -> str:
    """模拟物流数据库"""
    if not order_id:
        return "系统提示：用户未提供订单号，请在回复中礼貌地询问用户具体的订单号（如：123456）。"

    mock_db = {
        "123456": "【顺丰速运】包裹已到达北京市朝阳区运转中心，正在派件中，派件员电话 13800000000。",
        "654321": "【京东物流】包裹已发货，目前在深圳市宝安区揽收中。"
    }
    return mock_db.get(order_id, f"系统提示：抱歉，未在系统中查到订单 {order_id} 的物流信息，请安抚用户并建议核对单号。")


async def handle_logistics_intent(user_message: str, llm: BaseChatModel) -> str:
    # 🎯 极其重要的本地调试打印，帮我们死死盯住运行进度
    print("\n▶️ [DEBUG-1] 已经成功进入 handle_logistics_intent 工具函数！")

    try:
        # 🛡️ 策略一：绝招！先用纯 Python 正则表达式提取数字（速度快 100 倍，且绝对不卡死）
        print("🔍 [DEBUG-2] 正在尝试使用正则表达式提取数字...")
        digits = re.findall(r'\d+', user_message)

        if digits:
            order_id = digits[0]
            print(f"🎯 [DEBUG-3] 成功！通过正则直接抓取到订单号: '{order_id}'，跳过大模型网络请求！")
            return query_mock_db(order_id)

        # 🛡️ 策略二：如果句子里没数字（比如“帮我查下快递”），走最基本的 ainvoke，废除容易死锁的 structured_output
        print("📝 [DEBUG-4] 句子里没有纯数字，正在向大模型发起基础异步请求...")

        prompt = f"请从用户的这句话中找出订单号，只输出订单号数字，不要有任何其他字符。如果没有找到订单号，请只输出'无'。用户的话：'{user_message}'"

        # 使用你最稳定的聊天接口，绝不搞花里胡哨的封装
        response = await llm.ainvoke(prompt)

        ans = response.content.strip()
        print(f"🤖 [DEBUG-5] 大模型响应成功！返回的原始文本为: '{ans}'")

        if "无" in ans or not ans:
            print("⚠️ [DEBUG-6] 大模型判定用户没有提供订单号。")
            return query_mock_db("")

        # 再次清洗大模型返回的数字
        clean_digits = re.findall(r'\d+', ans) # 提取订单号
        order_id = clean_digits[0] if clean_digits else "" # 获取订单号
        print(f"🎯 [DEBUG-7] 从大模型回复中清洗出订单号: '{order_id}'")
        return query_mock_db(order_id) # 根据订单号查询物流信息

    except Exception as e:
        print(f"❌ [DEBUG-ERROR] 物流工具内部发生惨烈崩溃: {e}")
        return "系统提示：物流查询系统暂时异常，请稍后再试。"