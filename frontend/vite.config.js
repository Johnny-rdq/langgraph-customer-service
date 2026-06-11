import { defineConfig } from 'vite'       // Vite 配置函数
import react from '@vitejs/plugin-react'   // React JSX 编译插件

// 后端地址：支持通过环境变量配置（Docker 部署时指向 backend 服务名）
const API_TARGET = process.env.VITE_API_TARGET || 'http://localhost:8888'  // 默认后端端口 8888（与 main.py 硬编码端口一致）

// Vite 配置 —— 构建工具的核心配置
export default defineConfig({
  plugins: [react()],   // 启用 React 插件，支持 JSX 语法
  server: {
    port: 3000,         // 前端开发服务器端口
    proxy: {
      // 代理配置：将 /api 开头的请求转发到后端 FastAPI 服务
      '/api': {
        target: API_TARGET,  // 后端地址（开发: localhost, Docker: backend 服务名）
        changeOrigin: true,  // 修改请求头中的 origin
      },
    },
  },
})
