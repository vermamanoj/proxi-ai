import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: ['proxi.audista.com', 'localhost']
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  }
});