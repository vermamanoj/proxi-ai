import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file from the parent directory (project root)
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '');

  return {
    plugins: [react()],
    server: {
      host: true,
      port: 5173,
      allowedHosts: ['proxi.audista.com', 'localhost'],
      proxy: {
        // Proxy API requests to the Python Backend running on port 8080
        '/api': {
          target: 'http://127.0.0.1:8080',
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
