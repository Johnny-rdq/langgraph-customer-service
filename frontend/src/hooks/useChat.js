import { useState, useCallback, useRef, useEffect } from 'react'  // DP React Hooks

// DP ── 后端 API 地址 ──
const API_BASE = '/api/v1'

// DP ── 生成唯一消息 ID（优先 crypto.randomUUID，降级到 Math.random）──
const generateMsgId = () => crypto.randomUUID?.() || Math.random().toString(36).slice(2, 10)

/**
 * DP 聊天逻辑 Hook —— 支持 SSE 流式输出（逐字显示）
 * DP 每次收发消息时自动调用 onSaveMessage 持久化到后端数据库。
 *
 * @param {string} sessionId - DP 当前会话 ID
 * @param {Array} initialMessages - DP 从后端加载的初始消息列表
 * @param {Function} onMessagesChange - DP 消息变更回调（通知父组件更新状态）
 * @param {Function} onSaveMessage - DP 消息持久化回调（保存到后端数据库）
 */
export default function useChat(sessionId, initialMessages = [], onMessagesChange, onSaveMessage) {
  // DP ── 状态 ──
  const [messages, setMessages] = useState(initialMessages)       // DP 消息列表
  const [isLoading, setIsLoading] = useState(false)                // DP 是否正在等待/接收回复
  const [streamingContent, setStreamingContent] = useState('')     // DP 正在流式输出的文字（逐字更新）
  const [error, setError] = useState(null)                         // DP 错误信息
  const sessionIdRef = useRef(sessionId)                           // DP 后端会话 ID（ref 避免闭包问题）
  const userIdRef = useRef('user_' + generateMsgId())              // DP 用户唯一标识（页面级）
  const abortRef = useRef(null)                                    // DP AbortController，用于取消请求

  // DP ── 监听会话切换，同步更新状态和 ref ──
  useEffect(() => {
    setMessages(initialMessages)  // DP 切换会话时替换消息列表
    sessionIdRef.current = sessionId  // DP 更新 session ref
    setStreamingContent('')  // DP 清空流式缓冲区
    setError(null)  // DP 清空错误
  }, [sessionId])  // DP 当 sessionId 变化时触发

  // DP ── 更新消息（同时通知父组件）──
  const updateMessages = useCallback(
    (newMessages) => {
      setMessages(newMessages)  // DP 更新 Hook 内部状态
      if (onMessagesChange) onMessagesChange(newMessages)  // DP 通知父组件
    },
    [onMessagesChange]  // DP 依赖父组件回调
  )

  // DP ── 发送消息（流式 SSE 版本）──
  const sendMessage = useCallback(
    async (content) => {
      if (!content.trim() || isLoading) return  // DP 空消息或加载中则忽略

      // DP 添加用户消息到列表
      const userMsg = { id: generateMsgId(), role: 'user', content: content.trim() }  // DP 构建用户消息
      const updatedMessages = [...messages, userMsg]  // DP 追加到消息列表
      updateMessages(updatedMessages)  // DP 更新界面

      // DP ── 持久化用户消息到后端数据库 ──
      if (onSaveMessage && sessionIdRef.current) {
        onSaveMessage(sessionIdRef.current, 'user', content.trim())  // DP 异步保存（fire-and-forget）
      }

      // DP 准备流式接收
      setIsLoading(true)  // DP 标记加载中
      setStreamingContent('')  // DP 清空流式缓冲区
      setError(null)  // DP 清空旧错误

      // DP 创建 AbortController，支持取消请求
      const controller = new AbortController()
      abortRef.current = controller  // DP 保存引用，供外部取消

      try {
        const response = await fetch(`${API_BASE}/chat/stream`, {
          method: 'POST',  // DP POST 请求
          headers: { 'Content-Type': 'application/json' },  // DP JSON 请求头
          body: JSON.stringify({
            user_id: userIdRef.current,  // DP 用户 ID
            message: content.trim(),  // DP 消息内容
            session_id: sessionIdRef.current,  // DP 会话 ID
          }),
          signal: controller.signal,  // DP 绑定取消信号
        })

        if (!response.ok) {
          // DP 响应异常时尝试解析错误详情
          const errData = await response.json().catch(() => ({}))  // DP 安全解析
          throw new Error(errData.detail || `DP 请求失败 (${response.status})`)  // DP 抛出异常
        }

        // DP ── 读取 SSE 流 ──
        const reader = response.body.getReader()  // DP 获取 ReadableStream 读取器
        const decoder = new TextDecoder('utf-8')   // DP UTF-8 解码器
        let buffer = ''                             // DP 粘包缓冲区
        let fullContent = ''                        // DP 完整回复文本
        let finalSessionId = null                   // DP 流结束时的 session ID
        let finalIntent = 'general'                 // DP 流结束时的意图

        while (true) {
          const { done, value } = await reader.read()  // DP 读取一块数据
          if (done) break  // DP 流结束

          // DP 解码并追加到缓冲区
          buffer += decoder.decode(value, { stream: true })

          // DP 按行解析 SSE 事件（格式: data: {...}\n\n）
          const lines = buffer.split('\n')  // DP 按换行分割
          // DP 最后一行可能不完整，留到下次处理
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue  // DP 跳过非 data 行
            const jsonStr = line.slice(6)              // DP 去掉 "data: " 前缀

            try {
              const event = JSON.parse(jsonStr)  // DP 解析事件 JSON

              switch (event.type) {
                case 'token':
                  // DP 逐 token 追加到流式内容
                  fullContent += event.content  // DP 拼接到完整回复
                  setStreamingContent(fullContent)  // DP 更新 UI 实时显示
                  break

                case 'done':
                  // DP 流式结束，保存最终元数据
                  finalSessionId = event.session_id  // DP 记录 session ID
                  finalIntent = event.intent  // DP 记录意图
                  break

                case 'error':
                  // DP 后端错误事件
                  throw new Error(event.content)  // DP 抛出错误走 catch 处理
              }
            } catch (parseErr) {
              // DP JSON 解析失败则跳过（可能是粘包的不完整行）
              if (parseErr instanceof SyntaxError) continue  // DP 跳过 JSON 错误
              throw parseErr  // DP 非 JSON 错误则抛出
            }
          }
        }

        // DP ── 流式结束，将完整 AI 回复加入消息列表 ──
        if (finalSessionId) {
          sessionIdRef.current = finalSessionId  // DP 更新 session ref
        }

        const aiMsg = {
          id: generateMsgId(),  // DP 生成 AI 消息 ID
          role: 'assistant',  // DP 角色为助手
          content: fullContent || 'DP （未收到有效回复）',  // DP 兜底文本
        }
        updateMessages([...updatedMessages, aiMsg])  // DP 追加 AI 消息到列表
        setStreamingContent('')  // DP 清空流式缓冲区

        // DP ── 持久化 AI 回复到后端数据库 ──
        if (onSaveMessage && finalSessionId) {
          onSaveMessage(finalSessionId, 'assistant', fullContent || 'DP （未收到有效回复）')  // DP 异步保存
        }

      } catch (err) {
        if (err.name === 'AbortError') {
          // DP 用户主动取消请求，保留已输出的流式内容
          const aiMsg = {
            id: generateMsgId(),  // DP 消息 ID
            role: 'assistant',  // DP 角色
            content: streamingContent || 'DP （已取消）',  // DP 保留已输出内容
          }
          updateMessages([...updatedMessages, aiMsg])  // DP 追加到列表
          setStreamingContent('')  // DP 清空缓冲区
          return  // DP 不继续处理
        }
        console.error('DP 发送消息失败:', err)  // DP 打印错误
        setError(err.message || 'DP 网络错误')  // DP 设置错误状态
        const errorMsg = {
          id: generateMsgId(),  // DP 错误消息 ID
          role: 'assistant',  // DP 角色
          content: `DP 抱歉，系统遇到了一个问题：${err.message || '请稍后重试'}`,  // DP 错误提示
          isError: true,  // DP 标记为错误消息（UI 可能用不同样式）
        }
        updateMessages([...updatedMessages, errorMsg])  // DP 追加错误消息
        setStreamingContent('')  // DP 清空缓冲区
      } finally {
        setIsLoading(false)  // DP 加载结束
        abortRef.current = null  // DP 清空 abort 引用
      }
    },
    [messages, isLoading, streamingContent, updateMessages]  // DP 依赖消息状态和更新函数
  )

  // DP ── 清空聊天 ──
  const clearChat = useCallback(() => {
    updateMessages([])  // DP 清空消息列表
    sessionIdRef.current = null  // DP 清空 session ref
    setStreamingContent('')  // DP 清空流式缓冲区
    setError(null)  // DP 清空错误
  }, [updateMessages])  // DP 依赖消息更新函数

  return {
    messages,  // DP 已完成的消息列表
    streamingContent,  // DP 正在流式输出的文字（实时更新）
    isLoading,  // DP 是否正在等待/接收
    isStreaming: isLoading && streamingContent !== '',  // DP 是否正在流式输出中
    error,  // DP 错误信息
    sendMessage,  // DP 发送消息函数
    clearChat,  // DP 清空聊天函数
  }
}