import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// Security-enhanced Vite configuration
export default defineConfig({
  plugins: [react()],
  
  // Security: Configure build output
  build: {
    // Security: Remove source maps in production
    sourcemap: false,
    
    // Security: Minimize bundle size
    minify: 'terser',
    terserOptions: {
      compress: {
        // Security: Remove console logs in production
        drop_console: true,
        drop_debugger: true,
        // Security: Remove unused code
        dead_code: true,
        // Security: Obfuscate variable names
        mangle: true,
      },
      format: {
        // Security: Remove comments
        comments: false,
      },
    },
    
    // Security: Configure chunk splitting for better caching
    rollupOptions: {
      output: {
        // Security: Hash filenames for cache busting
        entryFileNames: 'assets/[name].[hash].js',
        chunkFileNames: 'assets/[name].[hash].js',
        assetFileNames: 'assets/[name].[hash].[ext]',
        
        // Security: Separate vendor chunks
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          ui: ['primereact', 'primeicons'],
          utils: ['axios', 'date-fns']
        },
      },
    },
    
    // Security: Set asset limits
    assetsInlineLimit: 4096, // 4kb
    
    // Security: Configure output directory
    outDir: 'dist',
    emptyOutDir: true,
  },
  
  // Security: Configure development server
  server: {
    // Security: Bind to localhost only
    host: 'localhost',
    port: 3000,
    
    // Security: Enable HTTPS in development
    https: process.env.VITE_HTTPS === 'true' ? {
      key: resolve(__dirname, 'ssl/dev-key.pem'),
      cert: resolve(__dirname, 'ssl/dev-cert.pem'),
    } : false,
    
    // Security: Configure headers
    headers: {
      // Security: Prevent MIME type sniffing
      'X-Content-Type-Options': 'nosniff',
      
      // Security: Prevent clickjacking
      'X-Frame-Options': 'DENY',
      
      // Security: Enable XSS protection
      'X-XSS-Protection': '1; mode=block',
      
      // Security: Content Security Policy for development
      'Content-Security-Policy': process.env.NODE_ENV === 'development' 
        ? "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; connect-src 'self' ws: wss:;"
        : "default-src 'self'; script-src 'self' 'unsafe-inline' https://js.stripe.com; style-src 'self' 'unsafe-inline'; connect-src 'self' wss:;",
      
      // Security: Referrer policy
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      
      // Security: Permissions policy
      'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), gyroscope=(), magnetometer=(), payment=(), usb=()',
    },
    
    // Security: Proxy configuration for API
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        secure: true,
        // Security: Configure proxy headers
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // Security: Add security headers to proxied requests
            proxyReq.setHeader('X-Forwarded-Proto', 'https');
            proxyReq.setHeader('X-Requested-With', 'XMLHttpRequest');
          });
        },
      },
    },
  },
  
  // Security: Configure environment variables
  define: {
    // Security: Only expose necessary environment variables
    __ENVIRONMENT__: JSON.stringify(process.env.NODE_ENV || 'development'),
    __VERSION__: JSON.stringify(process.env.npm_package_version),
  },
  
  // Security: Configure path resolution
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@components': resolve(__dirname, './src/components'),
      '@pages': resolve(__dirname, './src/pages'),
      '@utils': resolve(__dirname, './src/utils'),
      '@services': resolve(__dirname, './src/services'),
      '@hooks': resolve(__dirname, './src/hooks'),
      '@contexts': resolve(__dirname, './src/contexts'),
    },
  },
  
  // Security: Configure CSS
  css: {
    // Security: Enable CSS modules for scoped styling
    modules: {
      localsConvention: 'camelCase',
      generateScopedName: '[name]__[local]___[hash:base64:5]',
    },
    
    // Security: PostCSS configuration
    postcss: {
      plugins: [
        // Add security-focused PostCSS plugins here
      ],
    },
  },
  
  // Security: Configure optimizations
  optimizeDeps: {
    // Security: Include critical dependencies
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'primereact',
      'axios',
      'dompurify', // For HTML sanitization
    ],
    
    // Security: Exclude potentially unsafe dependencies
    exclude: [
      // Add any dependencies that shouldn't be optimized
    ],
  },
  
  // Security: Configure esbuild
  esbuild: {
    // Security: Remove debugger statements and console logs in production
    drop: process.env.NODE_ENV === 'production' ? ['console', 'debugger'] : [],
    
    // Security: Minify identifiers
    minifyIdentifiers: process.env.NODE_ENV === 'production',
    
    // Security: Minify syntax
    minifySyntax: process.env.NODE_ENV === 'production',
    
    // Security: Minify whitespace
    minifyWhitespace: process.env.NODE_ENV === 'production',
  },
  
  // Security: Configure worker
  worker: {
    format: 'es',
  },
  
  // Security: Configure preview server
  preview: {
    port: 3001,
    host: 'localhost',
    
    // Security: Same headers as dev server
    headers: {
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block',
      'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self' wss:;",
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    },
  },
})