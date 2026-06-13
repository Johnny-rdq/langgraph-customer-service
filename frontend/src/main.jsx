import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
// 🌟 引入你的客服后台组件
import AdminPanel from './AdminPanel.jsx'

const root = ReactDOM.createRoot(document.getElementById('root'));

// 🌟 核心分流逻辑：看网址决定渲染谁
if (window.location.pathname === '/admin') {
  root.render(<AdminPanel />);
} else {
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}