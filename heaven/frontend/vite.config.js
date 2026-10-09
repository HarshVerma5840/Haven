import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  build: {
    outDir: '../../hrms/hrms/public/heaven',
    emptyOutDir: true,
  },
  server: {
    port: 8082,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})

