import { useState, useCallback, useRef, useEffect } from 'react'  // React Hooks

// ── 后端 API 地址 ──
const API_BASE = '/api/v1'

// ── 生成唯一消息 ID（优先 crypto.randomUUID，降级到 Math.random）──
const generateMsgId = () => crypto.randomUUID?.() || Math.random().toString(36).slice(2, 10)

/**
 * 聊天逻辑 Hook —— 支持 SSE 流式输出（逐字显示）
 * 每次收发消息时自动调用 onSaveMessage 持久化到后端数据库。
 *
 * @param {string} sessionId - 当前会话 ID
 * @param {Array} initialMessages - 从后端加载的初始消息列表
 * @param {Function} onMessagesChange - 消息变更回调（通知父组件更新状态）
 * @param {Function} onSaveMessage - 消息持久化回调（保存到后端数据库）
 */
export default function useChat(sessionId, initialMessages = [], onMessagesChange, onSaveMessage) {
  // ── 状态 ──
  const [messages, setMessages] = useState(initialMessages)       // 消息列表
  const [isLoading, setIsLoading] = useState(false)                // 是否正在等待/接收回复
  const [streamingContent, setStreamingContent] = useState('')     // 正在流式输出的文字（逐字更新）
  const [error, setError] = useState(null)                         // 错误信息
  const sessionIdRef = useRef(sessionId)                           // 后端会话 ID（ref 避免闭包问题）
  const userIdRef = useRef('user_' + generateMsgId())              // 用户唯一标识（页面级）
  const abortRef = useRef(null)                                    // AbortController，用于取消请求
  const hasContentRef = useRef(false)                              // 当前会话是否有过消息（防止外部空数据覆盖导致闪屏）

  // 切换会话时重置
  useEffect(() => {
    setStreamingContent('')
    setError(null)
    hasContentRef.current = false
  }, [sessionId])

  // 追踪内部消息是否有内容
  useEffect(() => {
    if (messages.length > 0) hasContentRef.current = true
  }, [messages])

  // 同步外部消息到内部状态。守卫：外部传入空数组但当前会话已有过消息时拒绝同步
  useEffect(() => {
    if (initialMessages.length === 0 && hasContentRef.current) return
    setMessages(initialMessages)
    sessionIdRef.current = sessionId
  }, [sessionId, initialMessages])

  // 🌟🌟🌟 新增：WebSocket 监听器（负责接收人工客服的突然回复） 🌟🌟🌟
  useEffect(() => {
    // 如果没有选中具体的会话，就不连接
    if (!sessionId) return

    // 建立 WebSocket 连接 (直连后端 8888 端口，与 main.py 硬编码端口一致)
    const wsUrl = `ws://localhost:8888/api/v1/ws/${sessionId}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log(`✅ WebSocket 已连接 (Session: ${sessionId})`)
    }

    // 🌟 核心：监听到后端发来消息
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.type === 'admin_reply') {
          const adminMsg = {
            id: generateMsgId(),
            role: 'assistant',
            content: data.content,
          }

          // ！！！关键修复：不光要更新内部，还要通知父组件 App.jsx ！！！
          setMessages((prevMessages) => {
            const newMessages = [...prevMessages, adminMsg];

            // 用 setTimeout 避开 React 渲染冲突，将新消息同步给全局
            setTimeout(() => {
              if (onMessagesChange) {
                onMessagesChange(newMessages);
              }
            }, 0);

            return newMessages;
          });
        }
      } catch (err) {
        console.error('WebSocket 消息解析失败:', err)
      }
    }

    ws.onclose = () => {
      console.log(`❌ WebSocket 已断开 (Session: ${sessionId})`)
    }

    ws.onerror = (err) => {
      console.error('WebSocket 发生错误:', err)
    }

    // 清理函数：当用户切换到别的会话，或者关闭网页时，自动断开旧的 WebSocket
    return () => {
      ws.close()
    }
  }, [sessionId]) // 只要 sessionId 变化，就重新建立对应的连接
  // 🌟🌟🌟 WebSocket 监听器结束 🌟🌟🌟


  // ── 更新消息（同时通知父组件）──
  const updateMessages = useCallback(
    (newMessages) => {
      setMessages(newMessages)  // 更新 Hook 内部状态
      if (onMessagesChange) onMessagesChange(newMessages)  // 通知父组件
    },
    [onMessagesChange]  // 依赖父组件回调
  )

  // ── 发送消息（流式 SSE 版本）──
  const sendMessage = useCallback(
    async (content) => {
      if (!content.trim() || isLoading) return  // 空消息或加载中则忽略

      // 添加用户消息到列表
      const userMsg = { id: generateMsgId(), role: 'user', content: content.trim() }  // 构建用户消息
      const updatedMessages = [...messages, userMsg]  // 追加到消息列表
      updateMessages(updatedMessages)  // 更新界面

      // ── 持久化用户消息到后端数据库 ──
      if (onSaveMessage && sessionIdRef.current) {
        onSaveMessage(sessionIdRef.current, 'user', content.trim())  // 异步保存（fire-and-forget）
      }

      // 准备流式接收
      setIsLoading(true)  // 标记加载中
      setStreamingContent('')  // 清空流式缓冲区
      setError(null)  // 清空旧错误

      // 创建 AbortController，支持取消请求
      const controller = new AbortController()
      abortRef.current = controller  // 保存引用，供外部取消

      try {
        const response = await fetch(`${API_BASE}/chat/stream`, {
          method: 'POST',  // POST 请求
          headers: { 'Content-Type': 'application/json' },  // JSON 请求头
          body: JSON.stringify({
            user_id: userIdRef.current,  // 用户 ID
            message: content.trim(),  // 消息内容
            session_id: sessionIdRef.current,  // 会话 ID
          }),
          signal: controller.signal,  // 绑定取消信号
        })

        if (!response.ok) {
          // 响应异常时尝试解析错误详情
          const errData = await response.json().catch(() => ({}))  // 安全解析
          throw new Error(errData.detail || `请求失败 (${response.status})`)  // 抛出异常
        }

        // ── 读取 SSE 流 ──
        const reader = response.body.getReader()  // 获取 ReadableStream 读取器
        const decoder = new TextDecoder('utf-8')   // UTF-8 解码器
        let buffer = ''                             // 粘包缓冲区
        let fullContent = ''                        // 完整回复文本
        let finalSessionId = null                   // 流结束时的 session ID
        let finalIntent = 'general'                 // 流结束时的意图
        let finalRequiresHuman = false              // 流结束时是否需要转人工

        while (true) {
          const { done, value } = await reader.read()  // 读取一块数据
          if (done) break  // 流结束

          // 解码并追加到缓冲区
          buffer += decoder.decode(value, { stream: true })

          // 按行解析 SSE 事件（格式: data: {...}\n\n）
          const lines = buffer.split('\n')  // 按换行分割
          // 最后一行可能不完整，留到下次处理
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue  // 跳过非 data 行
            const jsonStr = line.slice(6)              // 去掉 "data: " 前缀

            try {
              const event = JSON.parse(jsonStr)  // 解析事件 JSON

              switch (event.type) {
                case 'token':
                  // 逐 token 追加到流式内容
                  fullContent += event.content  // 拼接到完整回复
                  setStreamingContent(fullContent)  // 更新 UI 实时显示
                  break

                case 'done':
                  // 流式结束，保存最终元数据
                  finalSessionId = event.session_id  // 记录 session ID
                  finalIntent = event.intent  // 记录意图
                  finalRequiresHuman = event.requires_human || false
                  break

                case 'error':
                  // 后端错误事件
                  throw new Error(event.content)  // 抛出错误走 catch 处理
              }
            } catch (parseErr) {
              // JSON 解析失败则跳过（可能是粘包的不完整行）
              if (parseErr instanceof SyntaxError) continue  // 跳过 JSON 错误
              throw parseErr  // 非 JSON 错误则抛出
            }
          }
        }

        // ── 流式结束，将完整 AI 回复加入消息列表 ──
        if (finalSessionId) {
          sessionIdRef.current = finalSessionId  // 更新 session ref
        }

        // 转人工时不生成本地 AI 兜底消息，等轮询从 DB 加载
        if (!finalRequiresHuman) {
          const aiMsg = {
            id: generateMsgId(),
            role: 'assistant',
            content: fullContent || '（未收到有效回复）',
          }
          updateMessages([...updatedMessages, aiMsg])  // 追加 AI 消息到列表

          // 持久化 AI 回复到后端数据库
          if (onSaveMessage && finalSessionId) {
            onSaveMessage(finalSessionId, 'assistant', fullContent || '（未收到有效回复）')
          }
        }
        setStreamingContent('')  // 清空流式缓冲区

      } catch (err) {
        if (err.name === 'AbortError') {
          // 用户主动取消请求，保留已输出的流式内容
          const aiMsg = {
            id: generateMsgId(),  // 消息 ID
            role: 'assistant',  // 角色
            content: streamingContent || '（已取消）',  // 用户取消时保留已输出内容
          }
          updateMessages([...updatedMessages, aiMsg])  // 追加到列表
          setStreamingContent('')  // 清空缓冲区
          return  // 不继续处理
        }
        console.error('发送消息失败:', err)  // 打印错误
        setError(err.message || '网络错误')  // 设置错误状态
        const errorMsg = {
          id: generateMsgId(),  // 错误消息 ID
          role: 'assistant',  // 角色
          content: `抱歉，系统遇到了一个问题：${err.message || '请稍后重试'}`,  // 错误提示文案
          isError: true,  // 标记为错误消息（UI 可能用不同样式）
        }
        updateMessages([...updatedMessages, errorMsg])  // 追加错误消息
        setStreamingContent('')  // 清空缓冲区
      } finally {
        setIsLoading(false)  // 加载结束
        abortRef.current = null  // 清空 abort 引用
      }
    },
    [messages, isLoading, streamingContent, updateMessages]  // 依赖消息状态和更新函数
  )

  // ── 清空聊天 ──
  const clearChat = useCallback(() => {
    updateMessages([])  // 清空消息列表
    sessionIdRef.current = null  // 清空 session ref
    setStreamingContent('')  // 清空流式缓冲区
    setError(null)  // 清空错误
  }, [updateMessages])  // 依赖消息更新函数

  return {
    messages,  // 已完成的消息列表
    streamingContent,  // 正在流式输出的文字（实时更新）
    isLoading,  // 是否正在等待/接收
    isStreaming: isLoading && streamingContent !== '',  // 是否正在流式输出中
    error,  // 错误信息
    sendMessage,  // 发送消息函数
    clearChat,  // 清空聊天函数
  }
}