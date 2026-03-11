import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    host: true
  },
  define: {
    // 確保環境變數可在應用中訪問
    __VITE_API_BASE__: JSON.stringify(process.env.VITE_API_BASE || 'http://localhost:8000')
  }
})
