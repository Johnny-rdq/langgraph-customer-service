import { Bot, User } from 'lucide-react'  // 图标
import clsx from 'clsx'                   // 条件类名

// ── Markdown 简易渲染 ──
// 将纯文本中的 **加粗**、*斜体*、`代码`、换行转为 HTML
function renderText(text) {
  if (!text) return ''
  return (
    text
      // 转义 HTML 实体
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      // 代码块 ```
      .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      // 行内代码 `...`
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      // **加粗**
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      // *斜体*
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      // 换行
      .replace(/\n/g, '<br/>')
  )
}

export default function MessageItem({ message, isLast }) {
  const isUser = message.role === 'user'  // 是否为用户消息

  return (
    <div
      className={clsx(
        'flex gap-3 px-4 py-4',
        isUser
          ? 'flex-row-reverse'              // 用户消息：头像和内容左右颠倒
          : 'flex-row'                       // AI 消息：头像在左，内容在右
      )}
    >
      {/* 头像区域 */}
      <div
        className={clsx(
          'shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isUser
            ? 'bg-brand-500/20 text-brand-400'     // 用户头像：橙色
            : 'bg-surface-700 text-surface-300'     // AI 头像：灰色
        )}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      {/* 消息内容 */}
      <div
        className={clsx(
          'max-w-[75%]',   // 消息最大宽度 75%
          isUser ? 'items-end' : 'items-start'
        )}
      >
        {/* 角色标签 */}
        <p
          className={clsx(
            'text-xs font-medium mb-1 text-surface-400',
            isUser ? 'text-right' : 'text-left'   // 用户标签右对齐
          )}
        >
          {isUser ? '你' : '智能客服'}
        </p>
        {/* 消息气泡 */}
        <div
          className={clsx(
            'message-content text-sm leading-relaxed whitespace-pre-wrap break-words px-4 py-2.5 rounded-2xl',
            isUser
              ? 'bg-brand-600 text-white rounded-tr-sm'           // 用户气泡：橙色，右上直角
              : 'bg-surface-700 text-white rounded-tl-sm'         // AI 气泡：灰色，左上直角
          )}
          dangerouslySetInnerHTML={{ __html: renderText(message.content) }}
        />
      </div>
    </div>
  )
}
