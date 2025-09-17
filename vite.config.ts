import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite';
import { resolve } from 'path';

export default defineConfig({
  
  plugins: [react(), tailwindcss()],
  build: {
    lib: {
      entry: resolve(__dirname, 'frontend/index.ts'),
      name: 'RcaComponent',
    },
    rollupOptions: {
      external: ['react', 'react-dom'],
      output: {
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM'
        },
        exports: 'named'
      }
    }
  },
  server: {
    proxy: {
      '/submit': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/watch': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/report': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    }
  }
})
