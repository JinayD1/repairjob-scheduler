import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development, Vite serves the React app and forwards /api/* to the
// Python dev server (python3 dev_server.py). In production on Vercel, dist/ is
// served statically and /api/* is handled by the Python functions in api/.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
