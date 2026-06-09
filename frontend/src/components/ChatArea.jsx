import { useEffect, useRef } from 'react'                       // React Hooks
import { Bot } from 'lucide-react'                              // 图标
import MessageItem from './MessageItem.jsx'                      // 消息条目组件
import ChatInput from './ChatInput.jsx'                          // 输入框组件
import WelcomeScreen from './WelcomeScreen.jsx'                  // 欢迎页组件
import useChat from '../hooks/useChat.js'                        // 聊天逻辑 Hook

export default function ChatArea({ session, onMessagesChange, onNewChat }) {
  // ── 使用聊天 Hook ──
  const {
    messages,
    streamingContent,
    isLoading,
    isStreaming,
    sendMessage,
  } = useChat(session?.messages || [], onMessagesChange)

  // ── 消息列表底部引用（自动滚动用）──
  const bottomRef = useRef(null)

  // ── 新消息 / 流式文字更新时自动滚动到底部 ──
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent, isLoading])

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full">
      {/* 消息区域 */}
      <div className="flex-1 overflow-y-auto">
        {!session || messages.length === 0 ? (
          /* 没有会话或消息为空时显示欢迎页 */
          <WelcomeScreen onSend={sendMessage} onNewChat={onNewChat} />
        ) : (
          <div className="max-w-4xl mx-auto">
            {/* 已完成的消息列表 */}
            {messages.map((msg, idx) => (
              <MessageItem
                key={msg.id}
                message={msg}
                isLast={idx === messages.length - 1 && !isStreaming}
              />
            ))}

            {/* 流式输出中的 AI 消息（正在逐字出现） */}
            {isStreaming && (
              <div className="flex gap-3 px-4 py-4">
                {/* AI 头像 */}
                <div className="shrink-0 w-8 h-8 rounded-full bg-surface-700 flex items-center justify-center">
                  <Bot size={16} className="text-surface-300" />
                </div>
                <div className="max-w-[75%]">
                  <p className="text-xs font-medium mb-1 text-surface-400">智能客服</p>
                  {/* 流式气泡：内容逐字出现 + 尾部闪烁光标 */}
                  <div className="message-content text-sm text-white leading-relaxed whitespace-pre-wrap break-words px-4 py-2.5 rounded-2xl rounded-tl-sm bg-surface-700">
                    {streamingContent}
                    <span className="inline-block w-0.5 h-4 bg-brand-400 ml-0.5 align-text-bottom animate-pulse" />
                  </div>
                </div>
              </div>
            )}

            {/* 加载状态 —— 还没开始流式输出时显示抖动圆点 */}
            {isLoading && !isStreaming && (
              <div className="flex gap-3 px-4 py-4">
                <div className="shrink-0 w-8 h-8 rounded-full bg-surface-700 flex items-center justify-center">
                  <Bot size={16} className="text-surface-300" />
                </div>
                <div className="max-w-[75%]">
                  <p className="text-xs font-medium mb-1 text-surface-400">智能客服</p>
                  <div className="flex gap-1.5 px-4 py-3 rounded-2xl rounded-tl-sm bg-surface-700">
                    <span className="typing-dot w-2 h-2 rounded-full bg-surface-400" />
                    <span className="typing-dot w-2 h-2 rounded-full bg-surface-400" />
                    <span className="typing-dot w-2 h-2 rounded-full bg-surface-400" />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 自动滚动锚点 */}
        <div ref={bottomRef} />
      </div>

      {/* 底部输入框 */}
      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  )
}
