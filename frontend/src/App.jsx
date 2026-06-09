import { useState, useCallback } from 'react'   // React Hooks
import Sidebar from './components/Sidebar.jsx'   // 侧边栏组件
import ChatArea from './components/ChatArea.jsx'  // 主聊天区域组件

// ── 会话管理工具函数 ──
// 生成唯一 ID
const generateId = () => crypto.randomUUID?.() || Math.random().toString(36).slice(2)

// 从 localStorage 加载会话数据
const loadSessions = () => {
  try {
    const raw = localStorage.getItem('chat_sessions')
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

// 保存会话数据到 localStorage
const saveSessions = (sessions) => {
  localStorage.setItem('chat_sessions', JSON.stringify(sessions))
}

export default function App() {
  // ── 状态管理 ──
  // 所有会话列表
  const [sessions, setSessions] = useState(loadSessions)
  // 当前活跃的会话 ID
  const [activeSessionId, setActiveSessionId] = useState(() => {
    const saved = loadSessions()
    return saved.length > 0 ? saved[0].id : null
  })

  // ── 获取当前会话 ──
  const activeSession = sessions.find((s) => s.id === activeSessionId) || null

  // ── 创建新会话 ──
  const handleNewChat = useCallback(() => {
    const newSession = {
      id: generateId(),
      title: '新对话',
      messages: [],
      createdAt: new Date().toISOString(),
    }
    const updated = [newSession, ...sessions]
    setSessions(updated)
    saveSessions(updated)
    setActiveSessionId(newSession.id)
  }, [sessions])

  // ── 切换会话 ──
  const handleSelectSession = useCallback((id) => {
    setActiveSessionId(id)
  }, [])

  // ── 删除会话 ──
  const handleDeleteSession = useCallback(
    (id) => {
      const updated = sessions.filter((s) => s.id !== id)
      setSessions(updated)
      saveSessions(updated)
      // 如果删除的是当前会话，切换到第一个
      if (id === activeSessionId) {
        setActiveSessionId(updated.length > 0 ? updated[0].id : null)
      }
    },
    [sessions, activeSessionId]
  )

  // ── 更新消息列表 ──
  const handleMessagesChange = useCallback(
    (messages) => {
      if (!activeSessionId) return
      const updated = sessions.map((s) => {
        if (s.id !== activeSessionId) return s
        // 自动取对话第一句作为标题
        const title =
          messages.length > 0 && messages[0].role === 'user'
            ? messages[0].content.slice(0, 30) + (messages[0].content.length > 30 ? '…' : '')
            : s.title
        return { ...s, messages, title }
      })
      setSessions(updated)
      saveSessions(updated)
    },
    [sessions, activeSessionId]
  )

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
        onMessagesChange={handleMessagesChange}
        onNewChat={handleNewChat}
      />
    </div>
  )
}
