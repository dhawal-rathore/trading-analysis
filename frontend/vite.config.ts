import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://server:8000',
        changeOrigin: true,
      }
    },
    host: true, // Listen on all network interfaces for Docker
    port: 3000
  }
})
