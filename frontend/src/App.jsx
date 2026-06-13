import { useState, useCallback, useEffect, useRef } from 'react'  // React Hooks
import Sidebar from './components/Sidebar.jsx'   // 侧边栏组件
import ChatArea from './components/ChatArea.jsx'  // 主聊天区域组件

// 后端 API 基础地址
const API_BASE = '/api/v1/sessions'

export default function App() {
  // 状态管理
  const [sessions, setSessions] = useState([])  // 会话列表（从后端加载）
  const [activeSessionId, setActiveSessionId] = useState(null)  // 当前活跃会话 ID
  const [activeMessages, setActiveMessages] = useState([])  // 当前活跃会话的消息列表
  const [messagesLoading, setMessagesLoading] = useState(false)  // 消息加载中
  const [loading, setLoading] = useState(true)  // 首次加载状态
  const msgCountRef = useRef(0)  // 消息计数守卫：防止空数据覆盖导致闪屏

  // 页面初始化：从后端加载会话列表
  useEffect(() => {
    loadSessions()  // 只执行一次
  }, [])

  const loadSessions = async () => {
    try {
      setLoading(true)
      const res = await fetch(API_BASE)
      if (!res.ok) throw new Error('加载会话失败')
      const data = await res.json()
      setSessions(data)
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id)
      }
    } catch (err) {
      console.error('加载会话列表失败:', err)
    } finally {
      setLoading(false)
    }
  }

  // 每 2 秒轮询最新消息，msgCountRef 防闪屏守卫
  useEffect(() => {
    if (!activeSessionId) return; // 如果没有选中的会话，就不刷新

    const fetchLatestMessages = async () => {
      try {
        const res = await fetch(`${API_BASE}/${activeSessionId}/messages`);
        if (res.ok) {
          const data = await res.json();
          // 消息数比当前少则跳过（DB 未同步完）
          if (data.length < msgCountRef.current) return;
          msgCountRef.current = data.length;  // 更新计数
          setActiveMessages(data); // 实时更新消息列表
        }
      } catch (error) {
        console.error("后台刷新消息失败:", error);
      }
    };

    const interval = setInterval(fetchLatestMessages, 2000);
    return () => clearInterval(interval); // 切换会话或卸载组件时清理定时器
  }, [activeSessionId]);

  // 切换会话时：清空旧消息 → 显示加载 → 异步加载新消息
  useEffect(() => {
    if (!activeSessionId) {
      setActiveMessages([])
      msgCountRef.current = 0
      return
    }
    setActiveMessages([])
    msgCountRef.current = 0
    setMessagesLoading(true)
    loadMessages(activeSessionId)
  }, [activeSessionId])

  const loadMessages = async (sessionId) => {
    try {
      const res = await fetch(`${API_BASE}/${sessionId}/messages`)
      if (!res.ok) throw new Error('加载消息失败')
      const data = await res.json()
      msgCountRef.current = data.length
      setActiveMessages(data)
    } catch (err) {
      console.error('加载消息失败:', err)
      msgCountRef.current = 0
      setActiveMessages([])
    } finally {
      setMessagesLoading(false)
    }
  }

  // 创建新会话
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

  // 切换会话
  const handleSelectSession = useCallback((id) => {
    if (id === activeSessionId) return
    setActiveMessages([])
    setActiveSessionId(id)
  }, [activeSessionId])

  // 删除会话
  const handleDeleteSession = useCallback(
    async (id) => {
      try {
        const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' })
        if (!res.ok) throw new Error('删除失败')
        const updated = sessions.filter((s) => s.id !== id)
        setSessions(updated)
        if (id === activeSessionId) {
          setActiveSessionId(updated.length > 0 ? updated[0].id : null)
        }
      } catch (err) {
        console.error('删除会话失败:', err)
      }
    },
    [sessions, activeSessionId]
  )

  // 保存单条消息到后端数据库 + 第一条用户消息自动设为会话标题
  const saveMessage = useCallback(async (sessionId, role, content) => {
    try {
      const res = await fetch(`${API_BASE}/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, content }),
      })
      if (!res.ok) throw new Error('保存消息失败')

      // 如果是用户消息，取前 30 字自动更新侧边栏标题
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

  // 消息变更回调
  const handleMessagesChange = useCallback(
    (messages) => {
      if (!activeSessionId) return
      if (messages.length > msgCountRef.current) {
        msgCountRef.current = messages.length
      }
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