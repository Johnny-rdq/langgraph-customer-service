import { defineConfig } from 'vite'       // Vite 配置函数
import react from '@vitejs/plugin-react'   // React JSX 编译插件

// Vite 配置 —— 构建工具的核心配置
export default defineConfig({
  plugins: [react()],   // 启用 React 插件，支持 JSX 语法
  server: {
    port: 3000,         // 前端开发服务器端口
    proxy: {
      // 代理配置：将 /api 开头的请求转发到后端 FastAPI 服务
      '/api': {
        target: 'http://localhost:8000',  // 后端地址
        changeOrigin: true,               // 修改请求头中的 origin
      },
    },
  },
})
