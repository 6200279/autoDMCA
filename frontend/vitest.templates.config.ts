/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.tsx'],
    include: ['src/components/templates/__tests__/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    exclude: [
      'node_modules',
      'dist',
      '.git',
      'e2e/**/*',
      'src/test/e2e/**/*'
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: 'coverage/templates',
      include: [
        'src/components/templates/**/*.{ts,tsx}',
        'src/services/dmcaTemplateValidator.ts',
        'src/types/templates.ts'
      ],
      exclude: [
        'src/components/templates/__tests__/**',
        'src/components/templates/**/*.test.{ts,tsx}',
        'src/components/templates/**/*.spec.{ts,tsx}',
        'src/components/templates/**/*.d.ts',
        'src/components/templates/**/index.ts'
      ],
      all: true,
      thresholds: {
        global: {
          branches: 85,
          functions: 85,
          lines: 85,
          statements: 85
        },
        // Specific thresholds for critical components
        'src/components/templates/TemplateLibraryDashboard.tsx': {
          branches: 90,
          functions: 90,
          lines: 90,
          statements: 90
        },
        'src/components/templates/TemplateCreationWizard.tsx': {
          branches: 90,
          functions: 90,
          lines: 90,
          statements: 90
        },
        'src/components/templates/EnhancedTemplateEditor.tsx': {
          branches: 90,
          functions: 90,
          lines: 90,
          statements: 90
        },
        'src/services/dmcaTemplateValidator.ts': {
          branches: 95,
          functions: 95,
          lines: 95,
          statements: 95
        }
      }
    },
    // Performance settings for template tests
    testTimeout: 15000,
    hookTimeout: 10000,
    teardownTimeout: 5000,
    
    // Parallel execution for faster testing
    pool: 'threads',
    poolOptions: {
      threads: {
        maxThreads: 4,
        minThreads: 2
      }
    },
    
    // Enhanced reporting for templates
    reporter: [
      'verbose',
      'json',
      ['html', { subdir: 'templates' }]
    ],
    
    // Custom test environment options
    environmentOptions: {
      jsdom: {
        resources: 'usable'
      }
    },

    // Template-specific globals
    define: {
      __TEMPLATE_TEST_ENV__: true,
      __MOCK_API__: true
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@templates': path.resolve(__dirname, './src/components/templates'),
      '@services': path.resolve(__dirname, './src/services'),
      '@types': path.resolve(__dirname, './src/types'),
      '@test': path.resolve(__dirname, './src/test')
    }
  }
})