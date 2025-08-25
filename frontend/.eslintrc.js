module.exports = {
  root: true,
  env: {
    browser: true,
    es2020: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
  ],
  ignorePatterns: [
    'dist',
    '.eslintrc.js',
    'node_modules',
    '*.config.*',
    'public/sw.js',
  ],
  parser: '@typescript-eslint/parser',
  plugins: ['react', '@typescript-eslint'],
  rules: {
    // Type safety
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/no-empty-function': 'warn',
    
    // React specific
    'react/react-in-jsx-scope': 'off',
    'react/prop-types': 'off',
    
    // General code quality
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'prefer-const': 'error',
    'no-unused-vars': 'off', // Use @typescript-eslint/no-unused-vars instead
  },
  settings: {
    react: {
      version: 'detect',
    },
  },
}