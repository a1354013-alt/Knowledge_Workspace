import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'happy-dom',
    setupFiles: ['./tests/vitest.setup.ts'],
    include: ['tests/**/*.test.ts'],
    restoreMocks: true,
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api'),
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return undefined
          }
          // Split heavy UI dependencies into multiple predictable chunks to reduce first-load pressure.
          if (id.includes('axios')) {
            return 'http-vendor'
          }
          if (id.includes('primeicons') || id.includes('@primeuix')) {
            return 'prime-style'
          }
          if (id.includes('primevue')) {
            const heavy = ['/datatable', '/column', '/dialog', '/dropdown', '/chips', '/textarea', '/password']
            if (heavy.some((part) => id.includes(part))) {
              return 'prime-heavy'
            }
            return 'prime-core'
          }
          return 'vendor'
        },
      },
    },
  },
})
