import { useState, useCallback, useRef, useEffect } from 'react'

const API_BASE = '/api/v1'
const generateMsgId = () => crypto.randomUUID?.() || Math.random().toString(36).slice(2, 10)

export default function useChat(sessionId, initialMessages = [], onMessagesChange, onSaveMessage) {
  const [messages, setMessages] = useState(initialMessages)
  const [isLoading, setIsLoading] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [error, setError] = useState(null)

  const sessionIdRef = useRef(sessionId)
  const userIdRef = useRef('user_' + generateMsgId())
  const abortRef = useRef(null)
  const hasContentRef = useRef(false)

  const [isHumanMode, setIsHumanMode] = useState(false)
  const isHumanModeRef = useRef(false)

  const lastActivityRef = useRef(Date.now())

  const setHumanModeState = useCallback((val) => {
    isHumanModeRef.current = val
    setIsHumanMode(val)
  }, [])

  useEffect(() => {
    setStreamingContent('')
    setError(null)
    hasContentRef.current = false
    setHumanModeState(false)
  }, [sessionId, setHumanModeState])

  useEffect(() => {
    if (messages.length > 0) hasContentRef.current = true
  }, [messages])

  useEffect(() => {
    if (initialMessages.length === 0 && hasContentRef.current) return
    setMessages((prev) => {
      if (sessionId !== sessionIdRef.current) return initialMessages
      if (initialMessages.length <= prev.length) return prev
      return initialMessages
    })
    sessionIdRef.current = sessionId
  }, [sessionId, initialMessages])

  const exitHumanMode = useCallback(async (reason = 'manual') => {
    if (!sessionIdRef.current) return
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionIdRef.current}/exit_human`, {
        method: 'POST'
      })
      if (res.ok) {
        setHumanModeState(false)

        let text = '✅ **已退出人工客服**\n智能助手已重新接管，请问还有什么我可以帮您的吗？'
        if (reason === 'timeout') {
          text = '⏱️ **对话超时**\n由于您长时间未发送消息，已自动断开人工服务。\n智能助手已重新接管，请问还有什么可以帮您？'
        }

        const sysMsg = { id: generateMsgId(), role: 'assistant', content: text }
        setMessages((prev) => {
          const newMsgs = [...prev, sysMsg]
          setTimeout(() => { if (onMessagesChange) onMessagesChange(newMsgs) }, 0)
          return newMsgs
        })
        if (onSaveMessage) {
          onSaveMessage(sessionIdRef.current, 'assistant', sysMsg.content)
        }
      }
    } catch (err) {
      console.error('退出人工模式失败:', err)
    }
  }, [onMessagesChange, onSaveMessage, setHumanModeState])

  useEffect(() => {
    const interval = setInterval(() => {
      if (isHumanModeRef.current) {
        const now = Date.now()
        if (now - lastActivityRef.current >= 30000) {
          console.log('⏳ 30秒无操作，触发自动退出人工客服')
          exitHumanMode('timeout')
        }
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [exitHumanMode])

  useEffect(() => {
    if (!sessionId) return
    const wsUrl = `ws://localhost:8888/api/v1/ws/${sessionId}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => console.log(`✅ WebSocket 已连接 (Session: ${sessionId})`)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'admin_reply' && data.content && data.content.trim() !== '') {
          setHumanModeState(true)
          lastActivityRef.current = Date.now()

          const adminMsg = { id: generateMsgId(), role: 'assistant', content: data.content }
          setMessages((prevMessages) => {
            const newMessages = [...prevMessages, adminMsg]
            setTimeout(() => { if (onMessagesChange) onMessagesChange(newMessages) }, 0)
            return newMessages
          })
        }
      } catch (err) {
        console.error('WebSocket 消息解析失败:', err)
      }
    }

    ws.onclose = () => console.log(`❌ WebSocket 已断开 (Session: ${sessionId})`)
    ws.onerror = (err) => console.error('WebSocket 发生错误:', err)

    return () => ws.close()
  }, [sessionId, setHumanModeState, onMessagesChange])

  const updateMessages = useCallback((newMessages) => {
    setMessages(newMessages)
    if (onMessagesChange) onMessagesChange(newMessages)
  }, [onMessagesChange])

  const sendMessage = useCallback(async (content) => {
    if (!content.trim() || isLoading) return

    // 🌟 记录发送消息前，我们是不是已经是人工模式了
    const wasHumanMode = isHumanModeRef.current

    lastActivityRef.current = Date.now()

    const userMsg = { id: generateMsgId(), role: 'user', content: content.trim() }

    setMessages((prev) => {
      const newMsgs = [...prev, userMsg]
      setTimeout(() => { if (onMessagesChange) onMessagesChange(newMsgs) }, 0)
      return newMsgs
    })

    if (onSaveMessage && sessionIdRef.current) {
      onSaveMessage(sessionIdRef.current, 'user', content.trim())
    }

    setIsLoading(true)
    setStreamingContent('')
    setError(null)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userIdRef.current,
          message: content.trim(),
          session_id: sessionIdRef.current,
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || `请求失败 (${response.status})`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      let fullContent = ''
      let finalSessionId = null
      let finalRequiresHuman = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const jsonStr = line.slice(6)

          try {
            const event = JSON.parse(jsonStr)
            switch (event.type) {
              case 'token':
                fullContent += event.content
                if (fullContent.trim() !== '') {
                  setStreamingContent(fullContent)
                }
                break
              case 'done':
                finalSessionId = event.session_id
                finalRequiresHuman = event.requires_human || false
                setHumanModeState(finalRequiresHuman)

                if (finalRequiresHuman) {
                  lastActivityRef.current = Date.now()
                }
                break
              case 'error':
                throw new Error(event.content)
            }
          } catch (parseErr) {
            if (parseErr instanceof SyntaxError) continue
            throw parseErr
          }
        }
      }

      if (finalSessionId) {
        sessionIdRef.current = finalSessionId
      }

      const finalContent = fullContent.trim()

      // 🌟🌟🌟 核心补偿逻辑：在这里主动给用户屏幕加上系统提示 🌟🌟🌟
      if (finalContent !== '') {
        // 场景 A：AI 说话了（比如：“好的，正在帮您转接...”）
        setMessages((prev) => {
          const newMsgs = [...prev, { id: generateMsgId(), role: 'assistant', content: finalContent }]

          // 如果这轮正好触发了转人工，紧跟着把系统提示气泡画出来！
          if (finalRequiresHuman && !wasHumanMode) {
            newMsgs.push({
              id: generateMsgId(),
              role: 'assistant',
              content: '【系统提示】已为您成功转接，人工客服马上就来！'
            })
          }

          setTimeout(() => { if (onMessagesChange) onMessagesChange(newMsgs) }, 0)
          return newMsgs
        })
        if (!finalRequiresHuman && onSaveMessage && finalSessionId) {
          onSaveMessage(finalSessionId, 'assistant', finalContent)
        }
      } else if (finalRequiresHuman && !wasHumanMode) {
        // 场景 B：AI 什么都没说，纯静默转接
        // 我们直接代替后端，在前端主动渲染出这句一模一样的系统提示
        setMessages((prev) => {
          const newMsgs = [...prev, {
            id: generateMsgId(),
            role: 'assistant',
            content: '【系统提示】已为您成功转接，人工客服马上就来！'
          }]
          setTimeout(() => { if (onMessagesChange) onMessagesChange(newMsgs) }, 0)
          return newMsgs
        })
        // ⚠️ 这里不要调用 onSaveMessage，因为后端的 nodes.py 已经把这句话写进数据库里了！
      } else if (!finalRequiresHuman) {
        const aiMsg = { id: generateMsgId(), role: 'assistant', content: '（未收到有效回复）' }
        setMessages((prev) => {
          const newMsgs = [...prev, aiMsg]
          setTimeout(() => { if (onMessagesChange) onMessagesChange(newMsgs) }, 0)
          return newMsgs
        })
        if (onSaveMessage && finalSessionId) {
          onSaveMessage(finalSessionId, 'assistant', '（未收到有效回复）')
        }
      }

      setStreamingContent('')

    } catch (err) {
      if (err.name === 'AbortError') {
        const aiMsg = {
          id: generateMsgId(),
          role: 'assistant',
          content: streamingContent || '（已取消）',
        }
        setMessages((prev) => {
          const newMsgs = [...prev, aiMsg]
          setTimeout(() => { if (onMessagesChange) onMessagesChange(newMsgs) }, 0)
          return newMsgs
        })
        setStreamingContent('')
        return
      }

      console.error('发送消息失败:', err)
      setError(err.message || '网络错误')
      const errorMsg = {
        id: generateMsgId(),
        role: 'assistant',
        content: `抱歉，系统遇到了一个问题：${err.message || '请稍后重试'}`,
        isError: true,
      }
      setMessages((prev) => {
        const newMsgs = [...prev, errorMsg]
        setTimeout(() => { if (onMessagesChange) onMessagesChange(newMsgs) }, 0)
        return newMsgs
      })
      setStreamingContent('')
    } finally {
      setIsLoading(false)
      abortRef.current = null
    }
  }, [isLoading, streamingContent, onSaveMessage, onMessagesChange, setHumanModeState])

  const clearChat = useCallback(() => {
    updateMessages([])
    sessionIdRef.current = null
    setStreamingContent('')
    setError(null)
  }, [updateMessages])

  return {
    messages,
    streamingContent,
    isLoading: isLoading && !isHumanModeRef.current,
    isStreaming: isLoading && streamingContent.trim() !== '',
    isHumanMode,
    exitHumanMode,
    error,
    sendMessage,
    clearChat,
  }
}