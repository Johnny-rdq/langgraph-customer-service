import { useState, useCallback, useEffect } from 'react'
import Sidebar from './components/Sidebar.jsx'
import ChatArea from './components/ChatArea.jsx'

const API_BASE = '/api/v1/sessions'

export default function App() {
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [activeMessages, setActiveMessages] = useState([])
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      setLoading(true)
      const res = await fetch(API_BASE)
      if (!res.ok) throw new Error('加载会话失败')
      const data = await res.json()

      // 🌟 核心修复 1：如果一个会话都没有，直接在初始化时自动请求后端生成一个
      if (data.length === 0) {
        const createRes = await fetch(API_BASE, { method: 'POST' })
        if (createRes.ok) {
          const newSession = await createRes.json()
          setSessions([newSession])
          setActiveSessionId(newSession.id)
        }
      } else {
        setSessions(data)
        if (!activeSessionId) {
          setActiveSessionId(data[0].id)
        }
      }
    } catch (err) {
      console.error('加载会话列表失败:', err)
    } finally {
      setLoading(false)
    }
  }

  // 切换会话
  useEffect(() => {
    if (!activeSessionId) {
      setActiveMessages([])
      return
    }
    setActiveMessages([])
    setMessagesLoading(true)
    loadMessages(activeSessionId)
  }, [activeSessionId])

  const loadMessages = async (sessionId) => {
    try {
      const res = await fetch(`${API_BASE}/${sessionId}/messages`)
      if (!res.ok) throw new Error('加载消息失败')
      const data = await res.json()
      setActiveMessages(data)
    } catch (err) {
      console.error('加载消息失败:', err)
      setActiveMessages([])
    } finally {
      setMessagesLoading(false)
    }
  }

  const handleNewChat = useCallback(async () => {
    try {
      const res = await fetch(API_BASE, { method: 'POST' })
      if (!res.ok) throw new Error('创建会话失败')
      const newSession = await res.json()
      setActiveMessages([])
      setSessions((prev) => [newSession, ...prev])
      setActiveSessionId(newSession.id)
    } catch (err) {
      console.error('创建会话失败:', err)
    }
  }, [])

  const handleSelectSession = useCallback((id) => {
    if (id === activeSessionId) return
    setActiveMessages([])
    setActiveSessionId(id)
  }, [activeSessionId])

  const handleDeleteSession = useCallback(
    async (id) => {
      try {
        const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' })
        if (!res.ok) throw new Error('删除失败')
        const updated = sessions.filter((s) => s.id !== id)
        setSessions(updated)

        if (id === activeSessionId) {
          if (updated.length > 0) {
            setActiveSessionId(updated[0].id)
          } else {
            // 🌟 核心修复 2：如果删除了左侧最后一个会话，自动补位创建，绝不留空白
            const createRes = await fetch(API_BASE, { method: 'POST' })
            if (createRes.ok) {
              const newSession = await createRes.json()
              setSessions([newSession])
              setActiveSessionId(newSession.id)
            } else {
              setActiveSessionId(null)
            }
          }
        }
      } catch (err) {
        console.error('删除会话失败:', err)
      }
    },
    [sessions, activeSessionId]
  )

  const saveMessage = useCallback(async (sessionId, role, content) => {
    try {
      const res = await fetch(`${API_BASE}/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, content }),
      })
      if (!res.ok) throw new Error('保存消息失败')

      if (role === 'user') {
        const title = content.slice(0, 30) + (content.length > 30 ? '…' : '')
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId && s.title === '新对话'
              ? { ...s, title }
              : s
          )
        )
      }

      return await res.json()
    } catch (err) {
      console.error('保存消息失败:', err)
      return null
    }
  }, [])

  const handleMessagesChange = useCallback(
    (messages) => {
      if (!activeSessionId) return
      setActiveMessages(messages)
    },
    [activeSessionId]
  )

  const activeSession = sessions.find((s) => s.id === activeSessionId) || null

  if (loading) {
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