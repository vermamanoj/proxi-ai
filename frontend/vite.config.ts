
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
      allowedHosts: true,  // Allow all hosts in Docker environment
      proxy: {
        // Proxy API requests to the Python Backend (Core)
        // Native (default): use localhost:4000
        // Docker: set VITE_API_URL=http://core:8000
        '/api': {
          target: process.env.VITE_API_URL || 'http://localhost:4000',
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
