@echo off
chcp 65001 >nul
title LangGraph 智能客服系统

echo ============================================
echo   🤖 LangGraph 智能客服系统 - 启动中...
echo ============================================
echo.

:: 进入项目目录
cd /d "%~dp0"

:: 启动后端 (新窗口)
echo 🚀 启动后端服务 (FastAPI)...
start "后端-API" cmd /k "cd /d %~dp0 && python app/main.py"

:: 等后端先启动
timeout /t 3 /nobreak >nul

:: 启动前端 (新窗口)
echo 🎨 启动前端页面 (React + Vite)...
start "前端-页面" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================
echo   ✅ 启动完成！
echo   🌐 前端页面: http://localhost:3000
echo   📡 API 文档: http://localhost:8000/docs
echo ============================================
echo.
echo   按任意键关闭启动窗口...
pause >nul
