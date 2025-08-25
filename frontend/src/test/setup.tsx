/**
 * Test setup file for Vitest and React Testing Library
 * Configures testing environment, mocks, and global utilities
 */

import '@testing-library/jest-dom'
import { vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeAll, afterAll } from 'vitest'
import { server } from './mocks/server'

// Mock ResizeObserver (used by PrimeReact components)
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver (used by lazy loading components)
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock matchMedia (used by responsive components)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock window.scrollTo
Object.defineProperty(window, 'scrollTo', {
  writable: true,
  value: vi.fn(),
})

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
})

// Mock environment variables
vi.mock('import.meta.env', () => ({
  VITE_API_URL: 'http://localhost:8080',
  VITE_WS_URL: 'ws://localhost:8080',
  VITE_STRIPE_PUBLIC_KEY: 'pk_test_fake_key',
  MODE: 'test',
  DEV: false,
  PROD: false,
}))

// Mock Chart.js to avoid canvas issues in tests
vi.mock('chart.js', () => ({
  Chart: {
    register: vi.fn(),
    defaults: {
      plugins: {
        legend: {
          labels: {
            usePointStyle: false,
          },
        },
      },
    },
  },
  CategoryScale: vi.fn(),
  LinearScale: vi.fn(),
  BarElement: vi.fn(),
  LineElement: vi.fn(),
  PointElement: vi.fn(),
  ArcElement: vi.fn(),
  Title: vi.fn(),
  Tooltip: vi.fn(),
  Legend: vi.fn(),
}))

// Mock react-chartjs-2
vi.mock('react-chartjs-2', () => ({
  Line: ({ data, options }: any) => <div data-testid="line-chart" data-chart-data={JSON.stringify(data)} />,
  Bar: ({ data, options }: any) => <div data-testid="bar-chart" data-chart-data={JSON.stringify(data)} />,
  Pie: ({ data, options }: any) => <div data-testid="pie-chart" data-chart-data={JSON.stringify(data)} />,
  Doughnut: ({ data, options }: any) => <div data-testid="doughnut-chart" data-chart-data={JSON.stringify(data)} />,
}))

// Mock file upload functionality
global.File = class MockFile {
  constructor(public parts: any[], public filename: string, public properties?: any) {}
}

global.FileReader = class MockFileReader {
  result: any = null
  error: any = null
  readyState: number = 0
  
  onload: ((this: FileReader, ev: ProgressEvent<FileReader>) => any) | null = null
  onerror: ((this: FileReader, ev: ProgressEvent<FileReader>) => any) | null = null
  
  readAsDataURL = vi.fn().mockImplementation(() => {
    this.readyState = 2
    this.result = 'data:image/jpeg;base64,fake-base64-data'
    if (this.onload) {
      this.onload({} as ProgressEvent<FileReader>)
    }
  })
  
  readAsText = vi.fn().mockImplementation(() => {
    this.readyState = 2
    this.result = 'fake file content'
    if (this.onload) {
      this.onload({} as ProgressEvent<FileReader>)
    }
  })
}

// Mock URL.createObjectURL and revokeObjectURL
global.URL.createObjectURL = vi.fn(() => 'mock-url')
global.URL.revokeObjectURL = vi.fn()

// Mock WebSocket for real-time features
global.WebSocket = vi.fn().mockImplementation(() => ({
  close: vi.fn(),
  send: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  readyState: 1, // OPEN
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3,
}))

// Mock crypto.randomUUID
Object.defineProperty(global.crypto, 'randomUUID', {
  value: vi.fn(() => 'mock-uuid-123'),
})

// Start mock service worker
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
})

// Clean up after each test
afterEach(() => {
  cleanup()
  server.resetHandlers()
  vi.clearAllMocks()
  localStorageMock.clear()
  sessionStorageMock.clear()
})

// Close mock service worker
afterAll(() => {
  server.close()
})

// Global test utilities
export const createMockFile = (name: string, size: number, type: string) => {
  const file = new File(['mock content'], name, { type })
  Object.defineProperty(file, 'size', { value: size })
  return file
}

export const createMockEvent = (eventType: string, target: any = {}) => ({
  type: eventType,
  target,
  preventDefault: vi.fn(),
  stopPropagation: vi.fn(),
})

export const mockNavigate = vi.fn()
export const mockLocation = {
  pathname: '/',
  search: '',
  hash: '',
  state: null,
  key: 'default',
}

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation,
    useParams: () => ({}),
    BrowserRouter: ({ children }: any) => children,
  }
})