import { useState, useCallback, useEffect } from 'react'  // DP React Hooks
import Sidebar from './components/Sidebar.jsx'   // DP 侧边栏组件
import ChatArea from './components/ChatArea.jsx'  // DP 主聊天区域组件

// DP ── 后端 API 基础地址 ──
const API_BASE = '/api/v1/sessions'

export default function App() {
  // DP ── 状态管理 ──
  const [sessions, setSessions] = useState([])  // DP 会话列表（从后端加载）
  const [activeSessionId, setActiveSessionId] = useState(null)  // DP 当前活跃会话 ID
  const [activeMessages, setActiveMessages] = useState([])  // DP 当前活跃会话的消息列表
  const [loading, setLoading] = useState(true)  // DP 首次加载状态

  // DP ── 页面初始化：从后端加载会话列表 ──
  useEffect(() => {
    loadSessions()  // DP 只执行一次
  }, [])

  const loadSessions = async () => {
    try {
      setLoading(true)  // DP 开始加载
      const res = await fetch(API_BASE)  // DP GET /api/v1/sessions/
      if (!res.ok) throw new Error('DP 加载会话失败')
      const data = await res.json()  // DP 解析后端返回的 JSON
      setSessions(data)  // DP 更新会话列表
      // DP 自动选中第一个会话
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id)  // DP 选中第一个
      }
    } catch (err) {
      console.error('DP 加载会话列表失败:', err)
    } finally {
      setLoading(false)  // DP 加载完成
    }
  }

  // DP ── 切换会话时，从后端加载对应消息 ──
  useEffect(() => {
    if (!activeSessionId) {
      setActiveMessages([])  // DP 没有选中会话则清空消息
      return
    }
    loadMessages(activeSessionId)  // DP 加载选中会话的消息
  }, [activeSessionId])

  const loadMessages = async (sessionId) => {
    try {
      const res = await fetch(`${API_BASE}/${sessionId}/messages`)  // DP GET /api/v1/sessions/{id}/messages
      if (!res.ok) throw new Error('DP 加载消息失败')
      const data = await res.json()  // DP 解析消息列表
      setActiveMessages(data)  // DP 更新当前消息列表
    } catch (err) {
      console.error('DP 加载消息失败:', err)
      setActiveMessages([])  // DP 出错则清空
    }
  }

  // DP ── 创建新会话 ──
  const handleNewChat = useCallback(async () => {
    try {
      const res = await fetch(API_BASE, { method: 'POST' })  // DP POST /api/v1/sessions/
      if (!res.ok) throw new Error('DP 创建会话失败')
      const newSession = await res.json()  // DP 解析新建的会话
      // DP 插入到列表顶部
      setSessions((prev) => [newSession, ...prev])
      setActiveSessionId(newSession.id)  // DP 自动切换到新会话
    } catch (err) {
      console.error('DP 创建会话失败:', err)
    }
  }, [])

  // DP ── 切换会话 ──
  const handleSelectSession = useCallback((id) => {
    setActiveSessionId(id)  // DP 更新 activeSessionId → useEffect 自动触发 loadMessages
  }, [])

  // DP ── 删除会话 ──
  const handleDeleteSession = useCallback(
    async (id) => {
      try {
        const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' })  // DP DELETE /api/v1/sessions/{id}
        if (!res.ok) throw new Error('DP 删除失败')
        const updated = sessions.filter((s) => s.id !== id)  // DP 从列表中移除
        setSessions(updated)  // DP 更新列表
        // DP 如果删除的是当前会话，切换到第一个
        if (id === activeSessionId) {
          setActiveSessionId(updated.length > 0 ? updated[0].id : null)  // DP 选第一个或清空
        }
      } catch (err) {
        console.error('DP 删除会话失败:', err)
      }
    },
    [sessions, activeSessionId]  // DP 依赖 sessions 和当前活跃 ID
  )

  // DP ── 保存单条消息到后端数据库 ──
  const saveMessage = useCallback(async (sessionId, role, content) => {
    try {
      const res = await fetch(`${API_BASE}/${sessionId}/messages`, {
        method: 'POST',  // DP POST
        headers: { 'Content-Type': 'application/json' },  // DP JSON 类型
        body: JSON.stringify({ role, content }),  // DP 请求体序列化
      })
      if (!res.ok) throw new Error('DP 保存消息失败')
      return await res.json()  // DP 返回保存成功的消息对象
    } catch (err) {
      console.error('DP 保存消息失败:', err)
      return null  // DP 失败返回 null
    }
  }, [])

  // DP ── 更新会话标题 ──
  const updateSessionTitle = useCallback(async (sessionId, title) => {
    try {
      await fetch(
        `${API_BASE}/${sessionId}?title=${encodeURIComponent(title)}`,  // DP query string 传标题
        { method: 'PATCH' }  // DP PATCH 部分更新
      )
      // DP 同步更新本地列表中的标题
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, title } : s))
      )
    } catch (err) {
      console.error('DP 更新标题失败:', err)
    }
  }, [])

  // DP ── 消息变更回调（useChat 每次有新消息时触发）──
  const handleMessagesChange = useCallback(
    async (messages) => {
      if (!activeSessionId) return  // DP 无活跃会话则忽略
      setActiveMessages(messages)  // DP 更新消息状态

      // DP 自动更新会话标题：取第一条用户消息的前 30 字
      const firstUserMsg = messages.find((m) => m.role === 'user')  // DP 找第一条用户消息
      if (firstUserMsg) {
        const currentSession = sessions.find((s) => s.id === activeSessionId)  // DP 找当前会话
        if (currentSession && currentSession.title === '新对话') {  // DP 标题还是默认值
          const title = firstUserMsg.content.slice(0, 30) + (firstUserMsg.content.length > 30 ? '…' : '')  // DP 截断
          updateSessionTitle(activeSessionId, title)  // DP 调用 API 更新标题
        }
      }
    },
    [activeSessionId, sessions, updateSessionTitle]  // DP 依赖当前会话和更新函数
  )

  // DP ── 当前活跃的会话对象 ──
  const activeSession = sessions.find((s) => s.id === activeSessionId) || null

  // DP 首次加载中，显示加载状态
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-surface-950">
        <p className="text-surface-400 text-lg">DP 正在加载会话…</p>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface-950">
      {/* DP 侧边栏 */}
      <Sidebar
        sessions={sessions}  {/* DP 会话列表 */}
        activeSessionId={activeSessionId}  {/* DP 当前活跃会话 ID */}
        onNewChat={handleNewChat}  {/* DP 新建会话回调 */}
        onSelectSession={handleSelectSession}  {/* DP 切换会话回调 */}
        onDeleteSession={handleDeleteSession}  {/* DP 删除会话回调 */}
      />

      {/* DP 主聊天区域 */}
      <ChatArea
        session={activeSession}  {/* DP 当前会话对象 */}
        messages={activeMessages}  {/* DP 从后端加载的消息列表 */}
        onMessagesChange={handleMessagesChange}  {/* DP 消息变更回调 */}
        onNewChat={handleNewChat}  {/* DP 新建会话回调 */}
        onSaveMessage={saveMessage}  {/* DP 消息持久化回调 */}
      />
    </div>
  )
}