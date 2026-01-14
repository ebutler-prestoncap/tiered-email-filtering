import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    allowedHosts: ['blackbox.pv.local', 'localhost'],
    proxy: {
      '/api': {
        // In Docker, use service name; locally use localhost
        target: process.env.DOCKER_ENV ? 'http://backend:5000' : 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      }
    }
  }
})

