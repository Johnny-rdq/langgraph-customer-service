import { useState, useCallback, useEffect } from 'react'  // React Hooks
import Sidebar from './components/Sidebar.jsx'   // 侧边栏组件
import ChatArea from './components/ChatArea.jsx'  // 主聊天区域组件

// 后端 API 基础地址
const API_BASE = '/api/v1/sessions'

export default function App() {
  // 状态管理
  const [sessions, setSessions] = useState([])  // 会话列表（从后端加载）
  const [activeSessionId, setActiveSessionId] = useState(null)  // 当前活跃会话 ID
  const [activeMessages, setActiveMessages] = useState([])  // 当前活跃会话的消息列表
  const [messagesLoading, setMessagesLoading] = useState(false)  // 消息加载中（切会话时显示加载动画，避免闪现欢迎页）
  const [loading, setLoading] = useState(true)  // 首次加载状态

  // 页面初始化：从后端加载会话列表
  useEffect(() => {
    loadSessions()  // 只执行一次
  }, [])

  const loadSessions = async () => {
    try {
      setLoading(true)  // 开始加载
      const res = await fetch(API_BASE)  // GET /api/v1/sessions/
      if (!res.ok) throw new Error('加载会话失败')
      const data = await res.json()  // 解析后端返回的 JSON
      setSessions(data)  // 更新会话列表
      // 自动选中第一个会话
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id)  // 选中第一个
      }
    } catch (err) {
      console.error('加载会话列表失败:', err)
    } finally {
      setLoading(false)  // 加载完成
    }
  }

  // 切换会话时：清空旧消息 → 显示加载 → 异步加载新消息
  useEffect(() => {
    if (!activeSessionId) {
      setActiveMessages([])  // 无选中会话
      return
    }
    setActiveMessages([])  // 清空旧消息
    setMessagesLoading(true)  // 标记加载中，ChatArea 显示加载动画而非欢迎页
    loadMessages(activeSessionId)  // 异步拉取
  }, [activeSessionId])

  const loadMessages = async (sessionId) => {
    try {
      const res = await fetch(`${API_BASE}/${sessionId}/messages`)  // GET
      if (!res.ok) throw new Error('加载消息失败')
      const data = await res.json()
      setActiveMessages(data)
    } catch (err) {
      console.error('加载消息失败:', err)
      setActiveMessages([])
    } finally {
      setMessagesLoading(false)  // 加载完成，关闭加载动画
    }
  }

  // 创建新会话
  const handleNewChat = useCallback(async () => {
    try {
      const res = await fetch(API_BASE, { method: 'POST' })  // POST /api/v1/sessions/
      if (!res.ok) throw new Error('创建会话失败')
      const newSession = await res.json()  // 解析新建的会话
      setActiveMessages([])  // 必须在 setActiveSessionId 之前清空，React 18 会批量合并到同一帧渲染
      setSessions((prev) => [newSession, ...prev])  // 插入到列表顶部
      setActiveSessionId(newSession.id)  // 切换到新会话
    } catch (err) {
      console.error('创建会话失败:', err)
    }
  }, [])

  // 切换会话：先同步清空消息再切 ID，避免渲染时闪现旧会话内容
  const handleSelectSession = useCallback((id) => {
    if (id === activeSessionId) return  // 点同一个会话不操作
    setActiveMessages([])  // 先清空，确保 ChatArea 重挂载时拿到的 messages 是空数组
    setActiveSessionId(id)  // 再切 ID，useEffect 自动触发 loadMessages
  }, [activeSessionId])

  // 删除会话
  const handleDeleteSession = useCallback(
    async (id) => {
      try {
        const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' })  // DELETE
        if (!res.ok) throw new Error('删除失败')
        const updated = sessions.filter((s) => s.id !== id)  // 从列表中移除
        setSessions(updated)  // 更新列表
        if (id === activeSessionId) {  // 如果删除的是当前会话
          setActiveSessionId(updated.length > 0 ? updated[0].id : null)  // 选第一个或清空
        }
      } catch (err) {
        console.error('删除会话失败:', err)
      }
    },
    [sessions, activeSessionId]  // 依赖
  )

  // 保存单条消息到后端数据库 + 第一条用户消息自动设为会话标题
  const saveMessage = useCallback(async (sessionId, role, content) => {
    try {
      const res = await fetch(`${API_BASE}/${sessionId}/messages`, {
        method: 'POST',  // POST
        headers: { 'Content-Type': 'application/json' },  // JSON
        body: JSON.stringify({ role, content }),  // 请求体
      })
      if (!res.ok) throw new Error('保存消息失败')

      // 如果是用户消息，取前 30 字自动更新侧边栏标题
      if (role === 'user') {
        const title = content.slice(0, 30) + (content.length > 30 ? '…' : '')  // 截断取前 30 字
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId && s.title === '新对话'
              ? { ...s, title }  // 替换默认标题
              : s  // 其他会话不动
          )
        )
      }

      return await res.json()  // 返回保存结果
    } catch (err) {
      console.error('保存消息失败:', err)
      return null  // 失败返回 null
    }
  }, [])

  // 消息变更回调（useChat 每次有新消息时触发）
  const handleMessagesChange = useCallback(
    (messages) => {
      if (!activeSessionId) return  // 无活跃会话则忽略
      setActiveMessages(messages)  // 更新消息状态
    },
    [activeSessionId]  // 依赖
  )

  // 当前活跃的会话对象
  const activeSession = sessions.find((s) => s.id === activeSessionId) || null

  if (loading) {  // 首次加载中
    return (
      <div className="flex h-screen items-center justify-center bg-surface-950">
        <p className="text-surface-400 text-lg">正在加载会话…</p>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface-950">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
      />

      {/* key 保证切换会话时 ChatArea 完全重新挂载，避免 useChat 闭包残留上一会话的消息 */}
      <ChatArea
        key={activeSessionId || 'new'}
        session={activeSession}
        messages={activeMessages}
        messagesLoading={messagesLoading}
        onMessagesChange={handleMessagesChange}
        onNewChat={handleNewChat}
        onSaveMessage={saveMessage}
      />
    </div>
  )
}