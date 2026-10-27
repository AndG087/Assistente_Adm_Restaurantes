/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.BACKEND_URL ?? 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    server: {
      // Apenas no computador local; não expõe a porta para a rede.
      host: '127.0.0.1',
      port: 5173,
      // O navegador chama /api no próprio Vite, que repassa ao backend.
      // Assim o frontend nunca conhece o endereço do Ollama e não é preciso CORS.
      proxy: {
        '/api': { target: backendUrl, changeOrigin: true },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
    },
  }
})
