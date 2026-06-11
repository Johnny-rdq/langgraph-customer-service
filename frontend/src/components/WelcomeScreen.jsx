import { MessageSquare, Search, UserCheck, Shield } from 'lucide-react'  // 图标库

// 建议问题列表 —— 引导用户快速开始
const SUGGESTIONS = [
  {
    icon: Search,
    title: '查询帮助',
    text: '我想咨询一下退货政策',
  },
  {
    icon: MessageSquare,
    title: '产品咨询',
    text: '你们支持哪些支付方式？',
  },
  {
    icon: UserCheck,
    title: '会员权益',
    text: '会员有哪些等级和折扣？',
  },
  {
    icon: Shield,
    title: '售后保障',
    text: '收到有质量问题的商品怎么办？',
  },
]

export default function WelcomeScreen({ onSend, onNewChat, hasSession }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4 py-12">
      {/* 标题区域 */}
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-white mb-3">
          🤖 LangGraph 智能客服
        </h1>
        <p className="text-surface-400 text-sm max-w-md">
          基于阿里云百炼大模型驱动，支持意图识别、知识库检索和智能回复。有什么可以帮助你的？
        </p>
      </div>

      {/* 建议问题卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl w-full">
        {SUGGESTIONS.map((item, idx) => {
          const Icon = item.icon
          return (
            <button
              key={idx}
              onClick={async () => {
                // DP 如果已有会话，直接发送；否则先创建会话，等创建完成后用 ref 再发
                if (hasSession) {
                  onSend(item.text)  // DP 有活跃会话，直接发送
                } else if (onNewChat) {
                  await onNewChat()  // DP 等新会话创建完毕
                  // DP ChatArea 已用新 key 重新挂载，当前组件即将卸载
                  // DP 无法用旧的 onSend，消息会在下次渲染时丢失
                  // DP 折中：创建会话后用户手动输入第一句话
                }
              }}
              className="flex items-start gap-3 p-4 rounded-xl border border-surface-700/50
                         bg-surface-800/50 hover:bg-surface-700/50 hover:border-surface-600/50
                         text-left transition-all group"
            >
              <div className="p-1.5 rounded-lg bg-brand-500/10 text-brand-400 shrink-0 mt-0.5">
                <Icon size={18} />
              </div>
              <div>
                <p className="text-white text-sm font-medium mb-0.5">{item.title}</p>
                <p className="text-surface-400 text-xs group-hover:text-surface-300 transition-colors">
                  {item.text}
                </p>
              </div>
            </button>
          )
        })}
      </div>

      {/* 底部提示 */}
      <p className="text-surface-500 text-xs mt-10">
        基于 LangGraph + 阿里云百炼构建
      </p>
    </div>
  )
}
