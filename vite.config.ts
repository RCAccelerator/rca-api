import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite';
import { resolve } from 'path';

const standalone = loadEnv("", process.cwd())['VITE_STANDALONE'];
console.log("standalone?", standalone)
export default defineConfig({

  plugins: [react(), tailwindcss()],
  build: standalone ? {} : {
    lib: {
      entry: resolve(__dirname, 'frontend/RcaComponent.jsx'),
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
    },
  },
  server: {
    proxy: {
      '/get': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    }
  }
})
