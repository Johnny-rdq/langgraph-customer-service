import React from 'react'            // React 核心库
import ReactDOM from 'react-dom/client'  // ReactDOM —— 挂载到浏览器 DOM
import App from './App.jsx'              // 根组件
import './index.css'                     // 全局样式

// 将 React 应用挂载到 index.html 中的 #root 元素
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
