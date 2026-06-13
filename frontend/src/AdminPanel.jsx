import React, { useState, useEffect, useRef } from 'react';

export default function AdminPanel() {
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [message, setMessage] = useState('');
  const [wsConnected, setWsConnected] = useState(false);  // WebSocket 连接状态
  const activeSessionRef = useRef(null);
  const chatBottomRef = useRef(null);
  // 同步 ref
  useEffect(() => { activeSessionRef.current = activeSession; }, [activeSession]);

  // 聊天记录更新时自动滚到底部
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  // ── 拉取排队列表的公共函数（供轮询和 WebSocket 通知复用）──
  const fetchSessions = async () => {
    try {
      const res = await fetch('http://localhost:8888/api/v1/ws/admin/sessions');
      const data = await res.json();
      setSessions(data);
    } catch (error) {
      console.error("获取排队列表失败", error);
    }
  };

  const fetchChatHistory = async (sessionId) => {
    if (!sessionId) return;
    try {
      const res = await fetch(`http://localhost:8888/api/v1/sessions/${sessionId}/messages`);
      const data = await res.json();
      setChatHistory(data);
    } catch (error) {
      console.error("获取聊天记录失败", error);
    }
  };

  // WebSocket 实时监听：new_human_session / user_message / session_exited
  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;
    let pingInterval = null;

    const connectWs = () => {
      ws = new WebSocket('ws://localhost:8888/api/v1/ws/admin/listen');

      ws.onopen = () => {
        setWsConnected(true);
        console.log('🔔 管理员 WebSocket 已连接，实时监听...');
        pingInterval = setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN) ws.send('ping');
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'new_human_session') {
            console.log('📢 新排队会话:', data.session_id);
            fetchSessions();  // 刷新排队列表
            // 没有选中会话时自动跳转到新来的
            if (!activeSessionRef.current) {
              setActiveSession(data.session_id);
            }

          } else if (data.type === 'user_message') {
            console.log('💬 用户新消息, 会话:', data.session_id);
            // 属于当前查看的会话则立即刷新
            if (activeSessionRef.current === data.session_id) {
              fetchChatHistory(data.session_id);
            }

          } else if (data.type === 'session_exited') {
            console.log('🔴 用户已退出人工:', data.session_id);
            // 立即将该会话从左侧列表中移除
            setSessions(prev => prev.filter(s => s.session_id !== data.session_id));

            // 当用户退出人工时，直接静默恢复未选中状态并清空聊天
            if (activeSessionRef.current === data.session_id) {
              setActiveSession(null);
              setChatHistory([]);
            }
          }

        } catch (err) {
          console.error('WebSocket 消息解析失败:', err);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        console.log('🔌 管理员 WebSocket 断开，3 秒后重连...');
        if (pingInterval) clearInterval(pingInterval);
        reconnectTimer = setTimeout(connectWs, 3000);
      };

      ws.onerror = (err) => {
        console.error('管理员 WebSocket 错误:', err);
        ws?.close();
      };
    };

    connectWs();

    return () => {
      if (pingInterval) clearInterval(pingInterval);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  // 1. 每 3 秒自动刷新左侧排队列表
  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 3000);
    return () => clearInterval(interval);
  }, []);

  // 2. 每 2 秒自动刷新右侧选中会话的聊天记录
  useEffect(() => {
    if (!activeSession) return;
    fetchChatHistory(activeSession);
    const interval = setInterval(() => fetchChatHistory(activeSession), 2000);
    return () => clearInterval(interval);
  }, [activeSession]);

  // 3. 发送客服消息
  const handleSend = async () => {
    if (!message.trim() || !activeSession) return;
    try {
      const res = await fetch('http://localhost:8888/api/v1/ws/admin/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: activeSession, content: message })
      });
      if (res.ok) {
        setMessage('');
        fetchChatHistory(activeSession);
      } else {
        alert("发送失败");
      }
    } catch (error) {
      alert("接口连接错误");
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: '#1e1e1e', color: 'white', fontFamily: 'sans-serif' }}>
      {/* 左侧列表 */}
      <div style={{ width: '300px', borderRight: '1px solid #444', padding: '20px' }}>
        <h2>人工客服工作台</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
          <span style={{
            display: 'inline-block',
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            backgroundColor: wsConnected ? '#00e676' : '#ff5252',
            boxShadow: wsConnected ? '0 0 6px #00e676' : 'none'
          }} />
          <span style={{ fontSize: '12px', color: '#aaa' }}>
            {wsConnected ? '实时连接已就绪' : '轮询模式（WebSocket 未连接）'}
          </span>
        </div>
        <p style={{ color: '#aaa' }}>当前排队人数：{sessions.length}</p>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {sessions.map(s => (
            <li
              key={s.session_id}
              onClick={() => { setActiveSession(s.session_id); fetchChatHistory(s.session_id); }}
              style={{
                padding: '15px',
                margin: '10px 0',
                cursor: 'pointer',
                backgroundColor: activeSession === s.session_id ? '#007bff' : '#333',
                color: 'white',
                borderRadius: '8px',
                fontWeight: 'bold'
              }}
            >
              <div style={{ fontSize: '14px' }} title={s.session_id}>{s.title || '新对话'}</div>
              <div style={{ fontSize: '11px', color: '#888', marginTop: '4px' }}>
                {s.session_id.substring(0, 12)}...
              </div>
            </li>
          ))}
        </ul>
      </div>

      {/* 右侧聊天及操作区 */}
      <div style={{ flex: 1, padding: '30px', display: 'flex', flexDirection: 'column' }}>
        {activeSession ? (
          <>
            <h3 style={{ borderBottom: '1px solid #444', paddingBottom: '10px' }}>
              正在接管会话: {activeSession}
            </h3>

            <div style={{ flex: 1, overflowY: 'auto', padding: '10px', backgroundColor: '#252526', borderRadius: '8px', marginBottom: '20px' }}>
              {chatHistory.length === 0 ? (
                <p style={{ color: '#888', textAlign: 'center', marginTop: '20px' }}>暂无聊天记录加载中...</p>
              ) : (
                // 🌟🌟🌟 核心过滤逻辑：把特定的系统提示语屏蔽掉 🌟🌟🌟
                chatHistory
                  .filter(msg => {
                    const text = msg.content || '';
                    return !text.includes('【系统提示】已为您成功转接') &&
                           !text.includes('✅ **已退出人工客服**') &&
                           !text.includes('⏱️ **对话超时**');
                  })
                  .map((msg, idx) => (
                    <div
                      key={idx}
                      style={{
                        margin: '10px 0',
                        textAlign: msg.role === 'user' ? 'left' : 'right'
                      }}
                    >
                      <span style={{
                        display: 'inline-block',
                        padding: '10px 15px',
                        borderRadius: '8px',
                        backgroundColor: msg.role === 'user' ? '#3e3e3e' : '#007bff',
                        color: 'white',
                        maxWidth: '70%',
                        wordBreak: 'break-all',
                        whiteSpace: 'pre-wrap'
                      }}>
                        <strong style={{ display: 'block', fontSize: '12px', color: '#aaa', marginBottom: '4px' }}>
                          {msg.role === 'user' ? '用户' : '客服/AI'}
                        </strong>
                        {msg.content}
                      </span>
                    </div>
                  ))
              )}
              <div ref={chatBottomRef} />
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                style={{
                  flex: 1,
                  padding: '15px',
                  fontSize: '16px',
                  color: 'black',
                  backgroundColor: 'white',
                  border: '2px solid #007bff',
                  borderRadius: '5px'
                }}
                placeholder="打字回复用户..."
              />
              <button
                onClick={handleSend}
                style={{
                  padding: '15px 30px',
                  fontSize: '16px',
                  cursor: 'pointer',
                  backgroundColor: '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  fontWeight: 'bold'
                }}
              >
                发送
              </button>
            </div>
          </>
        ) : (
          <h3 style={{ color: '#888', marginTop: '50px' }}>👈 选中的用户已离开或列表暂空</h3>
        )}
      </div>
    </div>
  );
}