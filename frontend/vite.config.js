import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// Capacitor 用 file:// / capacitor:// 加载页面，base 必须是相对路径
export default defineConfig({
  plugins: [vue()],
  base: './',
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    target: 'es2020',
    sourcemap: false,
  },
});
