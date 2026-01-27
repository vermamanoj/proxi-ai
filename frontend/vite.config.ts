
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file from the parent directory (project root)
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '');

  return {
    plugins: [react()],
    server: {
      host: true,
      port: 5173,
      allowedHosts: ['proxi.audista.com', 'localhost', 'serves-existence-sacrifice-bin.trycloudflare.com'],
      proxy: {
        // Proxy API requests to the Python Backend (Core)
        // In Docker: use service name 'core' or host.docker.internal
        // Locally: use 127.0.0.1:4000
        '/api': {
          target: process.env.VITE_API_URL || 'http://core:8000',
          changeOrigin: true,
          secure: false,
        }
      }
    },
    // Inject the API Key into the frontend so useGeminiLive.ts can use process.env.API_KEY
    define: {
      'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY)
    },
    build: {
      outDir: 'dist',
      emptyOutDir: true,
    }
  };
});
