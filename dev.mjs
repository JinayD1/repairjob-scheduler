// Starts the Python API and the Vite dev server together: `npm run dev`.
// Vite proxies /api/* to the Python server (see vite.config.ts).
import { spawn } from 'node:child_process'

const python = process.env.PYTHON || 'python3'
const api = spawn(python, ['dev_server.py', '8000'], { stdio: 'inherit' })
const vite = spawn('npx', ['vite'], { stdio: 'inherit', shell: process.platform === 'win32' })

const stop = () => {
  api.kill()
  vite.kill()
  process.exit(0)
}
process.on('SIGINT', stop)
process.on('SIGTERM', stop)
api.on('exit', (code) => {
  if (code !== 0 && code !== null) {
    console.error(`\nPython API exited with code ${code}. Is python3 installed?`)
    stop()
  }
})
vite.on('exit', stop)
