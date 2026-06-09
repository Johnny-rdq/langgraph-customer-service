import { useState, useCallback, useRef } from 'react'  // React Hooks

// ── 后端 API 地址 ──
const API_BASE = '/api/v1'

// ── 生成唯一消息 ID ──
const generateMsgId = () => crypto.randomUUID?.() || Math.random().toString(36).slice(2, 10)

/**
 * 聊天逻辑 Hook —— 支持流式输出（逐字显示）
 */
export default function useChat(initialMessages = [], onMessagesChange) {
  // ── 状态 ──
  const [messages, setMessages] = useState(initialMessages)       // 消息列表
  const [isLoading, setIsLoading] = useState(false)                // 是否正在等待回复
  const [streamingContent, setStreamingContent] = useState('')     // 正在流式输出的文字
  const [error, setError] = useState(null)                         // 错误信息
  const sessionIdRef = useRef(null)                                // 后端会话 ID
  const userIdRef = useRef('user_' + generateMsgId())              // 用户唯一标识
  const abortRef = useRef(null)                                    // AbortController，用于取消请求

  // ── 更新消息（同时通知父组件）──
  const updateMessages = useCallback(
    (newMessages) => {
      setMessages(newMessages)
      if (onMessagesChange) onMessagesChange(newMessages)
    },
    [onMessagesChange]
  )

  // ── 发送消息（流式版本）──
  const sendMessage = useCallback(
    async (content) => {
      if (!content.trim() || isLoading) return

      // 添加用户消息到列表
      const userMsg = { id: generateMsgId(), role: 'user', content: content.trim() }
      const updatedMessages = [...messages, userMsg]
      updateMessages(updatedMessages)

      // 准备流式接收
      setIsLoading(true)
      setStreamingContent('')     // 清空流式缓冲区
      setError(null)

      // 创建 AbortController，支持取消
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

        // ── 读取 SSE 流 ──
        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')   // UTF-8 解码器
        let buffer = ''                             // 粘包缓冲区
        let fullContent = ''                        // 完整回复文本
        let finalSessionId = null
        let finalIntent = 'general'

        while (true) {
          const { done, value } = await reader.read()
          if (done) break  // 流结束

          // 解码并追加到缓冲区
          buffer += decoder.decode(value, { stream: true })

          // 按行解析 SSE 事件（格式: data: {...}\n\n）
          const lines = buffer.split('\n')
          // 最后一行可能不完整，留到下次处理
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue  // 跳过非 data 行
            const jsonStr = line.slice(6)              // 去掉 "data: " 前缀

            try {
              const event = JSON.parse(jsonStr)

              switch (event.type) {
                case 'token':
                  // 逐 token 追加到流式内容
                  fullContent += event.content
                  setStreamingContent(fullContent)     // 更新 UI
                  break

                case 'done':
                  // 流式结束，保存最终消息
                  finalSessionId = event.session_id
                  finalIntent = event.intent
                  break

                case 'error':
                  throw new Error(event.content)
              }
            } catch (parseErr) {
              // JSON 解析失败则跳过（可能是粘包的不完整行）
              if (parseErr instanceof SyntaxError) continue
              throw parseErr  // 非 JSON 错误则抛出
            }
          }
        }

        // ── 流式结束，将完整回复加入消息列表 ──
        if (finalSessionId) {
          sessionIdRef.current = finalSessionId
        }

        const aiMsg = {
          id: generateMsgId(),
          role: 'assistant',
          content: fullContent || '（未收到有效回复）',
        }
        updateMessages([...updatedMessages, aiMsg])
        setStreamingContent('')  // 清空流式缓冲区

      } catch (err) {
        if (err.name === 'AbortError') {
          // 用户主动取消，保留已输出的内容
          const aiMsg = {
            id: generateMsgId(),
            role: 'assistant',
            content: streamingContent || '（已取消）',
          }
          updateMessages([...updatedMessages, aiMsg])
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
        updateMessages([...updatedMessages, errorMsg])
        setStreamingContent('')
      } finally {
        setIsLoading(false)
        abortRef.current = null
      }
    },
    [messages, isLoading, streamingContent, updateMessages]  // 注意：streamingContent 在依赖中
  )

  // ── 清空聊天 ──
  const clearChat = useCallback(() => {
    updateMessages([])
    sessionIdRef.current = null
    setStreamingContent('')
    setError(null)
  }, [updateMessages])

  return {
    messages,           // 已完成的消息列表
    streamingContent,   // 正在流式输出的文字（实时更新）
    isLoading,          // 是否正在等待/接收
    isStreaming: isLoading && streamingContent !== '',  // 是否正在流式输出中
    error,
    sendMessage,
    clearChat,
  }
}
