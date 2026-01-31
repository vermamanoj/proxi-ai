
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
    // For Capacitor mobile builds, use relative paths
    base: process.env.CAPACITOR_BUILD ? './' : '/',
    server: {
      host: true,
      port: 5173,
      allowedHosts: true,  // Allow all hosts in Docker environment
      hmr: {
        // Fix HMR WebSocket when running through Docker port mapping (4002->5173)
        // Use 'auto' to let Vite detect the client port from the browser URL
        port: 5173,
      },
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
    // Inject env vars into the frontend
    define: {
      'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      // For mobile: absolute backend URL (set VITE_API_BASE_URL in .env for production)
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify(env.VITE_API_BASE_URL || '')
    },
    build: {
      outDir: 'dist',
      emptyOutDir: true,
      // Production security: minify and drop console logs
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: mode === 'production',
          drop_debugger: true
        }
      },
      // Code splitting for better performance
      rollupOptions: {
        output: {
          manualChunks: {
            // Separate vendor chunks
            'react-vendor': ['react', 'react-dom'],
            'google-ai': ['@google/genai'],
            'lucide': ['lucide-react'],
          }
        }
      },
      chunkSizeWarningLimit: 600  // Slightly increase limit for main bundle
    }
  };
});
