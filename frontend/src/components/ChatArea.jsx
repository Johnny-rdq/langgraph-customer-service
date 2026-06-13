import { useEffect, useRef } from 'react'
import { Bot, User, LogOut, Sparkles } from 'lucide-react'     // 🌟 引入了更多酷炫图标
import MessageItem from './MessageItem.jsx'
import ChatInput from './ChatInput.jsx'
import WelcomeScreen from './WelcomeScreen.jsx'
import useChat from '../hooks/useChat.js'

export default function ChatArea({ session, messages, messagesLoading, onMessagesChange, onNewChat, onSaveMessage }) {
  const {
    messages: hookMessages,
    streamingContent,
    isLoading,
    isStreaming,
    isHumanMode,      // 🌟 获取人工模式状态
    exitHumanMode,    // 🌟 获取退出函数
    sendMessage,
  } = useChat(session?.id, messages, onMessagesChange, onSaveMessage)

  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [hookMessages, streamingContent, isLoading])

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full relative">

      {/* 🌟 退出人工客服的顶部悬浮横幅 */}
      {isHumanMode && (
        <div className="absolute top-0 left-0 right-0 z-20 bg-brand-500/10 backdrop-blur-md border-b border-brand-500/20 px-4 py-2.5 flex items-center justify-between shadow-lg">
          <span className="text-brand-400 text-sm font-medium flex items-center gap-2">
            <User size={16} className="animate-pulse" />
            您正在与人工客服对话中...
          </span>
          <button
            onClick={exitHumanMode}
            className="flex items-center gap-1.5 text-xs bg-brand-500 hover:bg-brand-600 text-white px-3 py-1.5 rounded-lg transition-all shadow-md hover:shadow-brand-500/30 active:scale-95"
          >
            <LogOut size={14} />
            退出人工客服
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {/* 如果有横幅，给顶部增加一点 padding 避免遮挡消息 */}
        <div className={isHumanMode ? "pt-14 h-full" : "h-full"}>

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
            <div className="max-w-4xl mx-auto pb-4">
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

              {/* 🌟 重新设计的更直观的“AI 思考中”加载动画 */}
              {isLoading && !isStreaming && (
                <div className="flex gap-3 px-4 py-4 animate-in fade-in duration-300">
                  <div className="shrink-0 w-8 h-8 rounded-full bg-brand-500/20 border border-brand-500/30 flex items-center justify-center shadow-[0_0_10px_rgba(249,115,22,0.2)]">
                    <Sparkles size={16} className="text-brand-400 animate-pulse" />
                  </div>
                  <div className="max-w-[75%]">
                    <p className="text-xs font-medium mb-1 text-brand-400/80">智能助手正在思考中...</p>
                    <div className="flex gap-1.5 px-4 py-3 rounded-2xl rounded-tl-sm bg-surface-700/60 border border-surface-600/50 backdrop-blur-sm">
                      <span className="typing-dot w-2 h-2 rounded-full bg-brand-400/80" />
                      <span className="typing-dot w-2 h-2 rounded-full bg-brand-400/80" />
                      <span className="typing-dot w-2 h-2 rounded-full bg-brand-400/80" />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  )
}