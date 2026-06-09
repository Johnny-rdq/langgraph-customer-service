import { useState } from 'react'                                    // React Hooks
import { Plus, MessageSquare, Trash2, PanelLeftClose, PanelLeft } from 'lucide-react'  // 图标库
import clsx from 'clsx'                                                // 条件类名工具

export default function Sidebar({
  sessions,            // 会话列表数组
  activeSessionId,     // 当前活跃会话 ID
  onNewChat,           // 新建会话回调
  onSelectSession,     // 选择会话回调
  onDeleteSession,     // 删除会话回调
}) {
  // 侧边栏是否折叠
  const [collapsed, setCollapsed] = useState(false)

  return (
    <>
      {/* 侧边栏主体 */}
      <aside
        className={clsx(
          'flex flex-col bg-surface-900 border-r border-surface-700/50 transition-all duration-200',
          collapsed ? 'w-0 overflow-hidden border-r-0' : 'w-64 min-w-[220px]'
        )}
      >
        {/* 顶部：新建对话按钮 */}
        <div className="p-3">
          <button
            onClick={onNewChat}
            className="flex items-center gap-2 w-full px-3 py-2.5 rounded-lg
                       bg-surface-800 hover:bg-surface-700 text-white text-sm
                       border border-surface-700/50 transition-colors"
          >
            <Plus size={16} />
            <span>新对话</span>
          </button>
        </div>

        {/* 中间：会话列表 */}
        <div className="flex-1 overflow-y-auto px-2 pb-2">
          {sessions.length === 0 ? (
            // 空状态
            <p className="text-surface-200 text-xs text-center mt-8 px-4">
              暂无对话记录，点击上方按钮开始新的对话
            </p>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => onSelectSession(session.id)}
                className={clsx(
                  'group flex items-center gap-2 px-3 py-2.5 mb-0.5 rounded-lg cursor-pointer transition-colors text-sm',
                  session.id === activeSessionId
                    ? 'bg-surface-700 text-white'          // 选中状态
                    : 'text-surface-200 hover:bg-surface-800 hover:text-white'  // 默认/悬停
                )}
              >
                {/* 对话图标 */}
                <MessageSquare size={14} className="shrink-0 text-surface-400" />
                {/* 对话标题 */}
                <span className="flex-1 truncate">{session.title}</span>
                {/* 删除按钮（悬停显示） */}
                <button
                  onClick={(e) => {
                    e.stopPropagation()                           // 阻止冒泡，不触发选中
                    onDeleteSession(session.id)
                  }}
                  className="shrink-0 opacity-0 group-hover:opacity-100 p-0.5 rounded
                             hover:bg-surface-600 text-surface-400 hover:text-red-400 transition-all"
                  title="删除对话"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>

        {/* 底部：项目信息 */}
        <div className="p-3 border-t border-surface-700/50">
          <p className="text-surface-400 text-xs text-center truncate">
            🤖 LangGraph 智能客服
          </p>
        </div>
      </aside>

      {/* 折叠/展开按钮（贴在侧边栏右边） */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className={clsx(
          'absolute top-3 z-10 p-1.5 rounded-md bg-surface-800 hover:bg-surface-700',
          'text-surface-400 hover:text-white border border-surface-700/50 transition-all',
          collapsed ? 'left-2' : 'left-[268px]'  // 跟随侧边栏位置
        )}
        title={collapsed ? '展开侧边栏' : '折叠侧边栏'}
      >
        {collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
      </button>
    </>
  )
}
