import { useState, useCallback, useEffect } from 'react'  // React Hooks
import Sidebar from './components/Sidebar.jsx'   // 侧边栏组件
import ChatArea from './components/ChatArea.jsx'  // 主聊天区域组件

// ── 后端 API 基础地址 ──
const API_BASE = '/api/v1/sessions'

export default function App() {
  // ── 状态管理 ──
  const [sessions, setSessions] = useState([])  // 会话列表（来自后端）
  const [activeSessionId, setActiveSessionId] = useState(null)  // 当前活跃会话 ID
  const [activeMessages, setActiveMessages] = useState([])  // 当前活跃会话的消息
  const [loading, setLoading] = useState(true)  // 首次加载状态

  // ── 页面初始化：从后端加载会话列表 ──
  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      setLoading(true)
      const res = await fetch(API_BASE)  // GET /api/v1/sessions/
      if (!res.ok) throw new Error('加载会话失败')
      const data = await res.json()
      setSessions(data)
      // 自动选中第一个会话
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id)
      }
    } catch (err) {
      console.error('加载会话列表失败:', err)
    } finally {
      setLoading(false)
    }
  }

  // ── 切换会话时，从后端加载消息 ──
  useEffect(() => {
    if (!activeSessionId) {
      setActiveMessages([])
      return
    }
    loadMessages(activeSessionId)
  }, [activeSessionId])

  const loadMessages = async (sessionId) => {
    try {
      const res = await fetch(`${API_BASE}/${sessionId}/messages`)  // GET /api/v1/sessions/{id}/messages
      if (!res.ok) throw new Error('加载消息失败')
      const data = await res.json()
      setActiveMessages(data)
    } catch (err) {
      console.error('加载消息失败:', err)
      setActiveMessages([])
    }
  }

  // ── 创建新会话 ──
  const handleNewChat = useCallback(async () => {
    try {
      const res = await fetch(API_BASE, { method: 'POST' })  // POST /api/v1/sessions/
      if (!res.ok) throw new Error('创建会话失败')
      const newSession = await res.json()
      // 插入到列表顶部
      setSessions((prev) => [newSession, ...prev])
      setActiveSessionId(newSession.id)
    } catch (err) {
      console.error('创建会话失败:', err)
    }
  }, [])

  // ── 切换会话 ──
  const handleSelectSession = useCallback((id) => {
    setActiveSessionId(id)  // useEffect 会自动触发 loadMessages
  }, [])

  // ── 删除会话 ──
  const handleDeleteSession = useCallback(
    async (id) => {
      try {
        const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' })  // DELETE /api/v1/sessions/{id}
        if (!res.ok) throw new Error('删除失败')
        const updated = sessions.filter((s) => s.id !== id)
        setSessions(updated)
        // 如果删除的是当前会话，切换到第一个
        if (id === activeSessionId) {
          setActiveSessionId(updated.length > 0 ? updated[0].id : null)
        }
      } catch (err) {
        console.error('删除会话失败:', err)
      }
    },
    [sessions, activeSessionId]
  )

  // ── 保存单条消息到后端 ──
  const saveMessage = useCallback(async (sessionId, role, content) => {
    try {
      const res = await fetch(`${API_BASE}/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, content }),  // JSON body，避免 URL 编码问题
      })
      if (!res.ok) throw new Error('保存消息失败')
      return await res.json()
    } catch (err) {
      console.error('保存消息失败:', err)
      return null
    }
  }, [])

  // ── 更新会话标题 ──
  const updateSessionTitle = useCallback(async (sessionId, title) => {
    try {
      await fetch(
        `${API_BASE}/${sessionId}?title=${encodeURIComponent(title)}`,
        { method: 'PATCH' }
      )
      // 更新本地列表中的标题
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, title } : s))
      )
    } catch (err) {
      console.error('更新标题失败:', err)
    }
  }, [])

  // ── 消息变更回调（useChat 每次有新消息触发）──
  const handleMessagesChange = useCallback(
    async (messages) => {
      if (!activeSessionId) return
      setActiveMessages(messages)

      // 自动更新标题（取第一条用户消息的前 30 字）
      const firstUserMsg = messages.find((m) => m.role === 'user')
      if (firstUserMsg) {
        const currentSession = sessions.find((s) => s.id === activeSessionId)
        if (currentSession && currentSession.title === '新对话') {
          const title = firstUserMsg.content.slice(0, 30) + (firstUserMsg.content.length > 30 ? '…' : '')
          updateSessionTitle(activeSessionId, title)
        }
      }
    },
    [activeSessionId, sessions, updateSessionTitle]
  )

  // ── 构建传给 ChatArea 的 session 对象 ──
  const activeSession = sessions.find((s) => s.id === activeSessionId) || null

  if (loading) {
    // 首次加载中，显示加载状态
    return (
      <div className="flex h-screen items-center justify-center bg-surface-950">
        <p className="text-surface-400 text-lg">正在加载会话…</p>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface-950">
      {/* 侧边栏 */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
      />

      {/* 主聊天区域 */}
      <ChatArea
        session={activeSession}
        messages={activeMessages}
        onMessagesChange={handleMessagesChange}
        onNewChat={handleNewChat}
        onSaveMessage={saveMessage}
      />
    </div>
  )
}
