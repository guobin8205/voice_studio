import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8765',
        ws: true,  // 启用 WebSocket 代理
        changeOrigin: true,
      },
      '/ws': { target: 'ws://localhost:8765', ws: true },
    },
  },
})
