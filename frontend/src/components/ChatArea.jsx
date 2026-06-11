import { useEffect, useRef } from 'react'                       // DP React Hooks
import { Bot } from 'lucide-react'                              // DP 图标库
import MessageItem from './MessageItem.jsx'                      // DP 消息条目组件
import ChatInput from './ChatInput.jsx'                          // DP 输入框组件
import WelcomeScreen from './WelcomeScreen.jsx'                  // DP 欢迎页组件
import useChat from '../hooks/useChat.js'                        // DP 聊天逻辑 Hook

export default function ChatArea({ session, messages, onMessagesChange, onNewChat, onSaveMessage }) {
  // DP ── 使用聊天 Hook（传入外部 messages，不再从 session 对象读）──
  const {
    messages: hookMessages,  // DP useChat 内部维护的消息列表
    streamingContent,  // DP 正在流式输出的文字（实时更新）
    isLoading,  // DP 是否正在等待/接收回复
    isStreaming,  // DP 是否正在流式输出中
    sendMessage,  // DP 发送消息函数
  } = useChat(session?.id, messages, onMessagesChange, onSaveMessage)  // DP 绑定外部回调

  // DP ── 消息列表底部引用（自动滚动用）──
  const bottomRef = useRef(null)

  // DP ── 新消息 / 流式文字更新时自动滚动到底部 ──
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })  // DP 平滑滚动
  }, [hookMessages, streamingContent, isLoading])  // DP 消息/流式/加载状态变化时触发

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full">
      {/* DP 消息区域 */}
      <div className="flex-1 overflow-y-auto">
        {!session || hookMessages.length === 0 ? (
          /* DP 没有会话或消息为空时显示欢迎页 */
          <WelcomeScreen onSend={sendMessage} onNewChat={onNewChat} />
        ) : (
          <div className="max-w-4xl mx-auto">
            {/* DP 已完成的消息列表 */}
            {hookMessages.map((msg, idx) => (
              <MessageItem
                key={msg.id}  {/* DP 消息唯一 key */}
                message={msg}  {/* DP 消息对象 */}
                isLast={idx === hookMessages.length - 1 && !isStreaming}  {/* DP 是否最后一条 */}
              />
            ))}

            {/* DP 流式输出中的 AI 消息（正在逐字出现） */}
            {isStreaming && (
              <div className="flex gap-3 px-4 py-4">
                {/* DP AI 头像 */}
                <div className="shrink-0 w-8 h-8 rounded-full bg-surface-700 flex items-center justify-center">
                  <Bot size={16} className="text-surface-300" />
                </div>
                <div className="max-w-[75%]">
                  <p className="text-xs font-medium mb-1 text-surface-400">DP 智能客服</p>
                  {/* DP 流式气泡：内容逐字出现 + 尾部闪烁光标 */}
                  <div className="message-content text-sm text-white leading-relaxed whitespace-pre-wrap break-words px-4 py-2.5 rounded-2xl rounded-tl-sm bg-surface-700">
                    {streamingContent}  {/* DP 流式输出中的文字 */}
                    <span className="inline-block w-0.5 h-4 bg-brand-400 ml-0.5 align-text-bottom animate-pulse" />  {/* DP 闪烁光标 */}
                  </div>
                </div>
              </div>
            )}

            {/* DP 加载状态 —— 还没开始流式输出时显示抖动圆点 */}
            {isLoading && !isStreaming && (
              <div className="flex gap-3 px-4 py-4">
                {/* DP AI 头像 */}
                <div className="shrink-0 w-8 h-8 rounded-full bg-surface-700 flex items-center justify-center">
                  <Bot size={16} className="text-surface-300" />
                </div>
                <div className="max-w-[75%]">
                  <p className="text-xs font-medium mb-1 text-surface-400">DP 智能客服</p>
                  {/* DP 加载中的跳动圆点动画 */}
                  <div className="flex gap-1.5 px-4 py-3 rounded-2xl rounded-tl-sm bg-surface-700">
                    <span className="typing-dot w-2 h-2 rounded-full bg-surface-400" />  {/* DP 圆点 1 */}
                    <span className="typing-dot w-2 h-2 rounded-full bg-surface-400" />  {/* DP 圆点 2 */}
                    <span className="typing-dot w-2 h-2 rounded-full bg-surface-400" />  {/* DP 圆点 3 */}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* DP 自动滚动锚点 */}
        <div ref={bottomRef} />
      </div>

      {/* DP 底部输入框 */}
      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  )
}