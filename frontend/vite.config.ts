import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  build: {
    outDir: 'dist',
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@import "primereact/resources/themes/lara-light-blue/theme.css";`
      }
    }
  },
  optimizeDeps: {
    include: [
      'primereact/button',
      'primereact/inputtext',
      'primereact/datatable',
      'primereact/column',
      'primereact/dialog',
      'primereact/toast',
      'primereact/toolbar',
      'primereact/panel',
      'primereact/card',
      'primereact/dropdown',
      'primereact/calendar',
      'primereact/chart',
      'primeicons/primeicons.css'
    ]
  }
})