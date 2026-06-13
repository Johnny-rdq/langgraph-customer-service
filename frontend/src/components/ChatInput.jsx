import { useState, useRef, useEffect } from 'react'  // React Hooks
import { Send, Loader2 } from 'lucide-react'        // 图标
import clsx from 'clsx'                               // 条件类名

export default function ChatInput({ onSend, disabled }) {
  // 输入框内容
  const [input, setInput] = useState('')
  // textarea 引用
  const textareaRef = useRef(null)

  // ── 自动调整 textarea 高度 ──
  const adjustHeight = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'                          // 先重置高度
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'  // 最大 200px
  }

  // 输入变化时调整高度
  useEffect(() => {
    adjustHeight()
  }, [input])

  // 加载完成时自动聚焦
  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [disabled])

  // ── 发送消息 ──
  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || disabled) return  // 空消息或正在加载时不允许发送
    onSend(trimmed)                    // 调用父组件回调
    setInput('')                       // 清空输入框
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'  // 重置高度
      textareaRef.current.focus()
    }
  }

  // ── 键盘事件处理 ──
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()    // 回车发送，Shift+回车换行
      handleSend()
    }
  }

  return (
    <div className="border-t border-surface-700/50 bg-surface-900/80 backdrop-blur-sm">
      <div className="max-w-3xl mx-auto px-4 py-3">
        {/* 输入区域 */}
        <div className="flex items-end gap-2 bg-surface-800 rounded-2xl border border-surface-700/50
                        focus-within:border-brand-500/50 focus-within:ring-1 focus-within:ring-brand-500/20
                        px-4 py-2 transition-all">
          {/* 文本框 */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的问题… (Enter 发送，Shift+Enter 换行)"
            rows={1}
            disabled={disabled}
            className="flex-1 bg-transparent text-white text-sm placeholder-surface-500
                       resize-none outline-none py-1.5 max-h-[200px]"
          />

          {/* 发送按钮或加载指示器 */}
          {disabled ? (
            <div className="shrink-0 p-1.5 text-brand-400 animate-pulse">
              <Loader2 size={18} className="animate-spin" />
            </div>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className={clsx(
                'shrink-0 p-1.5 rounded-lg transition-all',
                input.trim()
                  ? 'bg-brand-500 hover:bg-brand-600 text-white'    // 可发送状态
                  : 'bg-surface-700 text-surface-500 cursor-not-allowed'  // 禁用状态
              )}
            >
              <Send size={16} />
            </button>
          )}
        </div>

        {/* 底部提示 */}
        <p className="text-surface-500 text-[10px] text-center mt-2">
          智能客服可能会产生不准确回复，重要信息请核实。
        </p>
      </div>
    </div>
  )
}
