import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In local development /api is proxied to the FastAPI process.
// In the container nginx performs the same proxying.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 8080,
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
