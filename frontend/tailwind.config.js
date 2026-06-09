/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",            // 扫描入口 HTML
    "./src/**/*.{js,ts,jsx,tsx}",  // 扫描所有源文件中的 Tailwind 类名
  ],
  theme: {
    extend: {
      // 自定义颜色 —— 仿 Claude 风格配色
      colors: {
        // Claude 风格色调：暖橙色 → 这里用橙色作为主色调
        brand: {
          50:  '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          300: '#fdba74',
          400: '#fb923c',
          500: '#f97316',  // 主品牌色
          600: '#ea580c',
          700: '#c2410c',
          800: '#9a3412',
          900: '#7c2d12',
        },
        // 暗色主题背景色
        surface: {
          50:  '#fafafa',
          100: '#f5f5f4',
          200: '#e7e5e4',
          700: '#292524',
          800: '#1c1917',
          900: '#0c0a09',
          950: '#09090b',
        },
      },
      // 自定义动画 —— 打字指示器的跳动效果
      animation: {
        'bounce-dot': 'bounce-dot 1.4s infinite ease-in-out both',
      },
      keyframes: {
        'bounce-dot': {
          '0%, 80%, 100%': { transform: 'scale(0)' },
          '40%': { transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
}
