/**
 * Test utilities for React Testing Library and component testing
 * Provides custom render functions, mock providers, and common test helpers
 */

import React from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PrimeReactProvider } from 'primereact/api'
import { vi } from 'vitest'

import { AuthProvider } from '@/contexts/AuthContext'
import { LayoutProvider } from '@/contexts/LayoutContext'
import { WebSocketProvider } from '@/contexts/WebSocketContext'

// Mock authentication context value
export const mockAuthContextValue = {
  user: {
    id: 1,
    email: 'test@example.com',
    username: 'testuser',
    full_name: 'Test User',
    is_active: true,
    is_superuser: false,
  },
  token: 'mock-token',
  isAuthenticated: true,
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  updateUser: vi.fn(),
  loading: false,
  error: null,
}

// Mock layout context value
export const mockLayoutContextValue = {
  theme: 'light' as const,
  toggleTheme: vi.fn(),
  sidebarVisible: false,
  setSidebarVisible: vi.fn(),
  isMobile: false,
  isTablet: false,
  isDesktop: true,
}

// Mock WebSocket context value
export const mockWebSocketContextValue = {
  socket: null,
  isConnected: false,
  lastMessage: null,
  sendMessage: vi.fn(),
  subscribe: vi.fn(),
  unsubscribe: vi.fn(),
}

// Test wrapper component that provides all necessary context providers
interface TestProvidersProps {
  children: React.ReactNode
  authValue?: Partial<typeof mockAuthContextValue>
  layoutValue?: Partial<typeof mockLayoutContextValue>
  wsValue?: Partial<typeof mockWebSocketContextValue>
  queryClient?: QueryClient
  initialEntries?: string[]
}

export const TestProviders: React.FC<TestProvidersProps> = ({
  children,
  authValue = {},
  layoutValue = {},
  wsValue = {},
  queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  }),
  initialEntries = ['/'],
}) => {
  const mergedAuthValue = { ...mockAuthContextValue, ...authValue }
  const mergedLayoutValue = { ...mockLayoutContextValue, ...layoutValue }
  const mergedWsValue = { ...mockWebSocketContextValue, ...wsValue }

  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <PrimeReactProvider>
          <AuthProvider value={mergedAuthValue}>
            <LayoutProvider value={mergedLayoutValue}>
              <WebSocketProvider value={mergedWsValue}>
                {children}
              </WebSocketProvider>
            </LayoutProvider>
          </AuthProvider>
        </PrimeReactProvider>
      </QueryClientProvider>
    </BrowserRouter>
  )
}

// Custom render function that includes all providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  authValue?: Partial<typeof mockAuthContextValue>
  layoutValue?: Partial<typeof mockLayoutContextValue>
  wsValue?: Partial<typeof mockWebSocketContextValue>
  queryClient?: QueryClient
  initialEntries?: string[]
}

export const renderWithProviders = (
  ui: React.ReactElement,
  options: CustomRenderOptions = {}
) => {
  const {
    authValue,
    layoutValue,
    wsValue,
    queryClient,
    initialEntries,
    ...renderOptions
  } = options

  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <TestProviders
      authValue={authValue}
      layoutValue={layoutValue}
      wsValue={wsValue}
      queryClient={queryClient}
      initialEntries={initialEntries}
    >
      {children}
    </TestProviders>
  )

  return render(ui, { wrapper: Wrapper, ...renderOptions })
}

// Helper to create authenticated user state
export const createAuthenticatedUser = (overrides = {}) => ({
  ...mockAuthContextValue.user,
  ...overrides,
})

// Helper to create unauthenticated state
export const createUnauthenticatedState = () => ({
  ...mockAuthContextValue,
  user: null,
  token: null,
  isAuthenticated: false,
})

// Mock form data for testing
export const createMockFormData = (data: Record<string, any>) => {
  const formData = new FormData()
  Object.entries(data).forEach(([key, value]) => {
    if (value instanceof File) {
      formData.append(key, value)
    } else if (Array.isArray(value)) {
      value.forEach((item, index) => {
        formData.append(`${key}[${index}]`, item)
      })
    } else {
      formData.append(key, String(value))
    }
  })
  return formData
}

// Mock file for upload testing
export const createMockFile = (
  name: string = 'test.jpg',
  size: number = 1024,
  type: string = 'image/jpeg',
  content: string = 'mock file content'
) => {
  const file = new File([content], name, { type })
  Object.defineProperty(file, 'size', { value: size })
  return file
}

// Mock drag and drop events
export const createMockDragEvent = (files: File[] = []) => ({
  dataTransfer: {
    files,
    items: files.map(file => ({
      kind: 'file',
      type: file.type,
      getAsFile: () => file,
    })),
    types: ['Files'],
  },
  preventDefault: vi.fn(),
  stopPropagation: vi.fn(),
})

// Mock clipboard data
export const createMockClipboardEvent = (text: string = '') => ({
  clipboardData: {
    getData: vi.fn(() => text),
    setData: vi.fn(),
  },
  preventDefault: vi.fn(),
})

// Mock intersection observer entries
export const createMockIntersectionObserverEntry = (
  isIntersecting: boolean = true,
  target: Element = document.createElement('div')
) => ({
  isIntersecting,
  target,
  intersectionRatio: isIntersecting ? 1 : 0,
  boundingClientRect: target.getBoundingClientRect(),
  intersectionRect: target.getBoundingClientRect(),
  rootBounds: document.documentElement.getBoundingClientRect(),
  time: Date.now(),
})

// Wait for async operations to complete
export const waitForPromises = () => new Promise(resolve => setTimeout(resolve, 0))

// Utility to mock console methods
export const mockConsole = () => {
  const originalConsole = { ...console }
  
  beforeEach(() => {
    console.log = vi.fn()
    console.warn = vi.fn()
    console.error = vi.fn()
    console.info = vi.fn()
  })
  
  afterEach(() => {
    Object.assign(console, originalConsole)
  })
  
  return {
    expectLog: (message: string) => expect(console.log).toHaveBeenCalledWith(message),
    expectWarn: (message: string) => expect(console.warn).toHaveBeenCalledWith(message),
    expectError: (message: string) => expect(console.error).toHaveBeenCalledWith(message),
  }
}

// Mock window methods
export const mockWindow = () => {
  const originalWindow = { ...window }
  
  const mocks = {
    alert: vi.fn(),
    confirm: vi.fn(() => true),
    prompt: vi.fn(() => 'test input'),
    open: vi.fn(),
    close: vi.fn(),
    focus: vi.fn(),
    blur: vi.fn(),
  }
  
  beforeEach(() => {
    Object.assign(window, mocks)
  })
  
  afterEach(() => {
    Object.assign(window, originalWindow)
  })
  
  return mocks
}

// Mock API responses for specific test scenarios
export const mockApiResponses = {
  success: (data: any) => ({
    ok: true,
    status: 200,
    json: vi.fn().mockResolvedValue(data),
  }),
  
  error: (status: number = 500, message: string = 'Server Error') => ({
    ok: false,
    status,
    json: vi.fn().mockResolvedValue({ detail: message }),
  }),
  
  unauthorized: () => ({
    ok: false,
    status: 401,
    json: vi.fn().mockResolvedValue({ detail: 'Unauthorized' }),
  }),
  
  notFound: () => ({
    ok: false,
    status: 404,
    json: vi.fn().mockResolvedValue({ detail: 'Not Found' }),
  }),
  
  validationError: (errors: Record<string, string[]>) => ({
    ok: false,
    status: 422,
    json: vi.fn().mockResolvedValue({ detail: errors }),
  }),
}

// Mock data factories
export const createMockProfile = (overrides = {}) => ({
  id: 1,
  user_id: 1,
  stage_name: 'TestCreator',
  real_name: 'Test Creator',
  bio: 'Test creator bio',
  monitoring_enabled: true,
  social_media_accounts: {
    instagram: '@testcreator',
    twitter: '@testcreator',
  },
  protection_level: 'premium',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides,
})

export const createMockTakedown = (overrides = {}) => ({
  id: 1,
  profile_id: 1,
  infringing_url: 'https://example.com/stolen-content',
  original_work_title: 'My Original Content',
  copyright_owner: 'Test Creator',
  status: 'pending',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides,
})

export const createMockInfringement = (overrides = {}) => ({
  id: 1,
  profile_id: 1,
  url: 'https://example.com/infringement',
  title: 'Stolen Content',
  description: 'My content was stolen',
  confidence_score: 0.95,
  status: 'detected',
  platform: 'instagram',
  created_at: '2024-01-01T00:00:00Z',
  detected_at: '2024-01-01T00:00:00Z',
  ...overrides,
})

// Re-export everything from React Testing Library for convenience
export * from '@testing-library/react'
export * from '@testing-library/user-event'

// Re-export our custom render as the default
export { renderWithProviders as render }