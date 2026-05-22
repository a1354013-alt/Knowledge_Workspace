import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@vue/runtime-core': path.resolve(__dirname, './node_modules/@vue/runtime-core/dist/runtime-core.esm-bundler.js'),
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
          // Split shared UI dependencies by usage profile so the app shell does not inherit the full PrimeVue surface area.
          if (id.includes('axios')) {
            return 'http-vendor'
          }
          if (id.includes('primeicons') || id.includes('@primeuix')) {
            return 'prime-style'
          }
          if (id.includes('primevue')) {
            const shell = ['/button', '/card', '/inputtext', '/password']
            const feedback = ['/toast', '/toastservice', '/usetoast']
            const dataEntry = ['/dialog', '/dropdown', '/multiselect', '/chips', '/textarea']
            const dataGrid = ['/datatable', '/column']
            if (shell.some((part) => id.includes(part))) {
              return 'prime-shell'
            }
            if (feedback.some((part) => id.includes(part))) {
              return 'prime-feedback'
            }
            if (dataEntry.some((part) => id.includes(part))) {
              return 'prime-data-entry'
            }
            if (dataGrid.some((part) => id.includes(part))) {
              return 'prime-data-grid'
            }
            return 'prime-core'
          }
          return 'vendor'
        },
      },
    },
  },
})
