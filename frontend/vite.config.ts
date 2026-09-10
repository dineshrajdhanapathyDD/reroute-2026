import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Local dev: proxy API calls to the FastAPI backend.
      '/api': 'http://localhost:8000',
    },
  },
})
