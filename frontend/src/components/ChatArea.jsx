import { useEffect, useRef } from 'react'                       // React Hooks
import { Bot } from 'lucide-react'                              // 图标库
import MessageItem from './MessageItem.jsx'                      // 消息条目组件
import ChatInput from './ChatInput.jsx'                          // 输入框组件
import WelcomeScreen from './WelcomeScreen.jsx'                  // 欢迎页组件
import useChat from '../hooks/useChat.js'                        // 聊天逻辑 Hook

export default function ChatArea({ session, messages, messagesLoading, onMessagesChange, onNewChat, onSaveMessage }) {
  const {
    messages: hookMessages,
    streamingContent,
    isLoading,
    isStreaming,
    sendMessage,
  } = useChat(session?.id, messages, onMessagesChange, onSaveMessage)

  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [hookMessages, streamingContent, isLoading])

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full">
      <div className="flex-1 overflow-y-auto">

        {/* 切换会话加载中：显示过渡动画，避免闪现欢迎页 */}
        {messagesLoading && session ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="flex gap-1.5 mb-3">
              <span className="typing-dot w-2.5 h-2.5 rounded-full bg-brand-400" />
              <span className="typing-dot w-2.5 h-2.5 rounded-full bg-brand-400" />
              <span className="typing-dot w-2.5 h-2.5 rounded-full bg-brand-400" />
            </div>
            <p className="text-surface-400 text-sm">加载会话中…</p>
          </div>
        ) : !session || hookMessages.length === 0 ? (
          <WelcomeScreen onSend={sendMessage} onNewChat={onNewChat} hasSession={!!session} />
        ) : (
          <div className="max-w-4xl mx-auto">
            {hookMessages.map((msg, idx) => (
              <MessageItem
                key={msg.id}
                message={msg}
                isLast={idx === hookMessages.length - 1 && !isStreaming}
              />
            ))}

            {isStreaming && (
              <div className="flex gap-3 px-4 py-4">
                <div className="shrink-0 w-8 h-8 rounded-full bg-surface-700 flex items-center justify-center">
                  <Bot size={16} className="text-surface-300" />
                </div>
                <div className="max-w-[75%]">
                  <p className="text-xs font-medium mb-1 text-surface-400">智能客服</p>
                  <div className="message-content text-sm text-white leading-relaxed whitespace-pre-wrap break-words px-4 py-2.5 rounded-2xl rounded-tl-sm bg-surface-700">
                    {streamingContent}
                    <span className="inline-block w-0.5 h-4 bg-brand-400 ml-0.5 align-text-bottom animate-pulse" />
                  </div>
                </div>
              </div>
            )}

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

        <div ref={bottomRef} />
      </div>

      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  )
}