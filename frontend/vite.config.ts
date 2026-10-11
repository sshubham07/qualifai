import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev: the browser talks to Vite on :3000, which proxies API calls to FastAPI.
// Production: `npm run build` writes dist/, which FastAPI serves itself (ADR-0015).
const API_URL = process.env.QUALIFAI_API_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    strictPort: true,
    proxy: { '/v1': API_URL },
  },
})
